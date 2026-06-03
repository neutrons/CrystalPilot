"""Module for the factory that creates viewmodels used in the application."""

from typing import Any, Callable, Optional

from nova.mvvm.interface import BindingInterface

from ..agent.bridge import bridged_submodels
from ..core.beamline import active_technique
from .models.chat import ChatModel
from .models.main_model import MainModel
from .view_models.app_shell import AppShellViewModel
from .view_models.chat import ChatViewModel


def _build_steering(
    model: Any, binding: BindingInterface, notify_fn: Optional[Callable[[str], None]]
) -> Any:
    """Resolve and build the active technique's steering VM + root model.

    The steering VM and root model both come from the active technique manifest
    (``steering_vm_factory`` / ``root_model_factory``). Single-crystal leaves
    both ``None`` and is served by the historical defaults
    (``SingleCrystalSteeringViewModel`` + ``app.models.MainModel``), so its
    composition is unchanged; SANS (and any future technique) supplies its own
    pair, which is how ``MainApp()`` constructs under a ``technique="sans"``
    beamline such as USANS.
    """
    manifest = active_technique()
    factory = manifest.steering_vm_factory
    if factory is None:
        from ..techniques.single_crystal.view_models.steering import (
            SingleCrystalSteeringViewModel,
        )

        return SingleCrystalSteeringViewModel(model, binding, notify_fn=notify_fn)
    return factory(model, binding, notify_fn=notify_fn)


def create_viewmodels(binding: BindingInterface) -> dict:
    # Root model is the active technique's composite (single-crystal falls back
    # to the app-level MainModel); the steering VM is resolved the same way so
    # the shell never names a technique class.
    root_factory = active_technique().root_model_factory or MainModel
    model = root_factory()
    vm: dict = {}
    # The technique-agnostic shell owns tab navigation, the beamline
    # selector and the global snackbar; the steering VM owns the
    # technique tabs and reuses the shell snackbar via ``notify``.
    shell_vm = AppShellViewModel(binding)
    steering_vm = _build_steering(model, binding, shell_vm.notify)
    # On an inside-technique beamline switch the shell calls this hook on the
    # outgoing technique VM (cancel live-update, clear temporal buffers) before
    # the registry swaps. P3 deliverable 5.
    shell_vm.set_deactivate_hook(steering_vm.on_deactivate)
    vm["app_shell"] = shell_vm
    vm["steering"] = steering_vm

    # Chat / Agent viewmodel — shares the same technique root model so the
    # agent can read and write the same Pydantic fields the left-side tabs use.
    # Sub-model binds + action verbs resolve against the steering VM;
    # tab navigation resolves against the shell VM.
    chat_model = ChatModel()
    main_bindings = {name: getattr(steering_vm, f"{name}_bind") for name in bridged_submodels()}
    vm["chat"] = ChatViewModel(
        chat_model, model, binding, main_bindings,
        nav_fn=shell_vm.navigate_to_tab,
        main_vm=steering_vm,
    )

    return vm
