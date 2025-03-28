"""Module for the main ViewModel."""

from typing import Any, Dict
import time
from nova.mvvm.interface import BindingInterface


from ..models.main_model import MainModel
from ..models.angle_plan import AnglePlanModel
from ..models.experiment_info import ExperimentInfoModel
from ..models.eic_control import EICControlModel
from ..models.newtabtemplate import NewTabTemplateModel

#from ..models.plotly import PlotlyConfig
#from pyvista import Plotter  # just for typing
#from ..models.pyvista import PyVistaConfig

from trame.app.asynchronous import create_task
import asyncio

#from ..models.css_status import CSSStatusModel
#from ..models.temporal_analysis import TemporalAnalysisModel    



class MainViewModel:
    """Viewmodel class, used to create data<->view binding and react on changes from GUI."""

    def __init__(self, model: MainModel, binding: BindingInterface):
        self.model = model
        #self.angleplan = AnglePlanModel()

        # here we create a bind that connects ViewModel with View. It returns a communicator object,
        # that allows to update View from ViewModel (by calling update_view).
        # self.model will be updated automatically on changes of connected fields in View,
        # but one also can provide a callback function if they want to react to those events
        # and/or process errors.
        self.model_bind = binding.new_bind(self.model, callback_after_update=self.change_callback)

        #self.experimentinfo_bind = binding.new_bind(self.model.experimentinfo, callback_after_update=self.change_callback)
        self.experimentinfo_bind = binding.new_bind(self.model.experimentinfo, callback_after_update=self.update_experimentinfo_options)
        self.angleplan_bind = binding.new_bind(self.model.angleplan, callback_after_update=self.change_callback)
        self.eiccontrol_bind = binding.new_bind(self.model.eiccontrol, callback_after_update=self.change_callback)
        #self.temporalanalysis_bind = binding.new_bind(self.model.temporalanalysis, callback_after_update=self.change_callback)
        self.temporalanalysis_bind = binding.new_bind(self.model.temporalanalysis, callback_after_update=self.update_temporalanalysis_figure)

        #self.cssstatus_bind = binding.new_bind(self.model.cssstatus, callback_after_update=self.change_callback)
        self.cssstatus_bind = binding.new_bind(self.model.cssstatus, callback_after_update=self.update_cssstatus_figure)
        self.cssstatus_updatefig_bind = binding.new_bind()
        self.temporalanalysis_updatefigure_uncertainty_bind = binding.new_bind()
        self.temporalanalysis_updatefigure_intensity_bind = binding.new_bind()
######################################################################################################################################################
# wrong
#        self.newtabtemplate_bind = binding.new_bind(self.model.newtabtemplate, callback_after_update=self.change_callback)
#        self.newtabtemplate_updatefig_bind = binding.new_bind(self.model.newtabtemplate, callback_after_update=self.update_newtabtemplate_figure)
######################################################################################################################################################
        self.newtabtemplate_bind = binding.new_bind(self.model.newtabtemplate,
                                                callback_after_update=self.update_newtabtemplate_figure)
        self.newtabtemplate_updatefig_bind = binding.new_bind()
######################################################################################################################################################

        #self.pyvista_config = PyVistaConfig()

        #self.plotly_config_bind = binding.new_bind(
        #    linked_object=self.plotly_config, callback_after_update=self.update_plotly_figure
        #)
        #self.plotly_figure_bind = binding.new_bind(linked_object=self.plotly_config)
        #self.pyvista_config_bind = binding.new_bind(linked_object=self.pyvista_config)


        #self.create_auto_update_cssstatus_figure()




    #def update_experimentinfo_options(self, _: Any = None) -> None:
    def  update_experimentinfo_options(self, results: Dict[str, Any]) -> None:
        self.model.experimentinfo.update_option_lists()
        self.experimentinfo_bind.update_in_view(self.model.experimentinfo)
        print("update_experimentinfo_options")
        print(self.model.experimentinfo.options)
        if results["error"]:
            print(f"error in fields {results['errored']}, model not changed")
        else:
            print(f"model fields updated: {results['updated']}")
        #time.sleep(7)

    def change_callback(self, results: Dict[str, Any]) -> None:
        if results["error"]:
            print(f"error in fields {results['errored']}, model not changed")
        else:
            print(f"model fields updated: {results['updated']}")

    def upload_strategy(self) -> None:
        self.model.angleplan.load_ap(self.model.angleplan.plan_file)
        self.update_view()

    def update_view(self) -> None:
        #self.model_bind.update_in_view(self.model)
        self.angleplan_bind.update_in_view(self.model.angleplan)
        self.eiccontrol_bind.update_in_view(self.model.eiccontrol)
        self.cssstatus_bind.update_in_view(self.model.cssstatus)
        
######################################################################################################################################################
        #self.newtabtemplate_bind.update_in_view(self.model.newtabtemplate)
######################################################################################################################################################
        #print(self.model.angleplan.test_list)

    def submit_angle_plan(self) -> None:
        #print("submit_angle_plan")
        self.model.eiccontrol.submit_eic(self.model.angleplan.angle_list)
        self.update_view()

    def call_load_token(self) -> None:
        self.model.eiccontrol.load_token(self.model.eiccontrol.token_file)
        self.update_view()
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
        self.cssstatus_bind.update_in_view(self.model.cssstatus)
        self.cssstatus_updatefig_bind.update_in_view(self.model.cssstatus.get_figure())
        #time.sleep(7)

    async def auto_update_cssstatus_figure(self) -> None:
        while True:
            self.update_cssstatus_figure()
            await asyncio.sleep(1)

    def create_auto_update_cssstatus_figure(self) -> None:
        asyncio.create_task(self.auto_update_cssstatus_figure())        


 
    def update_temporalanalysis_figure(self, _: Any = None) -> None:
        #self.temporalanalysis_updatefig_bind.update_in_view(self.model.temporalanalysis.get_figure_intensity(),self.model.temporalanalysis.get_figure_uncertainty())
        self.temporalanalysis_updatefigure_intensity_bind.update_in_view(self.model.temporalanalysis.get_figure_intensity())
        self.temporalanalysis_updatefigure_uncertainty_bind.update_in_view(self.model.temporalanalysis.get_figure_uncertainty())
        self.temporalanalysis_bind.update_in_view(self.model.temporalanalysis)
        #time.sleep(7)

    async def auto_update_temporalanalysis_figure(self) -> None:
        while True:
            self.update_temporalanalysis_figure()
            await asyncio.sleep(1)

    def create_auto_update_temporalanalysis_figure(self) -> None:
        self.model.temporalanalysis.start_reading_live_mtd_data()
        asyncio.create_task(self.get_live_mtd_data()) 
        #asyncio.create_task(self.auto_update_temporalanalysis_figure()) 


    async def get_live_mtd_data(self) -> None:
        while True:
            print("============================================================================================")
            print("get_live_mtd_data")
            try:
                #self.update_temporalanalysis_figure()
                self.model.temporalanalysis.mtd_workflow.live_data_reduction()
                print("get_live_mtd_data done")
                print("============================================================================================")
                self.update_temporalanalysis_figure()
                print("=====================update temporal done=======================================================================")
                if self.model.eiccontrol.eic_auto_stop_strategy=="By Uncertainty" and len(self.model.temporalanalysis.mtd_workflow.temporal_poisson_uncertainty)>0:
                  if self.model.temporalanalysis.mtd_workflow.temporal_poisson_uncertainty[-1]<self.model.eiccontrol.eic_auto_stop_uncertainty_threshold:
                    print("stop_run")
                    self.stoprun()
                    self.model.temporalanalysis.mtd_workflow.temporal_poisson_uncertainty=[]
                    self.model.temporalanalysis.mtd_workflow.timeseries_data_plt=[]

                    continue
            except Exception as e:
                print(e)
            #self.update_temporalanalysis_figure()
            await asyncio.sleep(40)
        


    def update_newtabtemplate_figure(self, _: Any = None) -> None:
        self.newtabtemplate_bind.update_in_view(self.model.newtabtemplate)
        self.newtabtemplate_updatefig_bind.update_in_view(self.model.newtabtemplate.get_figure())

    def stoprun(self) -> None:
        self.model.eiccontrol.stop_run()
        self.update_view()
        pass


##########################################################################################################################
#  edit angle plans
##########################################################################################################################
    #import trame
    #trame_server=trame.app.get_server()

    #@trame_server.controller.trigger('add_run')
    def add_run(self) -> None:
        print("add_run")
        self.model.angleplan.is_editing_run = False
        self.model.angleplan.run_record = self.model.angleplan.get_default_run_record()
        self.model.angleplan.runedit_dialog = True
        #### should be called after change object in python and want to sync with js object
        self.update_view()

    # trigger needed for passing js variable to fucntion call in view
    #@trame_server.controller.trigger('edit_run')
    def edit_run(self,run_id):
        print("edit_run")
        print(run_id)
        self.model.angleplan.is_editing_run = True
        run = next((r for r in self.model.angleplan.angle_list if r["id"] == run_id), None)
        if run:
            self.model.angleplan.run_record = run.copy()
            self.model.angleplan.runedit_dialog = True
        self.update_view()

    #@trame_server.controller.trigger('save_run')
    def save_run(self) -> None:
        print("save_run")
        print(self.model.angleplan.run_record["id"])
        if self.model.angleplan.is_editing_run:
            for i, run in enumerate(self.model.angleplan.angle_list):
                if run["id"] == self.model.angleplan.run_record["id"]:
                    self.model.angleplan.angle_list[i] = self.model.angleplan.run_record.copy()
                    break
        else:
            self.model.angleplan.run_record["id"] = len(self.model.angleplan.angle_list) + 1
            self.model.angleplan.angle_list.append(self.model.angleplan.run_record.copy())
        self.model.angleplan.runedit_dialog = False
        self.update_view()

    #@trame_server.controller.trigger('remove_run')
    def remove_run(self,run_id):
        print("remove_run")
        print(run_id)
        self.model.angleplan.angle_list = [r for r in self.model.angleplan.angle_list if r["id"] != run_id]
        print(self.model.angleplan.angle_list)
        self.update_view()

