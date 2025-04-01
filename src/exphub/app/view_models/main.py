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

import numpy as np
import plotly.graph_objects as go


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
        self.is_under_development = False
        self.is_under_development_bind = binding.new_bind(self.is_under_development)
        self.is_uninterruptable = False
        self.is_uninterruptable_bind = binding.new_bind(self.is_uninterruptable)

        #self.pyvista_config = PyVistaConfig()

        #self.plotly_config_bind = binding.new_bind(
        #    linked_object=self.plotly_config, callback_after_update=self.update_plotly_figure
        #)
        #self.plotly_figure_bind = binding.new_bind(linked_object=self.plotly_config)
        #self.pyvista_config_bind = binding.new_bind(linked_object=self.pyvista_config)


        #self.create_auto_update_cssstatus_figure()

        self.angleplan_updatefigure_coverage_bind = binding.new_bind()



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
        self.is_under_development_bind.update_in_view(self.is_under_development)
        self.is_uninterruptable_bind.update_in_view(self.is_uninterruptable)
        self.temporalanalysis_bind.update_in_view(self.model.temporalanalysis)
        
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
    def close_runedit_dialog(self) -> None:
        print("close_runedit_dialog")
        self.model.angleplan.runedit_dialog = False
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

############################### coverage figure update ###########################################################
    def update_coverage_figure(self, _: Any = None) -> None:
        #self.temporalanalysis_updatefig_bind.update_in_view(self.model.temporalanalysis.get_figure_intensity(),self.model.temporalanalysis.get_figure_uncertainty())
        self.angleplan_updatefigure_coverage_bind.update_in_view(self.model.angleplan.get_figure_coverage())
        self.update_view()

    def update_coverage_figure_with_symmetry(self, _: Any = None) -> None:
        self.angleplan_updatefigure_coverage_bind.update_in_view(self.model.angleplan.get_coverage_figure_with_symmetry())
        self.update_view()


    def get_coverage_figure_with_symmetry(self) -> None:
        print("get_coverage_figure_with_symmetry")
        fig=self.model.angleplan.get_coverage_figure_with_symmetry()
        self.update_view()
        return fig
    
    def get_figure_coverage(self) -> None:
        print("get_figure_coverage")
        fig=self.model.angleplan.get_figure_coverage()
        self.update_view()
        return fig

    def show_coverage(self):
        print("show_cov")
        self.model.angleplan.is_showing_coverage = True
        self.update_view()
    def close_coverage(self):
        print("hide_cov")
        self.model.angleplan.is_showing_coverage = False
        self.update_view()

############################### coverage figure update ###########################################################
    def reset_run(self):
        #if self.model.experimentinfo.c
        self.optimize_angleplan()
        print("reset_run")
        print(self.model.angleplan.angle_list)
        print(self.model.angleplan.qpane_cones)
        
        self.update_view()
        print("reset_run after update view")

        pass
    def show_under_development_dialog(self):
        print("show_underdev")
        self.model.angleplan.is_under_development = True
        self.update_view()
    def close_under_development_dialog(self):
        print("hide_underdev")
        self.is_under_development = False
        self.update_view()

    def optimize_angleplan(self):
        from .angle_plan import angleplan_optimize
        print("optimize_angleplan")
        ##self.is_uninterruptable = True
        ##self.update_view()
        final_angle_list=angleplan_optimize(self)
        ##self.is_uninterruptable = False
        ##self.update_view()
        #print('optimize done. final_angle_list',final_angle_list)

        if self.model.experimentinfo.pointGroup == "1":
            final_angle_list=[(0,135,0), (10, 135, 0),(69.0, 135,5.0),(95.0, 135,43.0),(97.0, 135,82.0),(129.0, 135,100.0),(136.0, 135,124.0),
                     (142.0, 135,140.0),(145.0, 135,152.0),(157.0, 135,190.0),(190.0, 135,220.0),(191.0, 135,215.0),(188.0, 135,255.0),
                     (250.0, 135,287.0),(264.0, 135,324.0),(350.0, 135,338.0),(21.0, 135,338.0),(27.0, 135,343.0),(17.0, 135,346.0),
                     (57.0, 135,22.0),(57.0, 135,24.0),(61.0, 135,25.0),(61.0, 135,37.0),(73.0, 135,34.0),(111.0, 135,69.0),
                     (131.0, 135,76.0),(138.0, 135,80.0),(157.0, 135,103.0),(194.0, 135,133.0),(197.0, 135,143.0),(211.0, 135,163.0),
                     (257.0, 135,157.0),(293.0, 135,176.0),(299.0, 135,191.0),(300.0, 135,198.0),(334.0, 135,196.0),(334.0, 135,209.0),
                     (336.0, 135,209.0),(342.0, 135,209.0),(344.0, 135,208.0),(342.0, 135,209.0),(351.0, 135,228.0),(0.0, 135,223.0),
                     (7.0, 135,224.0),(32.0, 135,235.0),(36.0, 135,235.0),(74.0, 135,236.0),(88.0, 135,245.0),(92.0, 135,261.0),
                     (115.0, 135,264.0),(128.0, 135,301.0),(155.0, 135,309.0),(164.0, 135,348.0),(170.0, 135,355.0),(204.0, 135,10.0),
                     (243.0, 135,24.0),(251.0, 135,49.0),(288.0, 135,55.0),(296.0, 135,81.0),(321.0, 135,88.0),(328.0, 135,103.0),
                     (333.0, 135,107.0),(333.0, 135,110.0),(330.0, 135,104.0),(329.0, 135,101.0),(339.0, 135,101.0),
                     (343.0, 135,101.0),(18.0, 135,132.0),(30.0, 135,161.0),(63.0, 135,163.0),(75.0, 135,169.0),(79.0, 135,188.0),
                     (89.0, 135,  215.0),(128.0, 135,235.0),(154.0, 135,244.0),(172.0, 135,251.0),(186.0, 135,252.0),(216.0, 135,275.0),
                      (248.0, 135,293.0),(276.0, 135,316.0),(284.0, 135,327.0),(289.0, 135,3.0),(300.0, 135,17.0),(326.0, 135,21.0),
                      (330.0, 135,21.0),(331.0, 135,39.0),(334.0, 135,39.0),(337.0, 135,39.0),(16.0, 135,60.0),(20.0, 135,69.0),
                      (38.0, 135,79.0),(56.0, 135,89.0),(90.0, 135,98.0),(122.0, 135,106.0),(147.0, 135,141.0),(175.0, 135, 168.0),
                      (192.0, 135,204.0),(193.0, 135,223.0),(207.0, 135,232.0),(245.0, 135,256.0),(279.0, 135,262.0),(302.0, 135,272.0),
                      (327.0, 135,306.0),(353.0, 135,318.0),(3.0, 135,354.0),(10.0, 135,26.0),(27.0, 135,30.0),(36.0, 135,69.0),
                          (73.0, 135,78.0),(91.0, 135,97.0),(127.0, 135,106.0),(153.0, 135,130.0),(156.0, 135,130.0),(181.0, 135,165.0),
                          (243.0, 135,168.0),(268.0, 135,206.0),(275.0, 135,223.0),(321.0, 135,237.0),(322.0, 135 ,240.0),(327.0, 135,267.0),
                          (330.0, 135,301.0),(6.0, 135,316.0),(11.0, 135,337.0),(19.0, 135,13.0),(28.0, 135,23.0),(37.0, 135,61.0),(38.0, 135,95.0),
                          (53.0, 135,134.0),(71.0, 135,168.0),(100.0, 135,202.0),(114.0, 135,213.0),(114.0, 135,228.0),(153.0, 135,238.0),
                          (158.0, 135,249.0),(161.0, 135,259.0),(191.0, 135,277.0),(197.0, 135,285.0),(238.0, 135,323.0),(249.0, 135,0.0),
                          (267.0, 135,15.0),(288.0, 135,34.0),(300.0, 135,58.0),(326.0, 135,75.0),(337.0, 135,76.0),(343.0, 135,76.0),( 17.0, 135,83.0),
                          (30.0, 135,109.0),(61.0, 135,146.0),(65.0, 135,166.0),(91.0, 135,187.0),(119.0, 135,201.0),(155.0, 135,226.0),
                          (155.0, 135,229.0),(170.0, 135,255.0),(187.0, 135,272.0),(235.0, 135,286.0),(218.0, 135, 320.0),(255.0, 135,357.0),
                          (262.0, 135,26.0),(277.0, 135,55.0),(300.0, 135,85.0),(330.0, 135,100.0),(358.0, 135,117.0),(0.0, 135,119.0),
                          (18.0, 135,132.0),(34.0, 135,134.0),(68.0, 135,144.0),(76.0, 135,182.0),(80.0, 135,210.0),(85.0, 135,212.0),
                          (118.0, 135,233.0),(144.0, 135,239.0),(157.0, 135,252.0),(180.0, 135,266.0),(182.0, 135,266.0),(187.0, 135, 280.0),
                          (190.0, 135,306.0),(219.0, 135,337.0),(252.0, 135,3.0),(290.0, 135,38.0),(325.0, 135,73.0),(331.0, 135,96.0),
                          (333.0, 135,101.0),(2.0, 135,140.0),(1.0, 135,151.0),(38.0, 135,185.0),(57.0, 135,190.0),(82.0, 135,208.0),
                          (95.0, 135,240.0),(126.0, 135,249.0),(139.0, 135,251.0),(157.0, 135,271.0),(184.0, 135,296.0),(194.0, 135,309.0),
                          (200.0, 135,324.0),(215.0, 135,337.0),(234.0, 135,1.0),(262.0, 135,32.0),(265.0, 135,52.0),(277.0, 135,77.0),(317.0, 135,78.0),(324.0, 135,116.0)]

        if self.model.experimentinfo.pointGroup == "-1":
            final_angle_list=[(0,135,0), (10, 135, 0),(69.0, 135,5.0),(95.0, 135,43.0),(97.0, 135,82.0),(129.0, 135,100.0),(136.0, 135,124.0),
                          (95.0, 135,240.0),(126.0, 135,249.0),(139.0, 135,251.0),(157.0, 135,271.0),(184.0, 135,296.0),(194.0, 135,309.0),
                          (200.0, 135,324.0),(215.0, 135,337.0),(234.0, 135,1.0),(262.0, 135,32.0),(265.0, 135,52.0),(277.0, 135,77.0),(317.0, 135,78.0),(324.0, 135,116.0)]

        if self.model.experimentinfo.pointGroup == "23":
            final_angle_list=[(0,135,0), (10, 135, 0)]

        #final_angle_list=[(0,135,0), (10, 135, 40)]
 

        print('update angle_list',)
        self.model.angleplan.angle_list=[]
        for i in range(len(final_angle_list)):
            r={
                "id": i + 1,
                "title":'pg:'+self.model.experimentinfo.pointGroup+'_'+str(i+1),
                "comment":"resetted",
                "phi":float(final_angle_list[i][0]),
                "chi":float(final_angle_list[i][1]),
                "omega":float(final_angle_list[i][2]),
                "wait_for": "PCharge",
                "value": 1,
            }
            self.model.angleplan.angle_list.append(r)
        
        print('vm optimize done for angle_list',self.model.angleplan.angle_list)





'''
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
        #goniometers = beamlines[instrument]['Goniometer']
        #print('goniometers ',goniometers )
        ##goniometers  {'BL12:Mot:goniokm:omega': [0, 1, 0, 1, 0, 360], 'BL12:Mot:goniokm:chi': [0, 0, 1, 1, 135, 135], 'BL12:Mot:goniokm:phi': [0, 1, 0, 1, 0, 360]}
        #omega0,omega1=goniometers['BL12:Mot:goniokm:omega'][4:6]
        #chi0,chi1    =goniometers['BL12:Mot:goniokm:chi'][4:6]
        #phi0,phi1    =goniometers['BL12:Mot:goniokm:phi'][4:6]

        #euler_angle_range=[[omega0,omega1,10],[chi0,chi1,0.5],[phi0,phi1,10]]
        #print('euler_angle_range ',euler_angle_range )
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
            det_ins_parameter.append({'pane_id':idx_pane,'pane_shape':'rectangle','pane_parameter':{'vertices':pane_vertices,'t_min':1000,'t_max':16000 }})
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


'''