"""Characterization tests for the EIC client (HANDOFF item D prerequisite).

``core/eic/eic_client.py`` is the priority god-file (~1.5k lines) and was wholly
untested — the golden-path tests in B fake ``EICClient`` away. The HANDOFF gates
any decomposition of it on "behavioral tests"; these are exactly that safety net.

They pin the client's *observable wire behavior* without a network or real auth:
``requests`` is mocked, and the client runs in its non-authenticated path (no
client_id, since a junk token does not decrypt). We assert the exact HTTP verb,
endpoint, and request payload it builds for each operation, plus how it parses
EIC's base64-wrapped ``response_json`` envelope. A future split of this file must
keep these green.
"""

from __future__ import annotations

import base64
import json
import pickle
import zlib
from typing import Any

import pytest
import requests as _requests
from cryptography.fernet import Fernet, InvalidToken

from exphub.core.eic import eic_client as eic_mod
from exphub.core.eic.eic_client import EICClient

# The outer Fernet key is hard-coded in eic_client._deserialize_outer_data; reuse
# it here to mint a valid token whose payload deserialises to a known dict.
_OUTER_KEY = b"R-2xj4mOi7UxjC7fR119FD5aw_GCfN4IZYlGn41XUxU="


def _make_eic_token(outer_data: dict) -> str:
    """Inverse of _deserialize_outer_data: Fernet(base64(zlib(pickle(data))))."""
    plaintext = base64.b64encode(zlib.compress(pickle.dumps(outer_data)))
    return Fernet(_OUTER_KEY).encrypt(plaintext).decode("utf-8")


def _eic_response(payload: dict, status: int = 200) -> _requests.models.Response:
    """Build a real ``requests.Response`` in EIC's ``response_json``/base64 format."""
    b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    body = json.dumps(f"response_json {b64}")  # response.json() -> "response_json <b64>"
    resp = _requests.models.Response()
    resp.status_code = status
    resp.reason = "OK"
    resp._content = body.encode("utf-8")
    return resp


class _HttpRecorder:
    """Captures the HTTP calls the EIC client makes and serves a canned payload."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._payload: dict = {"success": True}

    def set_payload(self, payload: dict) -> None:
        self._payload = payload

    def handler(self, method: str) -> Any:
        def _fn(url: str, params: Any = None, json: Any = None, **kwargs: Any) -> _requests.models.Response:
            self.calls.append({"method": method, "url": url, "json": json})
            return _eic_response(self._payload)

        return _fn


@pytest.fixture
def eic_http(monkeypatch: pytest.MonkeyPatch) -> _HttpRecorder:
    """Mock ``requests`` HTTP verbs in the eic_client module; force non-prod."""
    monkeypatch.setenv("EIC_ENV", "dev")
    rec = _HttpRecorder()
    for verb in ("get", "post", "put", "delete"):
        monkeypatch.setattr(eic_mod.requests, verb, rec.handler(verb))
    return rec


def _client() -> EICClient:
    # A valid token whose payload is an empty dict -> no client_id -> the
    # non-authenticated requests path (what dev/test uses).
    return EICClient(_make_eic_token({}), beamline="bl12", ipts_number="IPTS-1")


# --------------------------------------------------------------------------- construction


def test_construction_with_empty_payload_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EIC_ENV", "dev")
    client = _client()
    assert client.beamline == "bl12"
    assert client.ipts_number == "IPTS-1"
    assert client.client_id is None  # empty payload -> no credentials -> non-auth path
    assert client.outer_decrypt_error is None  # token decrypted cleanly
    assert client.is_production_environment is False
    assert isinstance(client.url_base, str) and client.url_base


def test_construction_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    # Characterises current behavior: a non-Fernet token raises at construction
    # (the decrypt call sits outside the handled block).
    monkeypatch.setenv("EIC_ENV", "dev")
    with pytest.raises(InvalidToken):
        EICClient("not-a-real-fernet-token", beamline="bl12")


# --------------------------------------------------------------------------- submit_table_scan


def test_submit_table_scan_request_shape(eic_http: _HttpRecorder) -> None:
    eic_http.set_payload({"success": True, "scan_id": 4242, "eic_response_message": "queued"})
    client = _client()

    headers = ["Title", "BL12:Mot:goniokm:omega"]
    rows = [["run1", 10.0]]
    success, scan_id, response_data = client.submit_table_scan(
        parms={"run_mode": 0, "headers": headers, "rows": rows},
        desc="CrystalPilot Submission run1",
        simulate_only=True,
    )

    assert success is True
    assert scan_id == 4242
    assert response_data["eic_response_message"] == "queued"

    # Exactly one POST to /eic/actions.
    assert len(eic_http.calls) == 1
    call = eic_http.calls[0]
    assert call["method"] == "post"
    assert call["url"].endswith("/eic/actions")

    # The EIC action envelope: ControlScenario -> TableScan -> our parms.
    body = call["json"]
    assert body["command"] == "ControlScenario"
    assert body["parameters"]["control_scenario"] == "TableScan"
    inner = body["parameters"]["parameters"]
    assert inner["run_mode"] == 0
    assert inner["headers"] == headers
    assert inner["rows"] == rows
    assert inner["simulate_only"] is True
    assert inner["description"] == "CrystalPilot Submission run1"
    # do_auth path stamps the IPTS number onto the request.
    assert body["ipts_number"] == "IPTS-1"


def test_submit_table_scan_missing_scan_id_defaults_to_minus_one(eic_http: _HttpRecorder) -> None:
    eic_http.set_payload({"success": True})  # no scan_id
    client = _client()
    success, scan_id, _ = client.submit_table_scan(parms={"headers": [], "rows": []})
    assert success is True
    assert scan_id == -1


# --------------------------------------------------------------------------- status / abort


def test_get_scan_status_parsing(eic_http: _HttpRecorder) -> None:
    eic_http.set_payload({"success": True, "is_done": True, "state": "done"})
    client = _client()
    success, is_done, state, _ = client.get_scan_status(scan_id=4242)
    assert success is True
    assert is_done is True
    assert state == "done"
    body = eic_http.calls[0]["json"]
    assert body["parameters"]["control_scenario"] == "ScanStatus"
    assert body["parameters"]["parameters"]["scan_id"] == 4242


def test_abort_scan_request_shape(eic_http: _HttpRecorder) -> None:
    eic_http.set_payload({"success": True})
    client = _client()
    success, _ = client.abort_scan(scan_id=4242)
    assert success is True
    body = eic_http.calls[0]["json"]
    assert body["parameters"]["control_scenario"] == "AbortScan"
    assert body["parameters"]["parameters"]["scan_id"] == 4242


# --------------------------------------------------------------------------- is_eic_enabled


def test_is_eic_enabled_true(eic_http: _HttpRecorder) -> None:
    eic_http.set_payload({"success": True, "EICEnabled": True})
    assert _client().is_eic_enabled() is True


def test_is_eic_enabled_false(eic_http: _HttpRecorder) -> None:
    eic_http.set_payload({"success": True, "EICEnabled": False})
    assert _client().is_eic_enabled() is False


def test_is_eic_enabled_swallows_errors(eic_http: _HttpRecorder) -> None:
    # Malformed envelope (no success/EICEnabled) -> disabled, not an exception.
    eic_http.set_payload({"unexpected": "shape"})
    assert _client().is_eic_enabled(disabled_on_exception=True) is False
