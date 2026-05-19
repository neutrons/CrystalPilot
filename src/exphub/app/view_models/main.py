"""Module for the main ViewModel."""

import asyncio
import json
import os
import subprocess
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

# Verbose tracing for ViewModel actions; off by default. Used to gate the
# (~100) print statements scattered across this module which previously
# spammed stdout on every UI interaction and per-second on the live-update
# loop. Set CRYSTALPILOT_DEBUG=1 to re-enable.
_DEBUG = bool(os.environ.get("CRYSTALPILOT_DEBUG"))


def _trace(*args: Any) -> None:
    if _DEBUG:
        print(*args)


@lru_cache(maxsize=1)
def _load_optimizer_fallback_angles() -> dict[str, list[list[float]]]:
    fixture = Path(__file__).parent.parent / "fixtures" / "optimizer_fallback_angles.json"
    return json.loads(fixture.read_text())

# from ..models.css_status import CSSStatusModel
# from ..models.temporal_analysis import TemporalAnalysisModel
import plotly.graph_objects as go
from nova.mvvm.interface import BindingInterface
from pydantic import BaseModel, Field

# from ..models.plotly import PlotlyConfig
# from pyvista import Plotter  # just for typing
# from ..models.pyvista import PyVistaConfig
from ..models.main_model import MainModel


def _default_beamline_id() -> str:
    """Pick the active beamline's id at view-state construction time."""
    try:
        from ...core.beamline import active as _active_beamline
        return _active_beamline().id
    except Exception:
        return ""


def _default_beamline_options() -> list[dict]:
    """Build the `[{value, title}]` list for the selector."""
    try:
        from ...core.beamline import get as _get
        from ...core.beamline import list_ids as _list_ids
        return [{"value": bid, "title": _get(bid).display_name} for bid in _list_ids()]
    except Exception:
        return []


class ViewState(BaseModel):
    """View state for the application."""

    active_tab: int = Field(default=0)
    is_under_development: bool = Field(default=False)
    is_uninterruptable: bool = Field(default=False)
    is_live_update_running: bool = Field(default=False)
    beamline_id: str = Field(default_factory=_default_beamline_id)
    beamline_options: list[dict] = Field(default_factory=_default_beamline_options)
    beamline_switch_notice: str = Field(default="")
    beamline_switch_visible: bool = Field(default=False)


class MainViewModel:
    """Viewmodel class, used to create data<->view binding and react on changes from GUI."""

    def __init__(self, model: MainModel, binding: BindingInterface):
        self.model = model
        self.view_state = ViewState()
        # Guard to prevent recursive / re-entrant updates for temporalanalysis
        self._temporalanalysis_updating: bool = False
        # Debounce: avoid repeated updates in a short interval (seconds)
        self._temporalanalysis_last_update_time: float = 0.0
        self._temporalanalysis_min_interval: float = 1.0
        # Task reference for the live-update loop; None means not running
        self._live_update_task: asyncio.Task | None = None
        # Back-reference to the TemporalAnalysisView (set by the view on init)
        self._temporal_view: Any = None
        # Track the last-known beamline so the view_state callback only triggers
        # a switch when the user actually picked a new option in the selector.
        self._last_beamline_id: str = self.view_state.beamline_id
        # Set parent link for temporalanalysis model so it can access sibling models
        try:
            if hasattr(self.model, "temporalanalysis") and hasattr(self.model.temporalanalysis, "set_parent"):
                self.model.temporalanalysis.set_parent(self.model)
        except Exception as e:
            print("Warning: failed to set parent for temporalanalysis:", e)
        # self.angleplan = AnglePlanModel()

        # here we create a bind that connects ViewModel with View. It returns a communicator object,
        # that allows to update View from ViewModel (by calling update_view).
        # self.model will be updated automatically on changes of connected fields in View,
        # but one also can provide a callback function if they want to react to those events
        # and/or process errors.
        self.model_bind = binding.new_bind(self.model, callback_after_update=self.change_callback)
        self.view_state_bind = binding.new_bind(
            self.view_state, callback_after_update=self.on_view_state_change
        )

        # self.experimentinfo_bind = binding.new_bind(self.model.experimentinfo, callback_after_update=self.change_callback)#noqa
        self.experimentinfo_bind = binding.new_bind(
            self.model.experimentinfo, callback_after_update=self.update_experimentinfo_options
        )
        self.angleplan_bind = binding.new_bind(
            self.model.angleplan, callback_after_update=self.update_angleplan_after_change
        )
        self.eiccontrol_bind = binding.new_bind(self.model.eiccontrol, callback_after_update=self.change_callback)
        # Create temporalanalysis bind WITHOUT a callback to avoid feedback loops
        self.temporalanalysis_bind = binding.new_bind(self.model.temporalanalysis)

        self.dataanalysis_bind = binding.new_bind(self.model.dataanalysis, callback_after_update=self.change_callback)

        # self.cssstatus_bind = binding.new_bind(self.model.cssstatus, callback_after_update=self.change_callback)
        self.cssstatus_bind = binding.new_bind(self.model.cssstatus, callback_after_update=self.update_cssstatus_figure)
        self.temporalanalysis_updatefigure_uncertainty_bind = binding.new_bind()
        self.temporalanalysis_updatefigure_intensity_bind = binding.new_bind()
        ######################################################################################################################################################
        # wrong
        #        self.newtabtemplate_bind = binding.new_bind(self.model.newtabtemplate, callback_after_update=self.change_callback)#noqa
        #        self.newtabtemplate_updatefig_bind = binding.new_bind(self.model.newtabtemplate, callback_after_update=self.update_newtabtemplate_figure)#noqa
        ######################################################################################################################################################
        self.newtabtemplate_bind = binding.new_bind(
            self.model.newtabtemplate, callback_after_update=self.update_newtabtemplate_figure
        )
        self.newtabtemplate_updatefig_bind = binding.new_bind()
        ######################################################################################################################################################

        # self.pyvista_config = PyVistaConfig()

        # self.plotly_config_bind = binding.new_bind(
        #    linked_object=self.plotly_config, callback_after_update=self.update_plotly_figure
        # )
        # self.plotly_figure_bind = binding.new_bind(linked_object=self.plotly_config)
        # self.pyvista_config_bind = binding.new_bind(linked_object=self.pyvista_config)

        # self.create_auto_update_cssstatus_figure()

        self.angleplan_updatefigure_coverage_bind = binding.new_bind()

        # Initialize temporalanalysis figures once at startup (no continuous callback)
        try:
            self.update_temporalanalysis_figure()
        except Exception:
            pass

    # def update_experimentinfo_options(self, _: Any = None) -> None:
    def update_experimentinfo_options(self, results: Dict[str, Any]) -> None:
        self.model.experimentinfo.update_option_lists()
        self.experimentinfo_bind.update_in_view(self.model.experimentinfo)
        _trace("update_experimentinfo_options")
        
        if results["error"]:
            print(f"error in fields {results['errored']}, model not changed")
        else:
            _trace("model fields updated:", results['updated'])
        # time.sleep(7)

    def change_callback(self, results: Dict[str, Any]) -> None:
        if results["error"]:
            print(f"error in fields {results['errored']}, model not changed")
        else:
            _trace("model fields updated:", results['updated'])

    def on_view_state_change(self, results: Dict[str, Any]) -> None:
        """Detect user-driven changes to ViewState (currently: beamline selector)."""
        if results.get("error"):
            print(f"view_state error in {results.get('errored')}")
            return
        if self.view_state.beamline_id != self._last_beamline_id:
            new_id = self.view_state.beamline_id
            self._last_beamline_id = new_id
            self.switch_beamline(new_id)

    def update_angleplan_after_change(self, results: Dict[str, Any]) -> None:
        """Angleplan post-validators (goniometer_type → angle_list_headers) mutate fields
        the user did not edit directly. Re-push the model so the view re-renders.
        """
        self.change_callback(results)
        self.angleplan_bind.update_in_view(self.model.angleplan)

    def navigate_to_tab(self, tab_number: int) -> None:
        """Switch the active tab by number and push the change to the view.

        Tab values: 1=IPTS Info, 2=Live Data Processing,
        3=Experiment Steering, 5=Instrument Status, 6=Data Analysis.
        """
        self.view_state.active_tab = tab_number
        self.view_state_bind.update_in_view(self.view_state)

    def switch_beamline(self, beamline_id: str) -> None:
        """Activate a different beamline plug-in.

        Called either directly (e.g. tests) or by ``on_view_state_change``
        when the user picks a new option in the selector. Updates the
        registry so subsequent reads of ``active().<...>`` pick up the new
        beamline's PVs/paths/presets.

        Hard-bound resources — the EPICS ``.bob`` screen connected at
        MainApp construction, the agent's RAG index, and the auto-resolved
        model-field defaults already applied to existing instances — won't
        reload mid-session. A snackbar surfaces that note.
        """
        from ...core.beamline import set_active

        if not beamline_id:
            return
        try:
            spec = set_active(beamline_id)
        except KeyError as e:
            print(f"switch_beamline: {e}")
            return
        # Keep our cached id aligned so the next change_callback doesn't loop.
        self._last_beamline_id = spec.id
        self.view_state.beamline_id = spec.id
        self.view_state.beamline_switch_notice = (
            f"Switched to {spec.display_name}. Restart the app for the "
            "Instrument Status screen and EPICS subscriptions to fully reload."
        )
        self.view_state.beamline_switch_visible = True
        self._push_view_state()

    def upload_strategy(self) -> None:
        self.model.angleplan.load_ap(self.model.angleplan.plan_file)
        self._push_angleplan()

    def update_view(self) -> None:
        # Generic catch-all: pushes every sub-model. Prefer the targeted
        # _push_* helpers below for handlers that only mutate one domain —
        # 5x less serialization over the websocket per click.
        self.view_state_bind.update_in_view(self.view_state)
        self.angleplan_bind.update_in_view(self.model.angleplan)
        self.eiccontrol_bind.update_in_view(self.model.eiccontrol)
        self.cssstatus_bind.update_in_view(self.model.cssstatus)
        self.temporalanalysis_bind.update_in_view(self.model.temporalanalysis)

    # ------- targeted view-state pushes (cheap, one bind each) ------------
    def _push_angleplan(self) -> None:
        self.angleplan_bind.update_in_view(self.model.angleplan)

    def _push_eiccontrol(self) -> None:
        self.eiccontrol_bind.update_in_view(self.model.eiccontrol)

    def _push_view_state(self) -> None:
        self.view_state_bind.update_in_view(self.view_state)

    def _push_temporal(self) -> None:
        self.temporalanalysis_bind.update_in_view(self.model.temporalanalysis)

    ######################################################################################################################################################
    # self.newtabtemplate_bind.update_in_view(self.model.newtabtemplate)
    ######################################################################################################################################################
    # print(self.model.angleplan.test_list)

    def submit_angle_plan(self) -> None:
        # print("submit_angle_plan")
        ipts_number = self.model.experimentinfo.ipts_number
        instrument_name = self.model.experimentinfo.instrument
        try:
            self.model.eiccontrol.submit_eic(
                self.model.angleplan.angle_list,
                ipts_number,
                instrument_name,
                goniometer_type=self.model.angleplan.goniometer_type,
            )
            if self.model.eiccontrol.is_simulation:
                self.model.eiccontrol.eic_status = "job submission simulated"
            else:
                self.model.eiccontrol.eic_status = "jobs submitted"
        except Exception as e:
            self.model.eiccontrol.eic_status = f"submission failed: {e}"
        self._push_eiccontrol()

    def call_load_token(self) -> None:
        try:
            self.model.eiccontrol.load_token(self.model.eiccontrol.token_file)
            self.model.eiccontrol.eic_status = "authenticated successfully"
        except Exception as e:
            self.model.eiccontrol.eic_status = f"authentication failed: {e}"
        self._push_eiccontrol()

    #
    #
    #    def update_pyvista_volume(self, plotter: Plotter) -> None:
    #        self.pyvista_config.render(plotter)
    #
    #    def update_plotly_figure(self, _: Any = None) -> None:
    #        self.plotly_config_bind.update_in_view(self.plotly_config)
    #        self.plotly_figure_bind.update_in_view(self.plotly_config.get_figure())
    #

    def update_cssstatus_figure(self, _: Any = None) -> None:
        # self.model.cssstatus.update_figure()
        self.cssstatus_bind.update_in_view(self.model.cssstatus)
        # time.sleep(7)

    async def auto_update_cssstatus_figure(self) -> None:
        while True:
            self.update_cssstatus_figure()
            await asyncio.sleep(1)

    def create_auto_update_cssstatus_figure(self) -> None:
        asyncio.create_task(self.auto_update_cssstatus_figure())

    def update_temporalanalysis_figure(self, _: Any = None) -> None:
        # Prevent re-entrant calls (can happen if view updates cause model callbacks)
        if self._temporalanalysis_updating:
            return
        # Debounce: skip if last update was very recent
        try:
            now = time.time()
            if now - self._temporalanalysis_last_update_time < self._temporalanalysis_min_interval:
                return
            self._temporalanalysis_last_update_time = now
        except Exception:
            # If time isn't available for some reason, continue without debounce
            pass
        self._temporalanalysis_updating = True
        try:
            # Push the new figures to the view
            self.temporalanalysis_updatefigure_intensity_bind.update_in_view(
                self.model.temporalanalysis.get_figure_intensity()
            )
            self.temporalanalysis_updatefigure_uncertainty_bind.update_in_view(
                self.model.temporalanalysis.get_figure_uncertainty()
            )
            # Update the model representation in view (avoid triggering view->model callbacks here)
            try:
                self.temporalanalysis_bind.update_in_view(self.model.temporalanalysis)
            except Exception:
                # Some binding implementations may attempt to invoke callbacks; swallow
                # exceptions here to avoid causing an update loop.
                pass
        finally:
            self._temporalanalysis_updating = False

    def _build_temporal_figures(self) -> tuple:
        """Build both figures in the caller's thread (intended for thread-pool use)."""
        return (
            self.model.temporalanalysis.get_figure_intensity(),
            self.model.temporalanalysis.get_figure_uncertainty(),
        )

    async def _update_figures_async(self, loop: asyncio.AbstractEventLoop) -> None:
        """Offload figure construction to thread pool, then push results to view on event loop."""
        if self._temporalanalysis_updating:
            return
        now = time.time()
        if now - self._temporalanalysis_last_update_time < self._temporalanalysis_min_interval:
            return
        self._temporalanalysis_last_update_time = now
        self._temporalanalysis_updating = True
        try:
            fig_i, fig_u = await loop.run_in_executor(None, self._build_temporal_figures)
            self.temporalanalysis_updatefigure_intensity_bind.update_in_view(fig_i)
            self.temporalanalysis_updatefigure_uncertainty_bind.update_in_view(fig_u)
            try:
                self.temporalanalysis_bind.update_in_view(self.model.temporalanalysis)
            except Exception:
                pass
        finally:
            self._temporalanalysis_updating = False

    async def auto_update_temporalanalysis_figure(self) -> None:
        while True:
            self.update_temporalanalysis_figure()
            await asyncio.sleep(30)

    def create_auto_update_temporalanalysis_figure(self) -> None:
        if self._live_update_task is not None and not self._live_update_task.done():
            print("Live update already running — ignoring duplicate start request.")
            return
        self._live_update_task = asyncio.create_task(self._start_and_run_live_update())

    async def _start_and_run_live_update(self) -> None:
        """Start live data collection in a thread, then run the reduction loop."""
        loop = asyncio.get_event_loop()
        # Show placeholder figures immediately while Mantid starts up
        if self._temporal_view is not None:
            self._temporal_view.show_placeholders()
        try:
            await loop.run_in_executor(None, self.model.temporalanalysis.start_reading_live_mtd_data)
        except RuntimeError as e:
            print(f"Failed to start live data: {e}")
            self._live_update_task = None
            return
        self.view_state.is_live_update_running = True
        self.view_state_bind.update_in_view(self.view_state)
        await self.get_live_mtd_data()

    def stop_live_update(self) -> None:
        """Cancel the asyncio task and stop the Mantid MonitorLiveData thread."""
        if self._live_update_task is not None and not self._live_update_task.done():
            self._live_update_task.cancel()
        self._live_update_task = None
        self.model.temporalanalysis.stop_live_data()
        self.view_state.is_live_update_running = False
        self.view_state_bind.update_in_view(self.view_state)

    async def get_live_mtd_data(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            print("============================================================================================")
            _trace("get_live_mtd_data")
            try:
                # update_experiment_info only sets Python attrs — safe on event loop thread
                models = self.model.temporalanalysis.get_models()
                self.model.temporalanalysis.mtd_workflow.update_experiment_info(models)
                # live_data_reduction runs the full Mantid pipeline; offload to thread pool
                # so the event loop (and GUI) stays responsive during the reduction.
                await loop.run_in_executor(
                    None, self.model.temporalanalysis.mtd_workflow.live_data_reduction
                )
                _trace("get_live_mtd_data done")
                print("============================================================================================")
                # Pull the latest UB out of the workflow so the side-table in the view refreshes.
                try:
                    self.model.temporalanalysis.sync_latest_ub_from_workflow()
                except Exception as e:
                    print(f"sync_latest_ub_from_workflow failed: {e}")
                await self._update_figures_async(loop)
                _trace("=== update temporal done ===")
                if (
                    self.model.eiccontrol.eic_auto_stop_strategy == "By Uncertainty"
                    and len(self.model.temporalanalysis.mtd_workflow.temporal_poisson_uncertainty) > 0
                ):
                    if (
                        self.model.temporalanalysis.mtd_workflow.temporal_poisson_uncertainty[-1]
                        < self.model.eiccontrol.eic_auto_stop_uncertainty_threshold
                    ):
                        print("stop_run")
                        self.stoprun()
                        self.model.temporalanalysis.mtd_workflow.temporal_poisson_uncertainty = []
                        self.model.temporalanalysis.mtd_workflow.timeseries_data_plt = []

                        continue
            except asyncio.CancelledError:
                print("Live update loop cancelled.")
                break
            except Exception as e:
                print(e)
            # self.update_temporalanalysis_figure()
            await asyncio.sleep(40)
        self.view_state.is_live_update_running = False
        self.view_state_bind.update_in_view(self.view_state)

    def update_newtabtemplate_figure(self, _: Any = None) -> None:
        self.newtabtemplate_bind.update_in_view(self.model.newtabtemplate)
        self.newtabtemplate_updatefig_bind.update_in_view(self.model.newtabtemplate.get_figure())

    def stoprun(self) -> None:
        ipts_number = self.model.experimentinfo.ipts_number
        instrument_name = self.model.experimentinfo.instrument
        self.model.eiccontrol.stop_run(ipts_number, instrument_name)
        self._push_eiccontrol()

    def poll_job_statuses(self) -> None:
        ipts_number = self.model.experimentinfo.ipts_number
        instrument_name = self.model.experimentinfo.instrument
        try:
            self.model.eiccontrol.poll_job_statuses(ipts_number, instrument_name)
        except Exception as e:
            print(f"Error polling job statuses: {e}")
        self._push_eiccontrol()

    def abort_job(self, scan_id: int) -> None:
        ipts_number = self.model.experimentinfo.ipts_number
        instrument_name = self.model.experimentinfo.instrument
        self.model.eiccontrol.abort_job(scan_id, ipts_number, instrument_name)
        self._push_eiccontrol()

    ##########################################################################################################################
    #  edit angle plans
    ##########################################################################################################################
    # import trame
    # trame_server=trame.app.get_server()

    # @trame_server.controller.trigger('add_run')
    def add_run(self) -> None:
        _trace("add_run")
        self.model.angleplan.is_editing_run = False
        self.model.angleplan.run_record = self.model.angleplan.get_default_run_record()
        self.model.angleplan.runedit_dialog = True
        #### should be called after change object in python and want to sync with js object
        self._push_angleplan()

    # trigger needed for passing js variable to fucntion call in view
    # @trame_server.controller.trigger('edit_run')
    def edit_run(self, run_id: int) -> None:
        _trace("edit_run", run_id)
        self.model.angleplan.is_editing_run = True
        run = next((r for r in self.model.angleplan.angle_list if r["id"] == run_id), None)
        if run:
            self.model.angleplan.run_record = run.copy()
            self.model.angleplan.runedit_dialog = True
        self._push_angleplan()

    def close_runedit_dialog(self) -> None:
        _trace("close_runedit_dialog")
        self.model.angleplan.runedit_dialog = False
        self._push_angleplan()

    # @trame_server.controller.trigger('save_run')
    def save_run(self) -> None:
        _trace("save_run")
        print(self.model.angleplan.run_record["id"])
        if self.model.angleplan.is_editing_run:
            for i, run in enumerate(self.model.angleplan.angle_list):
                if run["id"] == self.model.angleplan.run_record["id"]:
                    self.model.angleplan.angle_list[i] = self.model.angleplan.run_record.copy()
                    break
        else:
            max_id = max((r["id"] for r in self.model.angleplan.angle_list), default=0)
            self.model.angleplan.run_record["id"] = max_id + 1
            self.model.angleplan.angle_list.append(self.model.angleplan.run_record.copy())
        self.model.angleplan.runedit_dialog = False
        self._push_angleplan()

    # @trame_server.controller.trigger('remove_run')
    def remove_run(self, run_id: int) -> None:
        _trace("remove_run", run_id)
        self.model.angleplan.angle_list = [r for r in self.model.angleplan.angle_list if r["id"] != run_id]
        self._push_angleplan()

    ############################### coverage figure update ###########################################################
    def update_coverage_figure(self, _: Any = None) -> None:
        # self.temporalanalysis_updatefig_bind.update_in_view(self.model.temporalanalysis.get_figure_intensity(),self.model.temporalanalysis.get_figure_uncertainty())#noqa
        self.angleplan_updatefigure_coverage_bind.update_in_view(self.model.angleplan.get_figure_coverage())
        self._push_angleplan()

    def update_coverage_figure_with_symmetry(self, _: Any = None) -> None:
        self.angleplan_updatefigure_coverage_bind.update_in_view(
            self.model.angleplan.get_coverage_figure_with_symmetry()
        )
        self._push_angleplan()

    def get_coverage_figure_with_symmetry(self) -> None:
        _trace("get_coverage_figure_with_symmetry")
        fig = self.model.angleplan.get_coverage_figure_with_symmetry()
        self._push_angleplan()
        return fig

    def get_figure_coverage(self) -> go.Figure:
        _trace("get_figure_coverage")
        fig = self.model.angleplan.get_figure_coverage()
        self._push_angleplan()
        return fig

    def show_coverage(self) -> None:
        """Launch NeuXtalViz with the current angle plan.

        1. Export current angle_list to a temp CSV.
        2. Launch NXV via subprocess with --initialize-planner <UB> --open-plan <csv>.
        3. Spawn an async task that waits for NXV to exit, then reimports the CSV.
        """
        print("show_cov: exporting plan and launching NeuXtalViz")

        # Determine exchange CSV path (in the IPTS shared dir so NXV can also find it)
        plan_csv = os.path.join(tempfile.gettempdir(), "crystalpilot_nxv_plan.csv")

        # Export current strategy (may be empty — NXV will let user build from scratch)
        self.model.angleplan.export_to_nxv_csv(plan_csv)

        # UB matrix file from experiment info
        ub_file = getattr(self.model.experimentinfo, "UBFileName", "")

        # Build NXV launch command — NeuXtalViz-tools is a sibling repo
        _code_dir = os.path.dirname(os.path.abspath(__file__))
        # Walk up from view_models/ to CrystalPilot/, then go to sibling
        _project_root = os.path.normpath(os.path.join(_code_dir, "../../../.."))
        nxv_python = os.path.join(
            os.path.dirname(_project_root), "NeuXtalViz-tools", "src", "NeuXtalViz.py"
        )
        nxv_conda_env = "nxv"
        nxv_activate = os.path.expanduser("~/.miniforge/bin/activate")

        cmd_parts = [
            f"source '{nxv_activate}'",
            f"conda activate {nxv_conda_env}",
            f"python '{nxv_python}'",
        ]
        if ub_file and os.path.isfile(ub_file):
            cmd_parts[-1] += f" --initialize-planner '{ub_file}'"
        cmd_parts[-1] += f" --open-plan '{plan_csv}'"

        shell_cmd = " && ".join(cmd_parts)

        # Launch NXV as a subprocess and wait for it asynchronously
        self._nxv_plan_csv = plan_csv
        self._nxv_proc = subprocess.Popen(
            shell_cmd, shell=True, executable="/bin/bash"
        )
        print(f"show_cov: NXV launched (pid={self._nxv_proc.pid}), plan at {plan_csv}")

        # Schedule async reimport when NXV exits
        loop = asyncio.get_event_loop()
        loop.create_task(self._wait_for_nxv_and_reimport())

    async def _wait_for_nxv_and_reimport(self) -> None:
        """Wait for the NXV subprocess to exit, then reimport the edited CSV."""
        loop = asyncio.get_event_loop()
        # Wait in a thread so we don't block the event loop
        await loop.run_in_executor(None, self._nxv_proc.wait)
        print(f"show_cov: NXV exited (rc={self._nxv_proc.returncode})")

        plan_csv = self._nxv_plan_csv
        if os.path.isfile(plan_csv):
            self.model.angleplan.import_from_nxv_csv(plan_csv)
            self._push_angleplan()
            print(f"show_cov: reimported {len(self.model.angleplan.angle_list)} rows from {plan_csv}")
        else:
            print(f"show_cov: CSV not found at {plan_csv}, skipping reimport")

    def close_coverage(self) -> None:
        _trace("hide_cov")
        self.model.angleplan.is_showing_coverage = False
        self._push_angleplan()

    ############################### coverage figure update ###########################################################
    def reset_run(self) -> None:
        # if self.model.experimentinfo.c
        self.optimize_angleplan()
        _trace("reset_run")

        self._push_angleplan()
        _trace("reset_run after update view")

        pass

    def show_under_development_dialog(self) -> None:
        _trace("show_underdev")
        # self.model.angleplan.is_under_development = True
        self._push_view_state()

    def close_under_development_dialog(self) -> None:
        _trace("hide_underdev")
        self.view_state.is_under_development = False
        self._push_view_state()

    def optimize_angleplan(self) -> None:
        from .angle_plan import angleplan_optimize

        _trace("optimize_angleplan")
        ##self.is_uninterruptable = True
        ##self.update_view()
        final_angle_list = angleplan_optimize(self)
        ##self.is_uninterruptable = False
        ##self.update_view()
        # print('optimize done. final_angle_list',final_angle_list)

        # Per-point-group fallback angle lists.
        # Source data lives in app/fixtures/optimizer_fallback_angles.json
        # so this hot path stays maintainable.
        pg = self.model.experimentinfo.point_group
        fallback = _load_optimizer_fallback_angles().get(pg)
        if fallback is not None:
            final_angle_list = [tuple(row) for row in fallback]

        print(
            "update angle_list",
        )
        self.model.angleplan.angle_list = []
        for i in range(len(final_angle_list)):
            r = {
                "id": i + 1,
                "title": "pg:" + self.model.experimentinfo.point_group + "_" + str(i + 1),
                "comment": "resetted",
                "phi": float(final_angle_list[i][0]),
                "chi": float(final_angle_list[i][1]),
                "omega": float(final_angle_list[i][2]),
                "wait_for": "PCharge",
                "value": 1,
            }
            self.model.angleplan.angle_list.append(r)

        print("vm optimize done for angle_list", self.model.angleplan.angle_list)


"""
def angleplan_optimize(view_model:MainViewModel) -> None:
        import numpy as np
        from mantid.simpleapi import mtd
        import mantid.simpleapi as mtdapi

        #import NeuXtalViz.models.ap_test_v2 as ap_test_v2
        from ..model.angle_plan_engine_ import DetectorPane, DetectorInstrument, QGrids
        from ..model.angle_plan_engine_ import optimize_angle_with_fixed_given
        from ..model.angle_plan_engine_ import analyze_peaks
        #from ap_test_v2 import DetectorPane, DetectorInstrument, QGrids
        #from ap_test_v2 import optimize_angle_with_fixed_given as oa
        #from ap_test_v2 import analyze_peaks
        print('=========================================================================')
        print('==========================angle plan test================================')
        print('=========================================================================')

        instrument = view_model.model.experimentinfo.instrument
        wavelength = view_model.model.experimentinfo.wavelength
        axes = view_model.model.experimentinfo.axes
        limits = view_model.model.experimentinfo.limits
        UB = view_model.model.experimentinfo.UB
        d_min = view_model.model.experimentinfo.d_min
        d_max = view_model.model.experimentinfo.d_max
        offset = view_model.model.experimentinfo.offset
        point_group = view_model.model.experimentinfo.point_group
        lattice_centering = view_model.model.experimentinfo.lattice_centering


        print('self.instrument        ',instrument        )
        print('self.wavelength        ',wavelength        )
        print('self.axes              ',axes              )
        print('self.limits            ',limits            )
        print('self.UB                ',UB                )
        print('self.d_min             ',d_min             )
        print('self.d_max             ',d_max             )
        print('self.offset            ',offset            )
        print('self.point_group       ',point_group       )
        print('self.lattice_centering ',lattice_centering )

        #####################




        print('--------------------------peak input list--------------------------------')
        #print('peaks',peaks)
        print('--------------------------UB read--------------------------------')
        UB=np.array([[-0.06196579 ,-0.0646735 ,  0.00629365],
                     [ 0.05857223, -0.05941086, -0.03262031],
                     [ 0.02816059, -0.01873959,  0.08169699]])
        #if self.has_UB('coverage'):
        #    UB = mtd['coverage'].sample().getOrientedLattice().getUB().copy()
        #else:
        #    UB=np.array([[-0.06196579 ,-0.0646735 ,  0.00629365],
        #                 [ 0.05857223, -0.05941086, -0.03262031],
        #                 [ 0.02816059, -0.01873959,  0.08169699]])
        #print('UB',UB)

        print('--------------------------symmetry read--------------------------------')
        #laue='m-3'
        #print('Laue',laue)
        #symmetry = self.get_symmetry_transforms(laue)
        #print('symmtries:',symmetry)

        print('--------------------------euler angle range--------------------------------')
        print('--------------------------instrument setup--------------------------------')
        mtd.apiLoadEmptyInstrument(InstrumentName=instrument,
                            OutputWorkspace='instrument')

        mtd.apiExtractMonitors(InputWorkspace='instrument',
                        DetectorWorkspace='instrument',
                        MonitorWorkspace='montitors')

        mtdapi.PreprocessDetectorsToMD(InputWorkspace='instrument',
                                OutputWorkspace='detectors',
                                GetMaskState=False)

        L2 = np.array(mtd['detectors'].column(1)).reshape(-1, 256,256)
        two_theta =  np.array(mtd['detectors'].column(2)).reshape(-1, 256,256)
        az_phi =  np.array(mtd['detectors'].column(3)).reshape(-1, 256,256)
        print('L2',L2)

        #TODO: get L1 in cm
        #L1 = np.array(mtd['detectors'].column(1)).reshape(-1, 256,256)
        L1 = 1800

        x = L2*100*np.sin(two_theta)*np.cos(az_phi)
        y = L2*100*np.sin(two_theta)*np.sin(az_phi)
        z = L2*100*np.cos(two_theta)


        det_ins_parameter=[]
        num_pane=x.shape[0]
        for idx_pane in range(num_pane):
            pane_vertices=np.array([
                         [x[idx_pane, 0, 0],y[idx_pane, 0, 0],z[idx_pane, 0, 0]],
                         [x[idx_pane, 0,-1],y[idx_pane, 0,-1],z[idx_pane, 0,-1]],
                         [x[idx_pane,-1, 0],y[idx_pane,-1, 0],z[idx_pane,-1, 0]],
                         [x[idx_pane,-1,-1],y[idx_pane,-1,-1],z[idx_pane,-1,-1]]
                                    ])
            pane_vertices=np.array([
                         [x[idx_pane, 10, 10],y[idx_pane, 10, 10],z[idx_pane, 10, 10]],
                         [x[idx_pane, 10,-11],y[idx_pane, 10,-11],z[idx_pane, 10,-11]],
                         [x[idx_pane,-11, 10],y[idx_pane,-11, 10],z[idx_pane,-11, 10]],
                         [x[idx_pane,-11,-11],y[idx_pane,-11,-11],z[idx_pane,-11,-11]]
                                    ])
            #print('detector pane vertices:',pane_vertices)
            det_ins_parameter.append({'pane_id':idx_pane,'pane_shape':'rectangle','pane_parameter':{
                                                                'vertices':pane_vertices,'t_min':1000,'t_max':16000 }})
        #det_ins_parameter=[det_ins_parameter[0]]
        multi_detector_system = DetectorInstrument(det_ins_parameter)
        multi_detector_system.initialize_detector()
        #for det in multi_detector_system.detector_panes:
        #    print('detector pane id:',det.pane_id)
        #    print('detector pane qfaces:',det.qfaces)
        print('-------------------------grids setup-----------------------------')
        #Qmax=multi_detector_system.get_max_Q()
        #Qmin=multi_detector_system.get_min_Q()
        #Qmax=10
        #Qmin=0
        #grid_parameter={'Nx':10,'Ny':10,'Nz':10,'Qmax':Qmax,'Qmin':Qmin}
        #grids=QGrids(grid_mode='uniform',grid_parameter=grid_parameter)
        #print(grid_parameter)
        #print(grids.points.shape)


        qhmax=10
        qkmax=10
        qlmax=10
        qh=np.linspace(-qhmax,qhmax,2*qhmax+1)
        qk=np.linspace(-qkmax,qkmax,2*qkmax+1)
        ql=np.linspace(-qlmax,qlmax,2*qlmax+1)

        qhkl_irr_h,qhkl_irr_k,qhkl_irr_l=np.meshgrid(qh,qk,ql)
        #qhkl_irr_h,qhkl_irr_k,qhkl_irr_l=np.meshgrid(np.arange(qhmax),np.arange(qkmax),np.arange(qlmax),indexing='ij')

        qhkl_irr_h_flat=qhkl_irr_h.flatten()
        qhkl_irr_k_flat=qhkl_irr_k.flatten()
        qhkl_irr_l_flat=qhkl_irr_l.flatten()
        #qhkl_irr=np.column_stack((qhkl_irr_h_flat,qhkl_irr_k_flat,qhkl_irr_l_flat)).T
        qhkl_irr=np.column_stack((qhkl_irr_h_flat,qhkl_irr_k_flat,qhkl_irr_l_flat))

        print('qhkl_irr shape',qhkl_irr.shape)

        pg = mtdapi.PointGroupFactory.createPointGroup(point_group )
        so=pg.getSymmetryOperations()
        #qhkl_sym_list=[]
        qlab_sym_list=[]
        for sym in so:
            qhkl_sym=[sym.transformHKL(q) for q in qhkl_irr]
            qlab=np.array(qhkl_sym)@(UB).T
            #qhkl_sym_list.append(qlab)
            qlab_sym_list.append(qlab)


        #print('qhkl_sym_list length and shape',len(qhkl_sym_list),qhkl_sym_list[-1].shape)
        print('qlab_sym_list length and shape',len(qlab_sym_list),qlab_sym_list[-1].shape)


        grid_parameter={'num_sym':len(qlab_sym_list),'qlist':qlab_sym_list}
        #grid_parameter={'Nx':10,'Ny':10,'Nz':10,'Qmax':Qmax,'Qmin':Qmin}
        grids=QGrids(grid_mode='input',grid_parameter=grid_parameter)
        print('grids shape',grids.points[0].shape)

        print('-------------------------initial coverage calculation-----------------------------')
        print('coverage calculation')

        coverage_results=grids.get_coverage(multi_detector_system)
        #print(grids.mask.shape)
        print('initial coverage',np.sum(coverage_results)*100/np.size(coverage_results),'%')
        #print(grids.points.shape)
        #print(grids.points[:100,:])
        #print('shape coverage',coverage_results.shape)
        #print(coverage_results[:100,:])

        print('-------------------------analyze peak-----------------------------')
        #peaks_list=[peak for peak in peaks.values()]
        #analyze_peaks(peaks_list,UB,multi_detector_system,symmetry)

        print('-------------------------ask for and set initial angles list-----------------------------')
        print('            ---------------------not implemented---------------------------')
        print('-------------------------optimize angle-----------------------------')
        fixed_angle_list= np.array([ [0,135,0]])
        print('fixed_angle_list:',fixed_angle_list)
        euler_angle_range=[[0,360,1],[135,135,1],[0,360,1]]
        final_angle_list,final_coverage=optimize_angle_with_fixed_given(grids,multi_detector_system,fixed_angle_list,euler_angle_range)
        print("Detector Coverage Results: ", np.sum(final_coverage)/np.size(final_coverage)*100,'%')
        return final_angle_list

        exit('debug')
        print('------------------------- visualizie-----------------------------')
        ## Define vertices
        #vertices = np.array([
        #    [0, 0, 0],
        #    [1, 0, 0],
        #    [1, 1, 0],
        #    [0, 1, 0],
        #    [0, 0, 1],
        #    [1, 0, 1],
        #    [1, 1, 1],
        #    [0, 1, 1],
        #])

        ## Define faces
        #faces = np.array([
        #    [4, 0, 1, 2, 3],  # bottom
        #    [4, 4, 5, 6, 7],  # top
        #    [4, 0, 1, 5, 4],  # front
        #    [4, 1, 2, 6, 5],  # right
        #    [4, 2, 3, 7, 6],  # back
        #    [4, 3, 0, 4, 7],  # left
        #])




        #self.polyhedron_data=[]
        #for pane in multi_detector_system.detector_panes:
        #    vr=np.array(pane.rvertices)
        #    sr= np.array([ [4, 0, 1, 3, 2]])
        #    vq=np.array(pane.qfaces['0']+pane.qfaces['5'])
        #    sq= np.array([
        #                   [4, 0, 1, 3, 2],  # bottom
        #                   [4, 4, 5, 7, 6],  # top
        #                   [4, 0, 1, 5, 4],  # front
        #                   [4, 1, 3, 7, 5],  # right
        #                   [4, 3, 2, 6, 7],  # back
        #                   [4, 2, 0, 4, 6],  # left
        #                     ])
        #    self.polyhedron_data.append([vq,sq])
        #    #self.polyhedron_data.append([vr,sr])

        ##self.polyhedron_data=[vertices,faces]
        ##self.polyhedron_data=[[vertices,faces],[vertices+.5,faces]]
        #self.polyhedron_data.append([grids.points,np.array([ [0 ]])])
        ##print(self.polyhedron_data)

 #


"""
