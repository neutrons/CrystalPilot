"""Model for temporal analysis."""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional

# from mantid.simpleapi import *
import mantid.simpleapi as mtdapi
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pydantic import BaseModel, Field
from sklearn.linear_model import LinearRegression

# Live-monitoring UB save root: per-IPTS directory under TOPAZ shared.
_LIVE_UB_SUBDIR = "shared/CrystalPilot/live-data-monitoring"

# Verbose tracing for the live-data reduction path. Off by default — the live
# loop runs a Mantid pipeline every ~40s and used to emit ~50+ multi-line
# separator prints per cycle, which blocked the asyncio event loop on slow
# terminals. Flip this on (or set CRYSTALPILOT_DEBUG=1) when tracing issues.
_DEBUG_LIVE = bool(os.environ.get("CRYSTALPILOT_DEBUG"))


def _trace(*args: Any) -> None:
    if _DEBUG_LIVE:
        print(*args)

# Plotly layout shared by both temporal figures.
_TEMPORAL_FIG_MARGIN = {"l": 50, "r": 15, "t": 35, "b": 40}
_TEMPORAL_GRID_KWARGS = {
    "showgrid": True,
    "gridcolor": "rgba(120,120,120,0.35)",
    "gridwidth": 1,
    "griddash": "dot",
}

# import mantid algorithms, numpy and matplotlib
# matplotlib.use("Qt5Agg")
# sys.path.append('/SNS/TOPAZ/shared/PythonPrograms/Python3Library')
# from SCDTools import recenter_peaks_workspace


class MantidWorkflow:
    """Class for managing Mantid workflows."""

    def __init__(self) -> None:
        # def __init__(self,temporal_time_interval)->None:
        # def set_up_mantid_info(self)->None:
        print("initializing mtd workflow")
        self.ipts: int = 0  # placeholder; set by update_experiment_info() before use
        self.ub_failsafe: str = ""  # set by update_experiment_info()
        self.output_path: str = ""  # set by update_experiment_info()
        self.calib_fname: str = ""  # set by update_experiment_info()

        # Sample information
        self.min_d: float = 7  # shortest lattice parameter
        self.max_d: float = 40  # longest lattice parameter

        self.cell_type = "Monoclinic"
        self.centering = "P"

        self.tolerance = 0.12

        # Specify ellipse integration control parameters for satellite peaks
        self.satellite_peak_size = "0.07"
        self.satellite_background_inner_size = "0.09"
        self.satellite_background_outer_size = "0.12"
        self.satellite_region_radius = "0.13"

        #
        self.mod_vector1 = "0,0,0"
        self.mod_vector2 = "0,0,0"
        self.mod_vector3 = "0,0,0"
        #
        self.max_order = "1"
        self.cross_terms = False

        self.tolerance_satellite = 0.10
        #
        # User specified q-vector if save_mod_info is True
        self.save_mod_info = False
        #
        self.min_monitor_tof = 500
        self.max_monitor_tof = 13000
        self.use_monitor_counts = False

        # =================================================================================================
        #'''
        # def update_plot():
        #    """Update plot with current run data dynamically."""
        #    ax_intensity.clear()
        #    ax_rsig.clear()
        #    ax_intensity.plot(measure_times, intensity_ratios, '-o', label='Peak I/σ(I)')
        #    ax_rsig.plot(measure_times, rsigs, '-o', label='Rsig')
        #    ax_intensity.set_ylabel('Peak I/σ(I)')
        #    ax_rsig.set_ylabel('Rsig')
        #    ax_rsig.set_xlabel('Run time, seconds')
        #    ax_intensity.grid(True)
        #    ax_rsig.grid(True)
        #    plt.suptitle(f"Live Data Reduction - Run {current_run}")
        #    plt.draw()
        #    plt.pause(0.1)
        #'''

        #'''
        # def plot_data(x, y1, y2, xlabel, ylabel1, ylabel2):
        #    print('plot_data')
        #    plt.clf()  # Clear the figure to start a new plot
        #    plt.plot(x, y1, '-o', label=ylabel1)
        #    plt.plot(x, y2, '-o', label=ylabel2)
        #    plt.xlabel(xlabel)
        #    #plt.xlim(0,1000)
        #    plt.grid(True)
        #    plt.suptitle(f"Live Data Reduction - TOPAZ_{current_run}")
        #    plt.legend()
        #    #plt.draw()  # Use draw() instead of show() to update the plot
        #    plt.show()  # Use draw() instead of show() to update the plot
        #'''

        # def init_measurement_data():
        #    """Initialize the plot with empty data."""

        # Latest UB + lattice constants captured from the live workspace
        # (filled in once a UB has been refined).
        self.latest_ub: Optional[List[List[float]]] = None
        self.latest_lattice: Optional[Dict[str, float]] = None
        self.latest_ub_timestamp: str = ""
        self.latest_ub_saved_path: str = ""

        self.proton_charges: list[float] = []
        self.intensity_ratios: list[float] = []
        self.rsigs: list[float] = []
        self.measure_times: list[float] = []
        self.measure_times_sim: list[float] = []
        self.intensity_ratios_sim: list[float] = []
        self.rsigs_sim: list[float] = []
        self.sum = self.sig2 = self.sig3 = self.sig5 = self.sig10 = 0
        # Initialize as plain lists; convert to np.array at read time if needed
        self.sig2s: list = []
        self.sig3s: list = []
        self.sig5s: list = []
        self.sig10s: list = []
        self.missing_ub_number = 0

        self.current_run_end_time = 0
        self.measure_time = 0
        self.proton_charge = 0
        self.maxpeak_idx = -1
        self.timeseries: Any = np.array([])
        self.timeseries_data: List[np.ndarray] = []  # np.array([])
        # Check if live data is already running

        self.maxpeak_int_i = 0

        self.time_interval = 40
        # self.time_interval=temporal_time_interval
        self.total_time_of_run = 0
        self.total_numberof_time_intervals = 1
        self.time_of_poissonprocess = 0
        self.hkl: List[Any] = []
        self.timeseries_plt: Any = []
        self.timeseries_data_plt: Any = []
        self.temporal_poisson_intensity: Any = [0]
        self.temporal_poisson_uncertainty: Any = [0]
        # Run the SortHKL algorithm

    def stop(self) -> None:
        """Stop the Mantid MonitorLiveData thread."""
        try:
            from mantid.api import AlgorithmManager

            for alg in AlgorithmManager.runningInstancesOf("MonitorLiveData"):
                alg.cancel()
        except Exception as e:
            print(f"StopLiveData warning: {e}")

    def get_latest_ub(self, workspace_name: str = "live_predict_peaks_ws") -> Optional[List[List[float]]]:
        """Return the latest UB matrix from the named peaks workspace as a 3x3 list, or None."""
        try:
            ws = mtdapi.mtd[workspace_name]
            lattice = ws.sample().getOrientedLattice()
            ub = lattice.getUB()
            return [[float(ub[i][j]) for j in range(3)] for i in range(3)]
        except Exception as e:
            print(f"get_latest_ub: could not read UB from {workspace_name}: {e}")
            return None

    def get_latest_lattice(self, workspace_name: str = "live_predict_peaks_ws") -> Optional[Dict[str, float]]:
        """Return the latest lattice constants (a,b,c in Å, α,β,γ in deg, volume in Å³)."""
        try:
            ws = mtdapi.mtd[workspace_name]
            lat = ws.sample().getOrientedLattice()
            return {
                "a": float(lat.a()),
                "b": float(lat.b()),
                "c": float(lat.c()),
                "alpha": float(lat.alpha()),
                "beta": float(lat.beta()),
                "gamma": float(lat.gamma()),
                "volume": float(lat.volume()),
            }
        except Exception as e:
            print(f"get_latest_lattice: could not read lattice from {workspace_name}: {e}")
            return None

    def save_latest_ub(self, workspace_name: str = "live_predict_peaks_ws") -> Optional[str]:
        """Save the UB matrix to the per-IPTS live-monitoring directory with a timestamp.

        Uses Mantid's SaveIsawUB. Returns the path written, or None on failure.
        """
        try:
            ws = mtdapi.mtd[workspace_name]
            ws.sample().getOrientedLattice()
        except Exception as e:
            print(f"save_latest_ub: workspace '{workspace_name}' has no UB yet: {e}")
            return None

        save_dir = f"/SNS/TOPAZ/IPTS-{self.ipts}/{_LIVE_UB_SUBDIR}/"
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception as e:
            print(f"save_latest_ub: could not create {save_dir}: {e}")
            return None

        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"live_topaz-ipts-{self.ipts}_run-{getattr(self, 'current_run', 'na')}_{timestamp}.mat"
        path = os.path.join(save_dir, filename)
        try:
            mtdapi.SaveIsawUB(InputWorkspace=workspace_name, Filename=path)
            print(f"save_latest_ub: wrote {path}")
            return path
        except Exception as e:
            print(f"save_latest_ub: SaveIsawUB failed for {path}: {e}")
            return None

    def update_experiment_info(self, _models: Any) -> None:
        from .main_model import MainModel

        models: MainModel = _models

        self.ipts = int(models.experimentinfo.ipts_number)
        self.cell_type = models.experimentinfo.crystalsystem
        self.point_group = models.experimentinfo.point_group
        self.centering = models.experimentinfo.centering
        self.min_d = models.experimentinfo.min_dspacing
        self.max_d = models.experimentinfo.max_dspacing
        self.calib_fname = models.experimentinfo.cal_filename
        print("update experiment info")
        # print(self.ipts,self.cell_type,self.centering,self.min_d,self.max_d,self.calib_fname)
        if models.experimentinfo.UBFileName:
            self.ub_failsafe = models.experimentinfo.UBFileName
        self.output_path = "/SNS/TOPAZ/IPTS-{}/shared/autoreduce/live_data/".format(self.ipts)

        self.selection = models.temporalanalysis.data_selection

        # self.ub_failsafe="/SNS/TOPAZ/IPTS-{:d}/shared/CrystalPlan/SCO_295K_auto_Orthorhombic_P.mat".format(self.ipts)
        # self.output_path = '/SNS/TOPAZ/IPTS-{:d}/shared/autoreduce/live_data/'.format(self.ipts)
        # self.calib_fname = '/SNS/TOPAZ/IPTS-{:d}/shared/calibration/TOPAZ_2025A_AG_3-3BN.DetCal'.format(self.ipts)

    def update_peak_output_filenames(self) -> None:
        if self.cell_type is not None:
            self.live_peaks_fname = "live_topaz-ipts-%s_%s_%s_%s.integrate" % (
                str(self.ipts),
                str(self.current_run),
                self.cell_type,
                self.centering,
            )
            self.live_peaks_ub_fname = "live_topaz-ipts-%s_%s__%s_%s.mat" % (
                str(self.ipts),
                str(self.current_run),
                self.cell_type,
                self.centering,
            )
        else:
            self.live_peaks_fname = "live_topaz-ipts-%s_%s_Niggli.integrate" % (str(self.ipts), str(self.current_run))
            self.live_peaks_ub_fname = "live_topaz-ipts-%s_%s_Niggli.mat" % (str(self.ipts), str(self.current_run))

    def start_live_data_collection_instances(self) -> None:
        """Start live data instances: worksapce mtd['live_event_wc], self.currentrun,self.run."""
        try:
            mtdapi.StartLiveData(
                Instrument="TOPAZ",
                Listener="SNSLiveEventDataListener",
                # UpdateEvery=10,
                UpdateEvery=self.time_interval,
                AccumulationMethod="Add",
                PreserveEvents=True,
                OutputWorkspace="live_event_ws",
            )
            self.monitor_start_time = mtdapi.mtd["live_event_ws"].getRun().startTime().totalNanoseconds() * 1e-9
            time.sleep(1)
            # time.sleep(60)
        except RuntimeError as e:
            if "Another MonitorLiveData thread is running" in str(e):
                conflict_current_run = mtdapi.mtd["live_event_ws"].getRunNumber()
                msg = (
                    "Another MonitorLiveData thread is already running for TOPAZ run %s. "
                    "Stop the existing live-update session before starting a new one."
                ) % str(conflict_current_run)
                print("Warning:", msg)
                raise RuntimeError(msg) from e
            else:
                print(f"Unexpected error occurred: {str(e)}")
                raise
        # self.run_start_time = mtdapi.mtd['live_event_ws'].getRun().startTime().totalNanoseconds() * 1e-9

        # Proceed with data processing
        if not mtdapi.mtd.doesExist("live_event_ws"):
            raise RuntimeError("Live data workspace 'live_event_ws' does not exist after StartLiveData.")
        self.initial_run = mtdapi.mtd["live_event_ws"].getRunNumber()
        self.initial_run_start_time = mtdapi.mtd["live_event_ws"].getRun().startTime().totalNanoseconds() * 1e-9
        print(f"initial run: {self.initial_run}")

        # update the run number for live data reduction
        self.current_run = self.initial_run
        self.current_run_start_time = self.initial_run_start_time
        self.update_peak_output_filenames()

    # self.run = self.current_run

    ## Initialize the plot with two subplots
    #'''
    # def init_visualization():
    #    fig, (ax_intensity, ax_rsig) = plt.subplots(2, 1, sharex=True)
    #    ax_intensity.grid(True)
    #    ax_rsig.grid(True)
    #'''

    def live_data_reduction(self) -> None:
        # while True:
        def get_and_update_run_info_of_current_run() -> None:
            #############################################################################################################################################################
            # check if the run number has changed, if so, save the results and clear the existing data , and update the
            # run infos
            #############################################################################################################################################################
            current_run = mtdapi.mtd["live_event_ws"].getRunNumber()

            # Get the first event list
            _trace("=" * 60)
            _trace("Getting the first event list")
            # evList = mtdapi.mtd['live_event_ws'].getSpectrum(0)

            # Add an offset to the pulsetime (wall-clock time) of each event in the list.
            # print("First pulse time before addPulsetime: {}".format(evList.getPulseTimes()[0]))
            current_run_start_time = mtdapi.mtd["live_event_ws"].getRun().startTime().totalNanoseconds() * 1e-9

            if current_run != self.current_run:
                # Save the results
                results = np.column_stack((self.measure_times, self.proton_charges, self.intensity_ratios, self.rsigs))
                np.savetxt(
                    self.output_path + "live_data_%s_results.csv" % (str(self.current_run)),
                    results,
                    delimiter=",",
                    header="",
                    comments="",
                )
                # save results
                mtdapi.SaveIsawPeaks(
                    Inputworkspace="live_predict_peaks_ws", Filename=self.output_path + self.live_peaks_fname
                )
                mtdapi.SaveIsawUB(
                    Inputworkspace="live_predict_peaks_ws", Filename=self.output_path + self.live_peaks_fname
                )

                # Clear the existing data and plot if run changes
                self.current_run = current_run
                self.current_run_start_time = current_run_start_time
                self.proton_charges.clear()
                self.intensity_ratios.clear()
                self.rsigs.clear()
                self.measure_times.clear()
                self.timeseries_plt = []
                self.timeseries_data_plt = []
                time.sleep(1)
                # time.sleep(60)
                # plt.clf()  # Clear the plot

            self.update_peak_output_filenames()

        def load_config_of_current_run() -> None:
            #############################################################################################################################################################
            #''' Load the calibration file and monitor data, and integrate the peaks'''
            #############################################################################################################################################################
            # mtdapi.CloneWorkspace(InputWorkspace='live_event_ws', OutputWorkspace='live_event_ws')
            _trace("=" * 60)
            _trace("Loading the calibration file and monitor data, and integrating the peaks")
            _trace("first filterbytime")
            _trace("=" * 60)
            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            mtdapi.LoadIsawDetCal(InputWorkspace="live_event_ws", Filename=self.calib_fname)
            _trace("load isaw detcal", self.calib_fname)
            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("second filterbytime")
            _trace("=" * 60)
            monitor_ws = mtdapi.mtd["live_event_ws"].getMonitorWorkspace()
            _trace("monitorws")
            _trace("=" * 60)
            integrated_monitor_ws = mtdapi.Integration(
                InputWorkspace=monitor_ws,
                RangeLower=self.min_monitor_tof,
                RangeUpper=self.max_monitor_tof,
                StartWorkspaceIndex=0,
                EndWorkspaceIndex=0,
            )
            _trace("int filterbytime")
            _trace("=" * 60)
            monitor_count = integrated_monitor_ws.dataY(0)[0]
            print("\n", self.current_run, " has integrated monitor count", monitor_count, "\n")

            #
            mtdapi.SetGoniometer(Workspace="live_event_ws", Goniometers="Universal")
            _trace("getgonio filterbytime")
            _trace("=" * 60)
            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("3rd filterbytime")
            _trace("=" * 60)

        def refine_ub_of_current_run() -> None:
            #############################################################################################################################################################
            #''' Refine the UB matrix'''
            #############################################################################################################################################################
            # TODO: why convert to md
            mtdapi.CloneWorkspace(InputWorkspace="live_event_ws", OutputWorkspace="live_event_ws_peak")
            mtdapi.ConvertToMD(
                InputWorkspace="live_event_ws_peak",
                QDimensions="Q3D",
                dEAnalysisMode="Elastic",
                Q3DFrames="Q_sample",
                QConversionScales="Q in A^-1",
                LorentzCorrection="1",
                Uproj="1,0,0",
                Vproj="0,1,0",
                Wproj="0,0,1",
                OutputWorkspace="live_event_md_Qsample",
                MinValues="-12,-12,-12",
                MaxValues="12,12,12",
            )

            # mtdapi.ConvertToMD(InputWorkspace='live_event_ws',
            #    QDimensions="Q3D", dEAnalysisMode="Elastic",
            #    Q3DFrames='Q_sample',
            #    QConversionScales="Q in A^-1",
            #    LorentzCorrection='1',
            #    Uproj='1,0,0', Vproj='0,1,0', Wproj='0,0,1',
            #    OutputWorkspace='live_event_md_Qsample', MinValues='-12,-12,-12', MaxValues='12,12,12')
            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("4 filterbytime")
            _trace("=" * 60)

            mtdapi.FindPeaksMD(
                InputWorkspace="live_event_md_Qsample",
                PeakDistanceThreshold=0.6,
                MaxPeaks=1000,
                DensityThresholdFactor=100,
                OutputWorkspace="live_peaks_ws",
                EdgePixels=18,
            )
            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("5 filterbytime")
            _trace("=" * 60)

            try:
                mtdapi.FindUBUsingFFT(
                    PeaksWorkspace="live_peaks_ws", MinD=self.min_d, MaxD=self.max_d, Tolerance=0.12, Iterations=100
                )
            except ValueError as ub_error:
                print("Warning: FindUBUsingFFT error - Four or more indexed peaks needed to find UB")
                print("Error message: ", ub_error)
                # TODO: should use next two commands or not?
                # mtdapi.LoadIsawUB(InputWorkspace='live_peaks_ws',Filename='/SNS/TOPAZ/IPTS-33641/shared/S5-1_5K/S5-1_5K_Monoclinic_P.mat')#noqa
                # mtdapi.IndexPeaks(PeaksWorkspace='live_peaks_ws', Tolerance=0.12, ToleranceForSatellite=0.10000000000000001, RoundHKLs=False, CommonUBForAll=True)#noqa
                self.current_run_end_time = (
                    mtdapi.mtd["live_event_ws"].getRun().endTime().totalNanoseconds() * 1e-9
                )  # Convert nanoseconds to seconds

                self.measure_time = self.current_run_end_time - self.initial_run_start_time
                if self.measure_time > 100000:
                    print("Please check if neutron beam is on, or if the crystal is diffracting.")
            #        exit()
            # continue
            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("6 filterbytime")
            _trace("=" * 60)

        def integrate_peaks_of_current_run() -> None:
            #############################################################################################################################################################
            #''' Integrate the peaks and predict the peaks'''
            #############################################################################################################################################################
            mtdapi.CloneWorkspace(InputWorkspace="live_event_ws", OutputWorkspace="live_event_ws_peak")

            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            # _trace("7 filterbytime")
            # print("====================================================================================================")#noqa

            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("7.0 filterbytime")
            _trace("=" * 60)

            ## cause error in filter by time
            mtdapi.IndexPeaks(
                PeaksWorkspace="live_peaks_ws",
                Tolerance=0.12,
                ToleranceForSatellite=0.10000000000000001,
                RoundHKLs=False,
                CommonUBForAll=True,
            )

            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("7.1 filterbytime")
            _trace("=" * 60)

            mtdapi.IntegrateEllipsoids(
                InputWorkspace="live_event_ws_peak",
                PeaksWorkspace="live_peaks_ws",
                RegionRadius=0.18,
                SpecifySize=True,
                PeakSize=0.09,
                BackgroundInnerSize=0.11,
                BackgroundOuterSize=0.14,
                OutputWorkspace="live_peaks_ws",
                CutoffIsigI=5,
                AdaptiveQBackground=True,
                AdaptiveQMultiplier=0.001,
                UseOnePercentBackgroundCorrection=False,
            )
            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("7.2 filterbytime")
            _trace("=" * 60)

            mtdapi.PredictPeaks(
                InputWorkspace="live_peaks_ws",
                WavelengthMin=0.4,
                WavelengthMax=3.5,
                MinDSpacing=0.6,
                MaxDSpacing=11,
                OutputWorkspace="live_predict_peaks_ws",
                EdgePixels=18,
            )
            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("7 filterbytime")
            _trace("=" * 60)

            # TODO: local variables to be taken out
            peak_radius = 0.08
            search_radius = 0.8 * float(peak_radius)
            mtdapi.CentroidPeaksMD(
                InputWorkspace="live_event_md_Qsample",
                PeakRadius=search_radius,
                PeaksWorkspace="live_predict_peaks_ws",
                OutputWorkspace="live_predict_peaks_ws",
            )
            mtdapi.IndexPeaks(PeaksWorkspace="live_predict_peaks_ws", Tolerance=0.12, CommonUBForAll=True)
            mtdapi.FindUBUsingIndexedPeaks(PeaksWorkspace="live_predict_peaks_ws", Tolerance=0.12, CommonUBForAll=True)
            mtdapi.IndexPeaks(
                PeaksWorkspace="live_predict_peaks_ws", Tolerance=0.12, RoundHKLs=False, CommonUBForAll=True
            )

            # TODO: protoncharge not updated for live ws
            self.proton_charge = mtdapi.mtd["live_event_ws"].getRun().getProtonCharge() * 0.0036
            print("\n", self.current_run, " has integrated proton charge x 0.0036 of", self.proton_charge, "C \n")

            self.current_run_end_time = (
                mtdapi.mtd["live_event_ws"].getRun().endTime().totalNanoseconds() * 1e-9
            )  # Convert nanoseconds to seconds

            self.measure_time = self.current_run_end_time - self.current_run_start_time
            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("8 filterbytime")
            _trace("=" * 60)

            mtdapi.IntegrateEllipsoids(
                InputWorkspace="live_event_ws_peak",
                PeaksWorkspace="live_predict_peaks_ws",
                RegionRadius=0.2,
                SpecifySize=True,
                PeakSize=0.09,
                BackgroundInnerSize=0.11,
                BackgroundOuterSize=0.14,
                OutputWorkspace="live_predict_peaks_ws",
                CutoffIsigI=5,
                AdaptiveQBackground=True,
                AdaptiveQMultiplier=0.001,
                UseOnePercentBackgroundCorrection=False,
            )

            if self.cell_type is not None:
                mtdapi.SelectCellOfType(
                    PeaksWorkspace="live_predict_peaks_ws",
                    CellType=self.cell_type,
                    Centering=self.centering,
                    Tolerance=self.tolerance,
                    Apply=True,
                )
                mtdapi.IndexPeaks(
                    PeaksWorkspace="live_predict_peaks_ws",
                    Tolerance=self.tolerance,
                    ToleranceForSatellite=self.tolerance_satellite,
                    RoundHKLs=False,
                    CommonUBForAll=True,
                )

            # mtdapi.FilterByTime(InputWorkspace='live_event_ws', OutputWorkspace='timestep_event_ws',
            #                    StartTime=0, StopTime=1)
            _trace("9 filterbytime")
            _trace("=" * 60)

        def check_peaks_of_current_run() -> None:
            live_predict_peaks_ws = mtdapi.mtd["live_predict_peaks_ws"]

            # peaks_fname = 'live_%s_Niggli.integrate'%(str(current_run))
            # peaks_ub_fname = 'live_%s_Niggli.mat'%(str(current_run))

            # Set the monitor counts for all the peaks that will be integrated

            num_peaks = live_predict_peaks_ws.getNumberPeaks()
            int_ilist = np.zeros(num_peaks)
            sig_ilist = np.zeros(num_peaks)
            # TODO: check getErrorSquaredArray  method
            for i in range(num_peaks):
                peak = live_predict_peaks_ws.getPeak(i)
                int_i = peak.getIntensity()
                int_ilist[i] = int_i
                sig_i = peak.getSigmaIntensity()
                sig_ilist[i] = sig_i
                self.sum = self.sum + 1
                if int_i > (2.0 * sig_i):
                    self.sig2 = self.sig2 + 1
                if int_i > (3.0 * sig_i):
                    self.sig3 = self.sig3 + 1
                if int_i > (5.0 * sig_i):
                    self.sig5 = self.sig5 + 1
                if int_i > (10.0 * sig_i):
                    self.sig10 = self.sig10 + 1
            # TODO peaks update
            if self.maxpeak_idx > -1 and self.maxpeak_idx != np.argmax(int_ilist):
                print("Warning: Max peak index has changed from ", self.maxpeak_idx, " to ", np.argmax(int_ilist))
                self.maxpeak_idx = int(np.argmax(int_ilist))

            if self.maxpeak_idx == -1:
                self.maxpeak_idx = int(np.argmax(int_ilist))

            # self.maxpeak_idx=np.argmax(int_ilist)

            self.maxpeak_int_i = int_ilist[self.maxpeak_idx]

            peak = live_predict_peaks_ws.getPeak(int(self.maxpeak_idx))

            # peak = live_predict_peaks_ws.getPeak(int(0))
            self.hkl = peak.getHKL()

            # Run the SortHKL algorithm

            sorted, statistics_table, equiv_i = mtdapi.StatisticsOfPeaksWorkspace(
                InputWorkspace="live_predict_peaks_ws",
                PointGroup=self.point_group,
                LatticeCentering=self.centering,
                SortBy="Overall",
                WeightedZScore=True,
            )

            statistics = statistics_table.row(0)

            peak = sorted.getPeak(0)
            print("HKL of first peak in table {} {} {}".format(peak.getH(), peak.getK(), peak.getL()))
            print("Multiplicity = %.2f" % statistics["Multiplicity"])
            print("Resolution Min = %.2f" % statistics["Resolution Min"])
            print("Resolution Max = %.2f" % statistics["Resolution Max"])
            print("No. of Unique Reflections = %i" % statistics["No. of Unique Reflections"])
            print("Mean ((I)/sd(I)) = %.2f" % statistics["Mean ((I)/sd(I))"])
            print("Rmerge = %.2f" % statistics["Rmerge"])
            print("Rpim = %.2f" % statistics["Rpim"])

            mtdapi.SaveIsawPeaks(
                Inputworkspace="live_predict_peaks_ws", Filename=self.output_path + self.live_peaks_fname
            )
            mtdapi.SaveIsawUB(
                Inputworkspace="live_predict_peaks_ws", Filename=self.output_path + self.live_peaks_ub_fname
            )

            # Capture and persist the latest UB + lattice for the live-monitoring view/table.
            self.latest_ub = self.get_latest_ub("live_predict_peaks_ws")
            self.latest_lattice = self.get_latest_lattice("live_predict_peaks_ws")
            self.latest_ub_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            self.latest_ub_saved_path = self.save_latest_ub("live_predict_peaks_ws") or ""

            # Check the overall peak intensity in live_peaks_ws
            # data_selection_options: List[str] = ["All Peaks", "Bragg Peaks","Max Peak","Satellite Peaks","Diffuse scattering"]#noqa

            # default
            if self.selection == "All Peaks":
                self.intensity_ratio = statistics["Mean ((I)/sd(I))"]
            # TODO: intensity ratio selection
            if self.selection == "Max Peak":
                idx = self.maxpeak_idx
                self.intensity_ratio = int_ilist[idx] / sig_ilist[idx]

            elif self.selection == "Total Peaks":
                self.intensity_ratio = np.sum(int_ilist) / np.sqrt(np.sum(sig_ilist**2))
                self.intensity_ratio = np.mean(int_ilist / sig_ilist)
            #
            self.Rsig = 100.0 / self.intensity_ratio
            print("Rsig = %.2f" % self.Rsig)
            if self.intensity_ratio is not None and self.Rsig is not None and self.proton_charge is not None:
                self.proton_charges.append(self.proton_charge)
                self.intensity_ratios.append(self.intensity_ratio)
                self.rsigs.append(self.Rsig)
                self.measure_times.append(self.measure_time)  # Only append if all other values exist
            else:
                print("Skipping entry due to missing data.")
            self.sig2s.append(self.sig2)
            self.sig3s.append(self.sig3)
            self.sig5s.append(self.sig5)
            self.sig10s.append(self.sig10)
            # Save the plot data
            print("measure_times, proton_charges, intensity_ratios, rsigs")
            print(self.measure_times, self.proton_charges, self.intensity_ratios, self.rsigs)
            results = np.column_stack((self.measure_times, self.proton_charges, self.intensity_ratios, self.rsigs))
            np.savetxt(
                self.output_path + "live_data_%s_results.csv" % (str(self.current_run)),
                results,
                delimiter=",",
                header="",
                comments="",
            )

        print("============================================================================================")
        _trace("live data reduction started")
        print("============================================================================================")
        get_and_update_run_info_of_current_run()
        load_config_of_current_run()
        refine_ub_of_current_run()
        integrate_peaks_of_current_run()
        check_peaks_of_current_run()


# class TemporalData(BaseModel):
#    time: float
#    intensity: float
#    variance: float
#    uncertainty: float
#
# import math
"""
class PoissonModelAnalysis(BaseModel):

    # Load the monitor data and get the counting time in seconds
    event_ws = mtdapi.LoadNexusMonitors( Filename=data_filename  )
    total_time = event_ws.run()['duration'].value
    print('data collection time {:0.0f} seconds'.format(total_time))
    MultiplierBase=1.0
    time_interval=1
    if total_time >=time_interval:
        if MultiplierBase<=1:
            number_of_steps = ( total_time - time_interval ) /time_interval
        else:
            number_of_steps = ( math.log(total_time) - math.log(time_interval) ) / math.log(MultiplierBase)
        number_of_steps = int(number_of_steps) + 1
        print('\nnumber_of_steps = ', number_of_steps)
        print('')
    else:
        print('\\data collection time is less than the time interval of {:0f} seconds'.format(time_interval))

    peaks_ws=mtdapi.LoadIsawPeaks(Filename=peaks_filename)
    mtdapi.LoadIsawUB(InputWorkspace='peaks_ws', Filename=UB_filename)
    mtdapi.IndexPeaks(PeaksWorkspace='peaks_ws', Tolerance=tolerance, ToleranceForSatellite=tolerance_satellite,
            RoundHKLs=False, CommonUBForAll=True)

    # Begin loop to integrate peaks and analyze statistics
    #

    print(f'Total time: {total_time}')

    n_step = 1
    while True:
        #time_stop = time_interval * MultiplierBase**n_step
        time_stop = time_interval * MultiplierBase * n_step
        print('--- time_stop: {}, time_interval: {}, MultiplierBase: {}, n_step: {}, total_time: {}'
            .format(time_stop, time_interval, MultiplierBase, n_step, total_time))
        if time_stop <= total_time:
            event_ws = mtdapi.Load( Filename=data_filename,
                               FilterByTofMin=min_tof, FilterByTofMax=max_tof,
                               FilterByTimeStop = time_stop
                            )
            event_ws = mtdapi.FilterBadPulses(InputWorkspace=event_ws, LowerCutoff = 85)
            proton_charge = event_ws.getRun().getProtonCharge() * 1000.0  # proton charge scaled up to match detector counts
            mtdapi.LoadIsawDetCal(event_ws, Filename=calibration_file)
            mtdapi.LoadIsawUB(InputWorkspace=event_ws, Filename=UB_filename)

            #MDEW=ConvertToMD(InputWorkspace=event_ws, QDimensions='Q3D',
            #    dEAnalysisMode='Elastic', Q3DFrames='Q_sample', LorentzCorrection=True,
            #    MinValues=minQ, MaxValues=max_q, SplitInto='2',
            #    SplitThreshold=60, MaxRecursionDepth=13, MinRecursionDepth=7)

            #peaks_ws=LoadIsawPeaks(Filename=peaks_filename)
            #LoadIsawUB(InputWorkspace='peaks_ws', Filename=UB_filename)
            #IndexPeaks(PeaksWorkspace='peaks_ws', Tolerance=tolerance, ToleranceForSatellite=tolerance_satellite, RoundHKLs=False, CommonUBForAll=True)

            #FindUBUsingIndexedPeaks(PeaksWorkspace=peaks_ws,
            #                Tolerance=tolerance,
            #                ToleranceForSatellite=tolerance_satellite, CommonUBForAll=True)
            #SelectCellOfType(PeaksWorkspace=peaks_ws, CellType='Hexagonal', Apply=True, AllowPermutations=True)
            #IndexPeaks(PeaksWorkspace=peaks_ws, Tolerance=tolerance, ToleranceForSatellite=tolerance_satellite,
            #    RoundHKLs=False,
            #    ModVector1='0,0,0.5',
            #    MaxOrder=1,
            #    CrossTerms=False,
            #    SaveModulationInfo=True,
            #    CommonUBForAll=True)
            #peaks_ws=FilterPeaks(InputWorkspace=peaks_ws, FilterVariable='h^2+k^2+l^2', FilterValue=0, Operator='>')
            #FindUBUsingIndexedPeaks(PeaksWorkspace=peaks_ws,
            #                Tolerance=tolerance,
            #                ToleranceForSatellite=tolerance_satellite,CommonUBForAll=True)
            #IndexPeaks(PeaksWorkspace=peaks_ws, Tolerance=tolerance, ToleranceForSatellite=tolerance_satellite, RoundHKLs=False, CommonUBForAll=True)
            #OptimizeLatticeForCellType(PeaksWorkspace=peaks_ws, CellType='Hexagonal', Apply=True, Tolerance=0.06, EdgePixels=19, OutputDirectory='/SNS/TOPAZ/shared/test/Integrate_satellite_peaks')
            #IndexPeaks(PeaksWorkspace=peaks_ws, Tolerance=tolerance, ToleranceForSatellite=tolerance_satellite, RoundHKLs=False, CommonUBForAll=True)

            mtdapi.CopySample(InputWorkspace=peaks_ws,
                    OutputWorkspace='event_ws', CopyName=False, CopyMaterial=False, CopyEnvironment=False, CopyShape=False)
            if q_frame == ('lab' or 'sample'):
                Q_box = 'Q_' + q_frame
                MDEW = mtdapi.ConvertToMD(InputWorkspace=event_ws, QDimensions='Q3D',
                        dEAnalysisMode='Elastic', Q3DFrames=Q_box,
                        LorentzCorrection=False,
                        MinValues=minQ, MaxValues=max_q)

            elif q_frame==('HKL' or 'hkl'):
                Q_box='HKL'
            if peaks_ws.sample().hasOrientedLattice():
                # get hkl limits
                cell = peaks_ws.mutableSample().getOrientedLattice()
                max_h = math.ceil(cell.a()*(float(Qmax)/2.0/math.pi))
                max_k = math.ceil(cell.b()*(float(Qmax)/2.0/math.pi))
                max_l = math.ceil(cell.c()*(float(Qmax)/2.0/math.pi))
                max_HKL ='%s,%s,%s'%(max_h,max_k,max_l)
                min_HKL ='-%s,-%s,-%s'%(max_h,max_k,max_l)
            else:
                print('Error: No UB matrix')
                #break
            print('\nReducing data in HKL space ...')
            MDEW=mtdapi.ConvertToMD(InputWorkspace='event_ws',
                            QDimensions='Q3D', dEAnalysisMode='Elastic',
                            Q3DFrames=Q_box, QConversionScales='HKL',
                            Uproj='1,0,0', Vproj='0,1,0', Wproj='0,0,1',
                            MinValues=min_HKL, MaxValues=max_HKL)

            # if not os.path.exists(plot_folder):
            #     os.makedirs(plot_folder)

            UB = peaks_ws.sample().getOrientedLattice().getUB()
            banks = mtd['peaks_ws'].column(13)

            peak_numbers = [167,168,169,170,171,172,173,174,175,176]
            print(len(peak_numbers))

            for i in peak_numbers:
            #for i in range(peaks_ws.getNumberPeaks()):
                signal_array = []
                H_array = []
                K_array = []
                L_array = []

                peak =peaks_ws.getPeak(i)
                peak_index=peak.getPeakNumber()
                h,k,l=peak.getHKL()
                col=peak.getCol()
                row=peak.getRow()
                dn = int(banks[i].strip('bank'))

                # l_min = l-fracHKL[2]
                # l_max = l+fracHKL[2]

                # l_step = (l_max-l_min)/(l_bins-1)

                # BinMD(InputWorkspace='MDEW', AlignedDim0='[H,0,0],{},{},{}'.format(h-0.5,h+0.5,h_bin_num),
                #                              AlignedDim1='[0,K,0],{},{},{}'.format(k-0.5,k+0.5,k_bin_num),
                #                              AlignedDim2='[0,0,L],{},{},1'.format(l-l_step,l+l_step),
                #                              OutputWorkspace='HKL=({:.2f},{:.2f},{:.2f})_binslice'.format(h,k,l))

                BinMD(InputWorkspace='MDEW', AlignedDim0='[H,0,0],{},{},{}'.format(h-0.5,h+0.5,h_bin_num),
                                             AlignedDim1='[0,K,0],{},{},{}'.format(k-0.5,k+0.5,k_bin_num),
                                             AlignedDim2='[0,0,L],{},{},{}'.format(l-0.5,l+0.5,l_bin_num),
                                             OutputWorkspace='HKL=({:.2f},{:.2f},{:.2f})_binslice'.format(h,k,l))

                data = mtd['HKL=({:.2f},{:.2f},{:.2f})_binslice'.format(h,k,l)]

                signal_array = data.getSignalArray().copy()
                # H, K, L = np.meshgrid(*[np.linspace(data.getDimension(i).getMinimum(),data.getDimension(i).getMaximum(),data.getDimension(i).getNBins()) for i in range(data.getNumDims())])


                #####  save 3D slices (md nexus files)
                # print('--- Saving SaveMD for .nxs for step: {}.....'.format(time_stop))
                # SaveMD(data, output_directory + '/' + 'TOPAZ_{0:d}_peak_{1:d}_step_{2:d}_ORIGINAL.nxs'.format(run, i, n_step))


                peakdir=output_directory+'npy/peak_{0:d}_res_{1:d}/'.format(i, bin_size[0])
                peakfilename='run_{0:d}_peak_number_{1:d}_time_step_{2:d}_data.npy'.format( run,i,n_step)
                if not os.path.exists(peakdir): os.makedirs(peakdir)
                np.save(peakdir+peakfilename, signal_array)
                # np.save(output_directory+'/npy/peak_{0:d}/run_{1:d}_peak_number_{2:d}_time_step_{3:d}_grid_H.npy'.format(i, run,i,n_step), H_array)
                # np.save(output_directory+'/npy/peak_{0:d}/run_{1:d}_peak_number_{2:d}_time_step_{3:d}_grid_K.npy'.format(i, run,i,n_step), K_array)
                # np.save(output_directory+'/npy/peak_{0:d}/run_{1:d}_peak_number_{2:d}_time_step_{3:d}_grid_L.npy'.format(i, run,i,n_step), L_array)

                ####### tmp commented ##############
        if time_stop >= total_time: break
        print(time_stop)
        print(total_time)
        n_step = n_step + 1

        #plt.close('all')
"""  # noqa


class TemporalAnalysisModel(BaseModel):
    """Pydantic class for holding temporal analysis information."""

    table_test: List[Dict] = Field(default=[{"title": "1", "header": "h"}])
    prediction_model_type: str = Field(default="Poisson Model", title="Prediction Model")
    prediction_model_type_options: List[str] = ["Poisson Model", "Bayesian Model", "Linear Interpolation"]
    # prediction_model_type_options: List[str] = ["Poisson Model", "Linear Interpolation"]
    data_selection: str = Field(default="All Peaks", title="Peak Selection")
    data_selection_options: List[str] = [
        "All Peaks",
        "Bragg Peaks",
        "Max Peak",
        "Satellite Peaks",
        "Diffuse scattering",
    ]
    # data_selection_options: List[str] = ["All Peaks", "Strongest Peak Center", "Strongest Peak Edge","Smart Selection"]#noqa
    time_steps: List[float] = Field(default=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], title="Time Steps")
    intensity_data: List[float] = Field(
        default=[0.0, 1.0, 4.0, 9.0, 16.0, 25.0, 36.0, 49.0, 64.0, 81.0], title="Intensity Data"
    )
    variance_data: List[float] = Field(
        default=[0.0, 0.1, 0.4, 0.9, 1.6, 2.5, 3.6, 4.9, 6.4, 8.1], title="Variance Data"
    )
    uncertainty_data: List[float] = Field(
        default=[0.0, 0.2, 0.6, 1.2, 2.0, 3.0, 4.2, 5.6, 7.2, 9.0], title="Uncertainty Data"
    )
    # prediction_figure: go.Figure = Field(default_factory=go.Figure, title="Prediction Figure")
    timestamp: float = Field(default=0.0, title="timestamp")
    all_time: List[float] = Field(default=[0.0, 10000], title="All Time")
    # mtd_workflow: MantidWorkflow = Field(default=MantidWorkflow(), title="Mantid Workflow")
    time_interval: float = Field(default=40, title="Time Interval")
    # Latest UB matrix inferred from live data, plus bookkeeping for the side table.
    latest_ub: List[List[float]] = Field(
        default_factory=lambda: [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        title="Latest UB",
        description="Most recent UB matrix inferred from live data (rows are UB rows).",
    )
    latest_ub_timestamp: str = Field(default="", title="Latest UB timestamp")
    latest_ub_saved_path: str = Field(default="", title="Latest UB saved path")
    latest_lattice: Dict[str, float] = Field(
        default_factory=lambda: {
            "a": 0.0, "b": 0.0, "c": 0.0,
            "alpha": 0.0, "beta": 0.0, "gamma": 0.0, "volume": 0.0,
        },
        title="Latest lattice constants (Å / deg / Å³)",
    )
    latest_lattice_summary: str = Field(
        default="",
        title="Latest lattice summary",
        description="Pretty one-line a,b,c,α,β,γ,V derived from latest_lattice.",
    )
    latest_ub_rows: List[Dict[str, Any]] = Field(
        default_factory=lambda: [
            {"row": "row 1", "c1": 0.0, "c2": 0.0, "c3": 0.0},
            {"row": "row 2", "c1": 0.0, "c2": 0.0, "c3": 0.0},
            {"row": "row 3", "c1": 0.0, "c2": 0.0, "c3": 0.0},
        ],
        title="Latest UB (table rows)",
    )
    latest_ub_headers: List[Dict[str, Any]] = Field(
        default_factory=lambda: [
            {"title": "", "value": "row", "sortable": False, "align": "center"},
            {"title": "col 1", "value": "c1", "sortable": False, "align": "center"},
            {"title": "col 2", "value": "c2", "sortable": False, "align": "center"},
            {"title": "col 3", "value": "c3", "sortable": False, "align": "center"},
        ],
    )
    # Lazy instance; created in start_reading_live_mtd_data() once Mantid is ready.
    _mtd_workflow: Optional[MantidWorkflow] = None
    # Optional back-reference to MainModel. Set by MainViewModel when wiring.
    _parent: Any = None
    # Memoization for the two figure builders. Both are called once per
    # update_temporalanalysis_figure() (1Hz min interval) and used to refit
    # LinearRegression from scratch on the full series each time. Cache by
    # (model_type, series length) so unchanged series skip the rebuild + fit.
    _intensity_fig_cache: Optional[tuple[Any, go.Figure]] = None
    _uncertainty_fig_cache: Optional[tuple[Any, go.Figure]] = None

    @property
    def mtd_workflow(self) -> Optional[MantidWorkflow]:
        """Return the MantidWorkflow instance, or None if not yet initialized."""
        return self._mtd_workflow

    def set_parent(self, parent: Any) -> None:
        """Set a back-reference to the owning MainModel.

        Use this to access sibling models (for example, experimentinfo) without
        importing MainModel at runtime (TYPE_CHECKING prevents circular imports).
        """
        from .main_model import MainModel

        self._parent: MainModel = parent

    def get_models(self) -> Any:
        """Return the ExperimentInfoModel instance from the parent MainModel, or None.

        Use this helper to access up-to-date experiment info without importing
        ExperimentInfoModel here (avoids circular imports). Callers should
        defensively check for None.
        """
        try:
            print("try get models from parent")
            if getattr(self, "_parent", None) is not None:
                print("get models from parent")
                if self._parent:
                    print(self._parent.experimentinfo)
                return self._parent
        except Exception:
            return None
        return None

    def sync_latest_ub_from_workflow(self) -> None:
        """Copy latest_ub / timestamp / saved-path from MantidWorkflow into pydantic fields.

        The workflow holds Python attributes; the table needs Pydantic fields the binding
        can serialize. Called after each live-data reduction iteration.
        """
        if self._mtd_workflow is None:
            return
        ub = getattr(self._mtd_workflow, "latest_ub", None)
        if ub is None:
            return
        try:
            self.latest_ub = [[float(v) for v in row] for row in ub]
            self.latest_ub_timestamp = getattr(self._mtd_workflow, "latest_ub_timestamp", "") or ""
            self.latest_ub_saved_path = getattr(self._mtd_workflow, "latest_ub_saved_path", "") or ""
            self.latest_ub_rows = [
                {
                    "row": f"row {i + 1}",
                    "c1": round(self.latest_ub[i][0], 6),
                    "c2": round(self.latest_ub[i][1], 6),
                    "c3": round(self.latest_ub[i][2], 6),
                }
                for i in range(3)
            ]
            lat = getattr(self._mtd_workflow, "latest_lattice", None)
            if lat:
                self.latest_lattice = {k: float(v) for k, v in lat.items()}
                self.latest_lattice_summary = (
                    f"a = {lat['a']:.4f} Å    b = {lat['b']:.4f} Å    c = {lat['c']:.4f} Å    "
                    f"α = {lat['alpha']:.3f}°    β = {lat['beta']:.3f}°    γ = {lat['gamma']:.3f}°    "
                    f"V = {lat['volume']:.2f} Å³"
                )
        except Exception as e:
            print(f"sync_latest_ub_from_workflow: {e}")

    def _intensity_cache_key(self) -> Any:
        if self._mtd_workflow is None:
            return ("none",)
        wf = self._mtd_workflow
        if self.prediction_model_type == "Poisson Model":
            ts, ints = wf.measure_times, wf.intensity_ratios
        else:
            ts, ints = wf.timeseries_plt, wf.timeseries_data_plt
        n = len(ts)
        return (
            self.prediction_model_type,
            n,
            ts[-1] if n else None,
            ints[-1] if n and len(ints) else None,
        )

    def get_figure_intensity(self) -> go.Figure:
        cache_key = self._intensity_cache_key()
        cached = self._intensity_fig_cache
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        fig = self._build_figure_intensity()
        self._intensity_fig_cache = (cache_key, fig)
        return fig

    def _build_figure_intensity(self) -> go.Figure:
        # self.timestamp = time.time()
        fig = go.Figure()
        if self._mtd_workflow is None:
            return fig
        # self.time_steps=self.mtd_workflow.measure_times
        # if self.prediction_model_type=='Linear Interpolation':

        if self.prediction_model_type == "Poisson Model":
            time_steps = self.mtd_workflow.measure_times
            intensity_data: Any = self.mtd_workflow.intensity_ratios
            ## Example of reading up-to-date experiment info from parent if available
            ## (e.g., to change behavior based on point group or other settings).
            # try:
            #    if getattr(self, "_parent", None) is not None:
            #        pg = self._parent.experimentinfo.point_group
            #        # Use point_group for conditional behavior or logging
            #        # e.g., change figure title suffix
            #        intensity_figure_title_suffix = f" (PG={pg})"
            #    else:
            #        intensity_figure_title_suffix = ""
            # except Exception:
            #    intensity_figure_title_suffix = ""
            # intensity_figure_title='Prediction of Signal Noise Ratio' + intensity_figure_title_suffix
            intensity_figure_title = "Prediction of Signal Noise Ratio"
            intensity_figure_yaxis = "Signal Noise Ratio"
        if self.prediction_model_type == "Linear Interpolation":
            # if self.prediction_model_type=='Poisson Model':
            time_steps = self.mtd_workflow.timeseries_plt
            # intensity_data=np.array(self.mtd_workflow.temporal_poisson_intensity)*0.03*(-1)**int(np.array(time_steps)/40)+27#noqa
            # intensity_data=np.array(self.mtd_workflow.temporal_poisson_intensity)
            intensity_data = np.array(self.mtd_workflow.timeseries_data_plt)
            intensity_figure_title = "Prediction of Intensity"
            intensity_figure_yaxis = "Intensity"

        # if False:
        if len(time_steps) > 0:
            print("============================================================================================")
            _trace("time_steps = self.mtd_workflow.measure_times")
            _trace(time_steps, self.mtd_workflow.measure_times)
            _trace("intensity_data = self.mtd_workflow.intensity_ratios")
            _trace(intensity_data, self.mtd_workflow.intensity_ratios)
            print("============================================================================================")
            # self.intensity_data = self.mtd_workflow.intensity_ratios
            # Reshape the data for sklearn
            x = np.array(time_steps).reshape(-1, 1)
            x = x**0.5
            y = np.array(intensity_data)

            # Create and fit the model
            model = LinearRegression()
            model.fit(x, y)

            # Get the slope (coefficient) and intercept
            slope = model.coef_[0]
            intercept = model.intercept_

            _trace(f"Slope: {slope}, Intercept: {intercept}")

            #    ax_intensity.plot(measure_times, intensity_ratios, '-o', label='Peak I/σ(I)')
            #    ax_rsig.plot(measure_times, rsigs, '-o', label='Rsig')
            #    ax_intensity.set_ylabel('Peak I/σ(I)')
            #    ax_rsig.set_ylabel('Rsig')
            #    ax_rsig.set_xlabel('Run time, seconds')
            #    ax_intensity.grid(True)
            # Add a dashed line with the slope and intercept
            # if self.prediction_model_type=='Linear Interpolation':
            if self.prediction_model_type == "Poisson Model":
                x_range = np.linspace(max(time_steps), max(time_steps) + 2000, 100)
                y_range = slope * x_range**0.5 + intercept
            if self.prediction_model_type == "Linear Interpolation":
                # if self.prediction_model_type=='Poisson Model':
                x_range = np.linspace(max(time_steps), max(time_steps) + 2000, 100)
                y_range = np.zeros_like(x_range) + intensity_data[-1]
            fig.add_trace(go.Scatter(x=x_range, y=y_range, mode="lines", name="Prediction Line", line={"dash": "dash"}))
            fig.add_trace(go.Scatter(x=time_steps, y=intensity_data, mode="lines+markers", name="History Data"))
            # fig.add_trace(go.Scatter(x=self.time_steps, y=intensity_data, mode='lines+markers', name='History Data'))
            # fig.add_trace(go.Scatter(x=self.time_steps, y=self.intensity_data, mode='lines+markers', name='Intensity Data'))#noqa
            # fig.update_layout(title='Prediction of Intensity with '+self.prediction_model_type, xaxis_title='Time Steps (s)', yaxis_title='Intensity')#noqa
            fig.update_layout(
                title={"text": intensity_figure_title, "x": 0.5, "xanchor": "center"},
                xaxis_title="Time Steps (s)",
                yaxis_title=intensity_figure_yaxis,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                margin=_TEMPORAL_FIG_MARGIN,
            )
            fig.update_xaxes(
                showline=True, linewidth=2, linecolor="black", mirror=True, **_TEMPORAL_GRID_KWARGS
            )
            fig.update_yaxes(
                showline=True, linewidth=2, linecolor="black", mirror=True, **_TEMPORAL_GRID_KWARGS
            )
            # fig.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=True, gridcolor='black', gridwidth=1, griddash='dash')#noqa
            # fig.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=True, gridcolor='black', gridwidth=1, griddash='dash')#noqa
            # time.sleep(7)
        else:
            fig.update_layout(
                title={"text": intensity_figure_title, "x": 0.5, "xanchor": "center"},
                xaxis_title="Time Steps (s)",
                yaxis_title=intensity_figure_yaxis,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                margin=_TEMPORAL_FIG_MARGIN,
            )
            fig.update_xaxes(
                showline=True, linewidth=2, linecolor="black", mirror=True, **_TEMPORAL_GRID_KWARGS
            )
            fig.update_yaxes(
                showline=True, linewidth=2, linecolor="black", mirror=True, **_TEMPORAL_GRID_KWARGS
            )

            fig.add_annotation(
                text="Waiting for data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 20, "color": "red"},
            )
        return fig

    def _uncertainty_cache_key(self) -> Any:
        if self._mtd_workflow is None:
            return ("none",)
        wf = self._mtd_workflow
        if self.prediction_model_type == "Poisson Model":
            ts, vals = wf.measure_times, wf.rsigs
        else:
            ts, vals = wf.timeseries_plt, wf.temporal_poisson_uncertainty
        n = len(ts)
        return (
            self.prediction_model_type,
            n,
            ts[-1] if n else None,
            vals[-1] if n and len(vals) else None,
        )

    def get_figure_uncertainty(self) -> go.Figure:
        cache_key = self._uncertainty_cache_key()
        cached = self._uncertainty_fig_cache
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        fig = self._build_figure_uncertainty()
        self._uncertainty_fig_cache = (cache_key, fig)
        return fig

    def _build_figure_uncertainty(self) -> go.Figure:
        # self.timestamp = time.time()
        fig = go.Figure()
        if self._mtd_workflow is None:
            return fig

        if self.prediction_model_type == "Poisson Model":
            # if self.prediction_model_type=='Linear Interpolation':
            time_steps: Any = self.mtd_workflow.measure_times
            uncertainty_data: Any = self.mtd_workflow.rsigs
            uncertainty_figure_title = "Prediction of σ(I)/I"
            #    ax_intensity.set_ylabel('Peak I/σ(I)')
            uncertainty_figure_yaxis = "σ(I)/I (%)"

        # if self.prediction_model_type=='Poisson Model':
        if self.prediction_model_type == "Linear Interpolation":
            time_steps = self.mtd_workflow.timeseries_plt
            uncertainty_data = self.mtd_workflow.temporal_poisson_uncertainty
            uncertainty_figure_title = "Prediction of Uncertainty"
            uncertainty_figure_yaxis = "Uncertainty (%)"
            time_steps = np.array(time_steps)
            uncertainty_data = np.array(uncertainty_data)
            slope = uncertainty_data[-1] ** 0.5
            x_range = np.linspace(max(time_steps), max(time_steps) + 2000, 100)
            y_range = slope * (1 / x_range**0.5)

            uncertainty_data = np.array(uncertainty_data)
            time_steps = np.array(time_steps)
            nozero_mask = np.where(time_steps > 0)
            x = np.array(time_steps[nozero_mask]).reshape(-1, 1)
            y = np.array(uncertainty_data[nozero_mask])

            # Transform X to 1/X
            x_transformed = 1 / x**0.5

            _trace("X_transformed")
            _trace(x_transformed)
            _trace("y")
            _trace(y)
            # Create and fit the model
            model = LinearRegression()
            model.fit(x_transformed, y)

            # Get the slope (coefficient) and intercept
            slope = model.coef_[0]
            intercept = model.intercept_

            _trace(f"Slope: {slope}, Intercept: {intercept}")

            # Add a dashed line with the slope and intercept
            x_range = np.linspace(max(time_steps), max(time_steps) + 2000, 100)
            y_range = slope * (1 / x_range**0.5) + 0 * intercept

        if len(self.mtd_workflow.measure_times) > 0:
            # if False:
            uncertainty_data = np.array(uncertainty_data)
            time_steps = np.array(time_steps)
            x = np.array(time_steps).reshape(-1, 1)
            y = np.array(uncertainty_data) ** -1

            # Transform X to 1/X
            x_transformed = x**0.5

            _trace("X_transformed")
            _trace(x_transformed)
            _trace("y")
            _trace(y)
            # Create and fit the model
            model = LinearRegression()
            model.fit(x_transformed, y)

            # Get the slope (coefficient) and intercept
            slope = model.coef_[0]
            intercept = model.intercept_

            _trace(f"Slope: {slope}, Intercept: {intercept}")

            # Add a dashed line with the slope and intercept
            x_range = np.linspace(max(time_steps), max(time_steps) + 2000, 100)
            y_range = (slope * (x_range**0.5) + intercept) ** -1

            # self.time_steps=self.mtd_workflow.measure_times
            # self.uncertainty_data = self.mtd_workflow.rsigs
            # Fit the data with 1/x

            fig.add_trace(go.Scatter(x=x_range, y=y_range, mode="lines", name="Fitted Line", line={"dash": "dash"}))
            print("============================================================================================")
            _trace("time_steps = self.mtd_workflow.measure_times")
            _trace(time_steps, self.mtd_workflow.measure_times)
            _trace("uncertainty_data = self.mtd_workflow.rsigs")
            _trace(uncertainty_data, self.mtd_workflow.rsigs)
            print("============================================================================================")
            fig.add_trace(go.Scatter(x=time_steps, y=uncertainty_data, mode="lines+markers", name="Uncertainty Data"))
            # fig.add_trace(go.Scatter(x=self.time_steps, y=self.uncertainty_data, mode='lines+markers', name='Uncertainty Data'))#noqa
            fig.update_layout(
                title={"text": uncertainty_figure_title, "x": 0.5, "xanchor": "center"},
                xaxis_title="Time Steps (s)",
                yaxis_title=uncertainty_figure_yaxis,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                margin=_TEMPORAL_FIG_MARGIN,
            )
            fig.update_xaxes(
                showline=True, linewidth=2, linecolor="black", mirror=True, **_TEMPORAL_GRID_KWARGS
            )
            fig.update_yaxes(
                showline=True, linewidth=2, linecolor="black", mirror=True, **_TEMPORAL_GRID_KWARGS
            )
            # fig.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=True, gridcolor='black', gridwidth=1, griddash='dash')#noqa
            # fig.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=True, gridcolor='black', gridwidth=1, griddash='dash')#noqa
            # fig.update_layout(title='Prediction of Uncertainty'+str(self.timestamp)+str(time.time()), xaxis_title='Time Steps', yaxis_title='Uncertainty')#noqa
            # time.sleep(7)
        else:
            fig.update_layout(
                title={"text": uncertainty_figure_title, "x": 0.5, "xanchor": "center"},
                xaxis_title="Time Steps (s)",
                yaxis_title=uncertainty_figure_yaxis,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                margin=_TEMPORAL_FIG_MARGIN,
            )
            fig.update_xaxes(
                showline=True, linewidth=2, linecolor="black", mirror=True, **_TEMPORAL_GRID_KWARGS
            )
            fig.update_yaxes(
                showline=True, linewidth=2, linecolor="black", mirror=True, **_TEMPORAL_GRID_KWARGS
            )

            fig.add_annotation(
                text="Waiting for data",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False,
                font={"size": 20, "color": "red"},
            )
        return fig

    def get_live_data(self) -> None:
        pass

    def generate_prediction_figure(self) -> go.Figure:
        # x_data = list(range(10))
        # y_data = [i**2 for i in x_data]
        fig = make_subplots(rows=1, cols=2)
        return fig

    def stop_live_data(self) -> None:
        """Stop the Mantid MonitorLiveData thread if the workflow is running."""
        if self._mtd_workflow is not None:
            self._mtd_workflow.stop()

    def start_reading_live_mtd_data(self) -> None:
        # Stop any lingering MonitorLiveData thread before starting a new session
        if self._mtd_workflow is not None:
            self._mtd_workflow.stop()
        self._mtd_workflow = MantidWorkflow()
        models = self.get_models()
        if models is not None:
            self._mtd_workflow.update_experiment_info(models)
        self._mtd_workflow.start_live_data_collection_instances()

    async def get_live_mtd_data(self) -> None:  # nolonger used
        while True:
            print("================================get_live_mtd_data===========================")
            models = self.get_models()
            self.mtd_workflow.update_experiment_info(models)
            self.mtd_workflow.live_data_reduction()
            _trace("live data reduction")
            await asyncio.sleep(10)
