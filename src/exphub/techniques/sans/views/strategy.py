"""SANS strategy / experiment-steering tab view (P4.2).

The SANS analogue of the single-crystal
:class:`~exphub.techniques.single_crystal.views.angle_plan.AnglePlanView`
strategy surface. It keeps the editable-CSV-table + row-edit-dialog + EIC
submit/auth idiom, but in the SANS shape:

  - the data-table columns are SANS instrument-configuration parameters
    (``sample_aperture`` / ``detector_distance`` / ``attenuator`` /
    ``wavelength_spread``) instead of goniometer angles (column names
    provisional — TBD with the SANS scientist)
  - there is **no** goniometer selector, no coverage / symmetry dialog, and no
    UB-driven "Initialize Strategy" optimizer (SANS has no reciprocal lattice)

EIC submission reuses the shared pipeline (decision #1). The SANS EIC
row-builder is TBD, so the steering VM's ``submit_strategy`` reports
"not yet configured" until it lands; the button is wired regardless so the
plumbing is in place.

Binds the strategy model under ``model_strategy`` and the shared EIC control
model under ``model_eiccontrol``.
"""

import trame
from nova.trame.view.components import InputField, RemoteFileInput
from nova.trame.view.layouts import GridLayout, HBoxLayout, VBoxLayout
from trame.widgets import html
from trame.widgets import vuetify3 as vuetify

from ..models.strategy import SANS_PARAM_COLUMNS
from ..view_models.steering import SansSteeringViewModel


class SansStrategyView:
    """View class for the SANS experiment-strategy tab."""

    def __init__(self, view_model: SansSteeringViewModel) -> None:
        self.view_model = view_model
        self.view_model.strategy_bind.connect("model_strategy")
        self.view_model.eiccontrol_bind.connect("model_eiccontrol")
        self.create_ui()

    def create_ui(self) -> None:
        trame_server = trame.app.get_server()

        @trame_server.controller.trigger("sans_edit_run")
        def edit_run(run_id: int) -> None:
            self.view_model.edit_run(run_id)

        @trame_server.controller.trigger("sans_remove_run")
        def remove_run(run_id: int) -> None:
            self.view_model.remove_run(run_id)

        @trame_server.controller.trigger("sans_save_run")
        def save_run() -> None:
            self.view_model.save_run()

        @trame_server.controller.trigger("sans_abort_job")
        def abort_job(scan_id: int) -> None:
            self.view_model.abort_job(scan_id)

        with GridLayout(columns=1, gap="0.5em"):
            InputField(v_model="model_strategy.plan_name")

        with HBoxLayout(gap="0.5em"):
            RemoteFileInput(
                v_model="model_strategy.plan_file",
                base_paths=["/HFIR", "/SNS"],
                extensions=[".csv"],
            )
            vuetify.VBtn("Upload Strategy", click=self.view_model.upload_strategy, style="align-self: center;")

        vuetify.VCardTitle("SANS Experiment Run Strategy")
        with VBoxLayout(classes="border-lg border-primary mb-1", stretch=True):
            with vuetify.VDataTable(
                classes="flex-1-1",
                headers=("model_strategy.strategy_headers", []),
                items=("model_strategy.strategy_list", []),
            ):
                with vuetify.Template(raw_attrs=['v-slot:item.actions="{ item }"']):
                    with html.Div(classes="d-flex justify-end"):
                        with vuetify.VBtn(icon=True, size="small", click="trigger('sans_edit_run', [item.id])"):
                            vuetify.VIcon("mdi-pencil")
                        with vuetify.VBtn(icon=True, size="small", click="trigger('sans_remove_run', [item.id])"):
                            vuetify.VIcon("mdi-delete")

        self._build_runedit_dialog()

        with HBoxLayout(gap="0.5em", halign="center"):
            vuetify.VBtn(
                "Add a Run",
                prepend_icon="mdi-plus",
                click=self.view_model.add_run,
            )

        # EIC authenticate + submit row (shared pipeline; SANS row-builder TBD).
        with HBoxLayout(gap="0.5em", valign="center"):
            RemoteFileInput(v_model="model_eiccontrol.token_file", base_paths=["/HFIR", "/SNS"])
            vuetify.VBtn("Authenticate", click=self.view_model.call_load_token)
            InputField(v_model="model_eiccontrol.is_simulation", type="checkbox")
            vuetify.VBtn("Submit through EIC", click=self.view_model.submit_strategy)
            vuetify.VChip(
                "{{ model_eiccontrol.eic_status }}",
                color="model_eiccontrol.eic_status === 'authenticated successfully' ? 'blue'"
                " : model_eiccontrol.eic_status === 'jobs submitted' ? 'green'"
                " : model_eiccontrol.eic_status === 'job submission simulated' ? 'orange'"
                " : model_eiccontrol.eic_status.startsWith('submission failed') || model_eiccontrol.eic_status.startsWith('authentication failed') ? 'red'"  # noqa: E501
                " : 'grey'",
                variant="flat",
                style="font-weight: bold;",
            )

        with GridLayout(columns=4, gap="0.5em"):
            InputField(
                v_model="model_eiccontrol.eic_auto_stop_strategy",
                type="select",
                items="model_eiccontrol.eic_auto_stop_strategy_options",
            )
            InputField(v_model="model_eiccontrol.eic_auto_stop_uncertainty_threshold")
            InputField(v_model="model_eiccontrol.eic_submission_scan_id", label="Scan ID")
            vuetify.VBtn("Manual Stop Run", click=self.view_model.stoprun, style="align-self: center;")

        vuetify.VCardTitle("Submitted Jobs")
        with HBoxLayout(gap="0.5em", halign="center"):
            vuetify.VBtn(
                "Refresh Status",
                prepend_icon="mdi-refresh",
                click=self.view_model.poll_job_statuses,
            )

        with VBoxLayout(classes="border-lg border-primary mb-1", stretch=True):
            with vuetify.VDataTable(
                classes="flex-1-1",
                headers=("model_eiccontrol.submitted_jobs_headers", []),
                items=("model_eiccontrol.submitted_jobs", []),
            ):
                with vuetify.Template(raw_attrs=['v-slot:item.status="{ item }"']):
                    vuetify.VChip(
                        "{{ item.status }}",
                        color="item.status === 'done' ? 'green'"
                        " : item.status === 'running' ? 'blue'"
                        " : item.status === 'submitted' ? 'orange'"
                        " : item.status === 'aborted' ? 'grey'"
                        " : item.status === 'failed' || item.status === 'error' ? 'red'"
                        " : 'default'",
                        variant="flat",
                        size="small",
                    )
                with vuetify.Template(raw_attrs=['v-slot:item.actions="{ item }"']):
                    with vuetify.VBtn(
                        icon=True,
                        size="small",
                        click="trigger('sans_abort_job', [item.scan_id])",
                        disabled="item.status === 'done' || item.status === 'aborted' || item.status === 'failed'",
                    ):
                        vuetify.VIcon("mdi-stop-circle-outline")

    def _build_runedit_dialog(self) -> None:
        """Add/Edit-a-run dialog with SANS instrument-configuration fields.

        Column names are provisional (TBD with the SANS scientist). The field
        list is generated from ``SANS_PARAM_COLUMNS`` so the dialog stays in
        step with the model's strategy-row schema.
        """
        with vuetify.VDialog(v_model="model_strategy.runedit_dialog", max_width="500px"):
            with vuetify.VCard():
                vuetify.VCardTitle("{{ model_strategy.is_editing_run ? 'Edit' : 'Add' }} a Run")
                vuetify.VCardSubtitle("{{ model_strategy.is_editing_run ? 'Update' : 'Create' }} SANS strategy step")
                with vuetify.VCardText():
                    vuetify.VTextField(
                        v_model="model_strategy.run_record['title']",
                        label="Title",
                        variant="outlined",
                        update_modelValue="flushState('model_strategy')",
                    )
                    vuetify.VTextField(
                        v_model="model_strategy.run_record.comment",
                        label="Comment",
                        variant="outlined",
                        update_modelValue="flushState('model_strategy')",
                    )
                    # SANS instrument-configuration parameters (provisional names).
                    for col in SANS_PARAM_COLUMNS:
                        vuetify.VTextField(
                            v_model=f"model_strategy.run_record.{col}",
                            label=col,
                            type="number",
                            variant="outlined",
                            update_modelValue="flushState('model_strategy')",
                        )
                    vuetify.VSelect(
                        v_model="model_strategy.run_record.wait_for",
                        items=("model_strategy.wait_for_list", []),
                        label="Wait For",
                        variant="outlined",
                        update_modelValue="flushState('model_strategy')",
                    )
                    vuetify.VTextField(
                        v_model="model_strategy.run_record.value",
                        label="Value",
                        type="number",
                        variant="outlined",
                        update_modelValue="flushState('model_strategy')",
                    )
                with vuetify.VCardActions():
                    vuetify.VBtn("Cancel", click=self.view_model.close_runedit_dialog, style="align-self: center;")
                    vuetify.VSpacer()
                    vuetify.VBtn("Save", click="trigger('sans_save_run')")
