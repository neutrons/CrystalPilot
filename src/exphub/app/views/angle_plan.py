from typing import List, Dict
from nova.trame.view.components import InputField,RemoteFileInput
from ..view_models.main import MainViewModel
from nova.trame.view.layouts import GridLayout, HBoxLayout
from trame.widgets import vuetify3 as vuetify
from trame.widgets import html
import trame

class AnglePlanView:

    def __init__(self,view_model:MainViewModel) -> None:
        self.view_model = view_model
        #self.view_model.angleplan_bind.connect("model.angleplan")
        self.view_model.angleplan_bind.connect("model_angleplan")
        self.view_model.eiccontrol_bind.connect("model_eiccontrol")
        self.is_editing = False
        self.create_ui()

    def create_ui(self) -> None:
        #with vuetify.VRow():
        trame_server=trame.app.get_server()
        @trame_server.controller.trigger("edit_run")
        def edit_run(run_id:int):
            #state.is_editing = True
            #book = next((b for b in state.books if b["id"] == book_id), None)
            #if book:
            #    state.record = book.copy()
            #    state.dialog = True
            print("view id",run_id)
            self.view_model.edit_run(run_id)
        
        @trame_server.controller.trigger("remove_run")
        def remove_run(run_id:int):
            #state.books = [b for b in state.books if b["id"] != book_id]
            print("view id",run_id)
            self.view_model.remove_run(run_id)

        @trame_server.controller.trigger("save_run")
        def save_run():
            #state.books = [b for b in state.books if b["id"] != book_id]
            #self.view_model.save_run()
            self.view_model.save_run()



        with GridLayout(columns=2):
            InputField(v_model="model_angleplan.plan_name")#, type="button", label="Upload")
            InputField(v_model="model_angleplan.plan_type", type="select", items="model_angleplan.plan_type_list")
        with GridLayout(columns=2):
            RemoteFileInput(v_model="model_eiccontrol.token_file", base_paths=["/HFIR", "/SNS"])
            vuetify.VBtn("Authenticate", click=self.view_model.call_load_token, style="align-self: center;")
        with GridLayout(columns=2):
            RemoteFileInput(
                    v_model="model_angleplan.plan_file",
                    base_paths=["/HFIR", "/SNS",],
                    #base_paths=["/HFIR", "/SNS", "/home/zx5/1-todo/6-hardware/"],
                    extensions=[".csv"],
                )
            vuetify.VBtn("Upload Strategy", click=self.view_model.upload_strategy, style="align-self: center;")

        #vuetify.VCardTitle("CrystalPlan Table")
        
        with vuetify.VSheet(classes="pa-4"):
            with vuetify.VDataTable(
                headers=("model_angleplan.angle_list_headers",[]), #TODO trame syntax, 
                items=("model_angleplan.angle_list",[]),
            ):
                    with vuetify.Template(v_slot_top=True):
                    #with vuetify.Template(v_slot_bottom=True):
                        with vuetify.VToolbar(flat=True):
                            vuetify.VToolbarTitle("Experiment Run Strategy")
                            vuetify.VSpacer()
                            vuetify.VBtn(
                                "Add a Run",
                                prepend_icon="mdi-plus",
                                click=self.view_model.add_run,
                                #click="trigger('add_run')",
                            )

                    with vuetify.Template(raw_attrs=['v-slot:item.actions="{ item }"']): #TODO 'item' predefined by vuetify
                        with html.Div(classes="d-flex justify-end"):

                            with vuetify.VBtn(icon=True, size="small", click="trigger('edit_run', [item.id])"):
                            #with vuetify.VBtn(icon=True, size="small", click="trigger('edit_run', [item.id])"):
                                vuetify.VIcon("mdi-pencil")
                            with vuetify.VBtn(icon=True, size="small", click="trigger('remove_run', [item.id])"):
                            #with vuetify.VBtn(icon=True, size="small", click="trigger('delete_run', [item.id])"):
                                vuetify.VIcon("mdi-delete")


        with vuetify.VDialog(v_model="model_angleplan.runedit_dialog", max_width="500px"): # only v_modle and inputfield-items auto wrap string to js,
            with vuetify.VCard():
                vuetify.VCardTitle(
                    "{{ model_angleplan.is_editing_run ? 'Edit' : 'Add' }} a Run" #todo handle bar syntax
                )
                vuetify.VCardSubtitle(
                    "{{ model_angleplan.is_editing_run ? 'Update' : 'Create' }} run strategy"
                )
                with vuetify.VCardText():
                        vuetify.VTextField(
                            v_model="model_angleplan.run_record['title']", label="Title",
                            update_modelValue="flushState('model_angleplan')"
                        )
                        vuetify.VTextField(
                            v_model="model_angleplan.run_record.comment", label="Comment",
                            update_modelValue="flushState('model_angleplan')"
                        )
                        vuetify.VTextField(
                            v_model="model_angleplan.run_record.phi", label="phi", type="number",
                            update_modelValue="flushState('model_angleplan')"
                        )
                        vuetify.VTextField(
                            v_model="model_angleplan.run_record.omega", label="omega", type="number",
                            update_modelValue="flushState('model_angleplan')"   
                        ) 
                        vuetify.VSelect(
                            v_model="model_angleplan.run_record.wait_for",
                            items=["PCharge", "seconds"],
                            label="Wait For",
                            update_modelValue="flushState('model_angleplan')"   
                        )
                        vuetify.VTextField(
                            v_model="model_angleplan.run_record.value", label="Value", type="number"
                            update_modelValue="flushState('model_angleplan')"   
                        )
                        vuetify.VTextField(
                            v_model="model_angleplan.run_record.or_time", label="Or Time", type="number"
                            update_modelValue="flushState('model_angleplan')"   
                        )
                with vuetify.VCardActions():
                    vuetify.VBtn("Cancel", click="model_angleplan.runedit_dialog = False")
                    vuetify.VSpacer()
                    vuetify.VBtn("Save", click="trigger('save_run')")
                    #vuetify.VBtn("Save", click="trigger('save_run')")


        #with GridLayout(columns=7):
        #    vuetify.VListItem(v_for="header in model_angleplan.headers", v_text="header")
        #    vuetify.VRow(
        #        v_for="(angle, index) in model_angleplan.angle_list",
        #        key="index",
        #        children=[
        #        vuetify.VRow(
        #            v_for="(key, keyindex) in angle",
        #            children=[
        #                vuetify.VTextField(
        #                v_model="key",
        #                #v_model=f"model_angleplan.angle_list[0][""Comment""]",
        #                #v_model="key",
        #                #label=f"Angle: {key}",
        #                dense=True,
        #                hide_details=True
        #                )
        #            ]
        #        )
        #        ]
        #    )
 
        #vuetify.VRow(v_for="header in model_angleplan.headers", v_text="header")
        print("model_angleplan.angle_list")
        print(self.view_model.model.angleplan.angle_list)
        print(len(self.view_model.model.angleplan.angle_list))
        
        #with vuetify.VRow( v_for="(angle, index) in model_angleplan.angle_list_pd",):
        #    InputField(v_model="model_angleplan.angle_list_pd[index].phi")
        #    InputField(v_model="model_angleplan.angle_list_pd[index].omega")
 
        with GridLayout(columns=3):
            InputField(v_model="model_eiccontrol.is_simulation", type="checkbox")
            vuetify.VBtn("Update Strategy", click=self.view_model.update_view, style="align-self: center;")
            vuetify.VBtn("Submit through EIC", click=self.view_model.submit_angle_plan, style="align-self: center;")

        #InputField(v_model="model_eiccontrol.IPTS_number")
        #InputField(v_model="model_eiccontrol.instrument_name")

        with GridLayout(columns=1):
            vuetify.VBanner(
                    v_if="model_eiccontrol.eic_submission_success",
                    text="Submission Successful.",
                    #text="Submission Successful. Scan ID: {{model_eiccontrol.eic_submission_scan_id}}, Message: {{model_eiccontrol.eic_submission_message}}",
                    color="success",
                )
        with GridLayout(columns=4):
            
            InputField(v_model="model_eiccontrol.eic_auto_stop_strategy", type="select", items="model_eiccontrol.eic_auto_stop_strategy_options")
            InputField(v_model="model_eiccontrol.eic_auto_stop_uncertainty_threshold")
            InputField(v_model="model_eiccontrol.eic_submission_scan_id", label="Scan ID")
            vuetify.VBtn("Manual Stop Run", click=self.view_model.stoprun, style="align-self: center;")