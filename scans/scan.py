from artiq.experiment import *
import numpy as np
import time
import inspect
import cProfile, pstats
from scan_framework.scans.data_logger import DataLogger


# allows @portable methods that use delay_mu to compile
def delay_mu(duration):
    pass


class Paused(Exception):
    """Exception raised on the core device when a scan should either pause and yield to a higher priority experiment or
    should terminate."""
    pass


class FitGuess(NumberValue):
    def __init__(self, fit_param=None, param_index=None, use_default=True, use=True, i_result=None, *args, **kwargs):
        self.i_result = i_result
        self.fit_param = fit_param
        self.use_default = use_default
        self.param_index = param_index
        self.use = use
        super().__init__(*args, **kwargs)


class Scan(HasEnvironment):
    """ Base class for all scans. Provides a generalized framework for executing a scan.
    Provides dataset initialization, mutating, fitting, validation of data, pausing/resuming, and
    plotting of scan data.

    **Scan Callbacks**

    Various callbacks are provided that execute at certain moments of a scan's life cycle.  Using callbacks allows
    code in child classes to execute at predefined stages of the scan.  The following callback methods are available,
    listed in order of execution.  (see the 'Scan Callbacks' section for additional information)
    """
    # -- kernel invariants
    kernel_invariants = {'npasses', 'nbins', 'nrepeats', 'npoints', 'nmeasurements', 'nresults',
                         'do_fit', 'save_fit', 'fit_only','nresults_array','nmeasureresults'}

    # ------------------- Configuration Attributes ---------------------
    # These are set by the child scan class to enable/disable features and control how the scan is run.

    # Feature: dataset mutating
    enable_mutate = True          #: Mutate mean values and standard errors datasets after each scan point.  Used to monitor progress of scan while it is running.

    # Feature: fitting
    enable_fitting = True         #: Set to True to perform fits at the end of the scan and show scan arguments needed for fitting.

    # Feature: pausing/terminating
    enable_pausing = True         #: Check pause via :code:`self.scheduler.check_pause()` and automatically yield/terminate the scan when needed.

    # Feature: count monitoring
    enable_count_monitor = True   #: Update the '/counts' dataset with the average of all values returned by 'measure()' during a single scan point.
    counts_perc = -1              #: Set to a value >= 0 to round the '/counts' dataset to the specified number of digits.

    # Feature: reporting
    enable_reporting = True       #: Print useful information to the Log window before a scan starts (i.e. number of passes, etc.) and when a fit is performed (fitted values, etc.)

    # Feature: warm-up points
    nwarmup_points = 0            #: Number of warm-up points

    # Feature: auto tracking
    enable_auto_tracking = True   #: Auto center the scan range around the last fitted value.

    # Feature: Scan simulating
    simulate_scan = None         #: Set to true to disable certain callbacks that run on the core device.  This is used when simulating a scan without a core device, i.e. for debugging/testing purposes.
    enable_simulations = False    #: Turn on GUI arguments for simulating scans.

    # Feature: host scans
    run_on_core = True            #: Set to False to run scans entirely on the host and not on the core device.
    
    # Feature: profiling/timing
    enable_profiling = False  #: Profile the execution of the scan to find bottlenecks.
    enable_timing = False  #: Enable automatic timing of certain events.  Currently only compilation time is timed.

    # ------------------- Scan State Variables ---------------------
    # Available in callbacks to determine the current state of the scan
    warming_up = False            #: Used in the measure method to determine when warmup points are being run by the framework.

    # ------------------- Internal/Private Variables -------------------
    _name = None
    _logger_name = None
    _analyzed = False
    _fit_guesses = {}
    _hide_arguments = {}

    # ------------------- Private Methods ---------------------
    def __init__(self, managers_or_parent, *args, **kwargs):
        if self._name == None:
            self._name = self.__class__.__name__
        if self._logger_name == None:
            self._logger_name = 'scan'
        self.create_logger()

        # initialize variables
        
        #multiresult models use the below initializations
        self.nresults_array=[] #list of number of results for each measurement
        self.nmeasureresults=0 #total number of measurement results (sum of above list)
        self.nresults=1 #maximum number of results for any measurement, default to 1
        self._measure_results = [0] #array of measure results sized by default to 1, otherwise sized to the maximum number of results for any measurement.

        self.nmeasurements = 0
        self.npoints = 0
        self.npasses = None
        self.nbins = None
        self.nrepeats = None
        self._x_offset = None
        #self.debug = 0
        self.debug = None
        
        self.continuous_scan=None

        self.do_fit = False  #: Fits are performed after the scan completes.  Set automatically by scan framework from the 'Fit Options' argument
        self.save_fit = False  #: Fitted params are saved to datasets.  Set automatically by scan framework from the 'Fit Options' argument
        self.fit_only = False  #: Scan is not run and fits are performed on data from the previous scan.  Set automatically by scan framework from the 'Fit Options' argument

        # -- scan state
        self._paused = False  #: scan is currently paused
        self._terminated = False  #: scan has been terminated
        self.measurement = ''  #: the current measurement

        # -- class variables
        self.measurements = []  #: List of measurements performed on each scan point
        self.calculations = []
        self._ncalcs = 0
        self._model_registry = []
        self._plot_shape = None
        self.min_point = None
        self.max_point = None
        self.tick = None
        self._points = None
        self._warmup_points = None
        self.warming_up = False
        self._check_pause = False

        # this stores "flat" idx point index when a scan is paused.  the idx index is then restored from
        # this variable when the scan resumes.
        self._idx = np.int32(0)
        self._i_pass = np.int32(0)
        self._i_measurement = np.int32(0)

        super().__init__(managers_or_parent, *args, **kwargs)

    # private: for scan.py
    def _profile(self, start=False, stop=False):
        if self.enable_profiling:
            # run scan in profiler
            #   This is useful for tracking down bottlenecks in the host side code only.  It does not profile code
            #   running on the core device.
            if start:
                self.pr = cProfile.Profile()
                self.pr.enable()
            if stop:
                if self.enable_profiling:
                    self.pr.disable()
                    p = pstats.Stats(self.pr)
                    #p.strip_dirs() #gets rid of directory prefix of file locations
                    p.sort_stats('time')
                    p.print_stats(10)
                    p.sort_stats('cumulative')
                    p.print_stats(20)

    # private: for scan.py
    def _initialize(self, resume):
        """Initialize the scan"""
        self._logger.debug("_initialize()")

        # initialize state variables
        self._paused = False
        self.measurement = ""

        # callback
        self._logger.debug("executing prepare_scan callback")

        if not resume:
            ###This is run first call of _initialize (resume=False), override and initialize anything needed at start of experiment
            if self.continuous_scan:
                self._init_continuous()
            #Check if nresults is greater than one, resize the _measure_results array to account for the maximum number of results for any individual measurement
            if self.nresults_array:
                self.nresults=max(self.nresults_array)
            else:
                self.nresults_array=[1]
                self.nmeasureresults=1
            if self.nresults>1:
                self._measure_results=[0 for _ in range(self.nresults)]
                #Override the do_measure function to call measure(point,results) to give a results list (_measure_results) to output results
                self.do_measure=self.do_measure_nresults
            #check simulation, if true set run_on_host true and overwrite do_measure with simulate_measure
            if self.simulate_scan:
                self.run_on_core=False
                self.do_measure=self.simulate_measure
                
            # load scan points
            self._load_points()
            self._logger.debug('loaded points')

        # this expects that self.npoints is available
        self.prepare_scan()
        self.lab_prepare_scan()

        if not resume:
            # display scan info
            if self.enable_reporting:
                self.report(location='top')
        else:
            # display scan info
            if self.enable_reporting:
                self.report()

        if not resume:
            # map gui arguments to class variables
            self.map_arguments()

            self._attach_models()

            # there must be at least one measurement
            if not self.measurements:
                self.measurements = ['main']
            self.nmeasurements = len(self.measurements)

            # expects self._x_offset has been set
            self._offset_points(self._x_offset)
            self._logger.debug("offset points by {0}".format(self._x_offset))

            # initialize storage
            self._init_storage()

            # attach scan to models (expects self.npoints has been set)
            self._attach_to_models()

            # initialize simulations (needs self._x_offset/self.frequency_center)
            if self.simulate_scan:
                self._init_simulations()

            # display scan info
            if self.enable_reporting:
                self.report(location='bottom')

            # reset model states
            self.reset_model_states()

        # callback
        self._logger.debug("executing before_scan callback")
        self.before_scan()

        # -- Initialize Datasets
        #shape,plot_shape,points are set in scan1d/2d,continuous etc. version of _load_points(), gives what the points being scanned over look like
        shape = self._shape
        plot_shape = self._plot_shape
        points = self._points
        # datasets are only initialized/written when a scan can run
        if not self.fit_only:
            # for every registered model...
            for entry in self._model_registry:
                # datasets are only initialized when the scan begins, only written to (to pull from the model into the datasets) if resuming
                if not resume:
                    # initialize datasets if requested by the users
                    if entry['init_datasets']:
                        # initialize the model's datasets
                        entry['datasets_initialized'] = True
                        entry['model'].init_datasets(shape, plot_shape, points, dimension=entry['dimension'])

                        # debug logging
                        self._logger.debug("initialized datasets of model '{0}' {1}".format(entry['name'], entry))
                else:
                    # restore data when resuming a scan by writing the model's local variables to it's datasets
                    self._write_datasets(entry)

                    # debug logging
                    self._logger.debug("wrote datasets of model '{0}' {1}".format(entry['model'], entry))

        self._ncalcs = len(self.calculations)

        if not (hasattr(self, 'scheduler')):
            raise NotImplementedError('The scan has no scheduler attribute.  Did you forget to call super().build()?')
    
    def _init_continuous(self):
        "Override functions necessary to perform a continuous scan. Sets _load_points,_loop,_mutate_plot, _offset_points to be continuous versions"
        self._load_points=ContinuousScan(self,self)._load_points
        self._loop=ContinuousScan(self,self)._loop
        self._mutate_plot=ContinuousScan(self,self)._mutate_plot
        self._offset_points=ContinuousScan(self,self)._offset_points
        if self.continuous_save:
            #Save all continuous data collected to an external hdf file with a resizeable array appended every time the points loop is filled
            self.continuous_logger=DataLogger(self)
        else:
            self.continuous_logger=None

    # private: for scan.py
    @portable
    def _loop(self, resume=False):
        """Main loop: performs measurement at each scan point and mutates datasets with measured values"""
        ncalcs = self._ncalcs
        npoints = self.npoints
        nwarmup_points = self.nwarmup_points
        nmeasurements = self.nmeasurements
        nrepeats = self.nrepeats
        measurements = self.measurements
        points = self._points_flat
        wupoints = self._warmup_points
        i_points = self._i_points
        npasses = self.npasses

        try:
            # callback
            self._before_loop(resume)
            # callback
            if not self.simulate_scan:
                # callback
                self.initialize_devices()

            
            # iterate of passes
            while self._i_pass < npasses:
                # update offset into self.dataptr[] where data begins for this pass
                last_pass = self._i_pass == npasses - 1
                poffset = self._i_pass * nrepeats

                # callback
                if not resume or self._idx == 0:
                    self.before_pass(self._i_pass)

                # inner loop
                self._point_loop(points,
                                 wupoints,
                                 i_points,
                                 npoints,
                                 nwarmup_points,
                                 ncalcs,
                                 poffset,
                                 nrepeats,
                                 nmeasurements,
                                 measurements,
                                 last_pass=last_pass)

                # update loop counter
                self._idx = 0
                self._i_pass += 1

            # reset loop counter
            self._i_pass = 0

        except Paused:
            self._paused = True
        finally:
            self.cleanup()

    # private: for scan.py
    @portable
    def _point_loop(self, points, warmup_points, i_points, npoints, nwarmup_points, ncalcs, poffset, nrepeats,
                    nmeasurements, measurements, last_pass=False):
        # -- warm-up points
        self.warming_up = True
        if nwarmup_points:
            self.warming_up = True
            for wupoint in warmup_points:
                for i_measurement in range(nmeasurements):
                    self.measurement = measurements[i_measurement]
                    self.warmup(wupoint)
            self.warming_up = False

        # -- loop over the scan points
        while self._idx < npoints - 1:
            # lookup the scan point (point) and the scan point index (i_point) at the current loop index (idx)
            point = points[self._idx]
            self._i_point = i_points[self._idx]

            # repeat measurement on scan point
            # first two arguments are point because point (value in the scan points array) is assumed to be the same as measure point (value you would like to
            # pass to the measure method). This is different for a continuous scan  that uses the first point as the number of scan points run, and the second as
            # the value that the measure function should use.
            self._repeat_loop(point, point, self._i_point, nrepeats, nmeasurements, measurements, poffset, ncalcs,
                              last_point=False, last_pass=last_pass)
            self._idx += 1

        # last scan point is special (optimization)
        point = points[npoints - 1]
        self._i_point = i_points[npoints - 1]
        self._repeat_loop(point, point, self._i_point, nrepeats, nmeasurements, measurements, poffset, ncalcs,
                          last_point=True, last_pass=last_pass)

        # -- reset loop counter
        self._idx = 0

    # private: for scan.py
    @portable
    def _repeat_loop(self, point, measure_point, i_point, nrepeats, nmeasurements, measurements, poffset, ncalcs,
                     last_point=False, last_pass=False):
        # see if check for higher priority experiment or termination requested raised at end of previous _repeat_loop. Do this so blocking rpc (the check_pause call)
        # isn't blocked by the quickly sent async rpc's called afterwords. Also allows user to manually set _check_pause status themselves and not lose deadtime when they
        # have slack on last pass
        if self._check_pause:
            # yield
            self._check_pause=False #reset for when scan restarts
            raise Paused

        # dynamically offset the scan point
        measure_point = self.offset_point(i_point, measure_point)
        
        # callback
        self.set_scan_point(i_point, measure_point)

        # iterate over repeats
        counts = np.int32(0)
        
        for i_repeat in range(nrepeats):
            # iterate over measurements
            for i_measurement in range(nmeasurements):
                # so other methods know what the current measurement is
                self.measurement = measurements[i_measurement]

                # callback
                self.before_measure(measure_point, self.measurement)
                self.lab_before_measure(measure_point, self.measurement)
                
                self.do_measure(measure_point)
                for i_result in range(self.nresults_array[i_measurement]):

                    count=self._measure_results[i_result]
                    self._data[i_measurement][i_result][i_repeat] = count
                    counts += count

                # callback
                self.after_measure(measure_point, self.measurement)
                self.lab_after_measure(measure_point, self.measurement)
        # update the dataset used to monitor counts
        mean = counts / (nrepeats*self.nmeasureresults)
        
        if self.enable_pausing:
            # cost: 3.6 ms slack, is blocking. Call on your last loop when you have 3.6ms slack and disable pausing to 
            #still check pausing but remove this delay
            self._check_pause = self.scheduler.check_pause()
            
        # cost: 18 ms per point, around 100us slack as async rpc, can block other rpc calls though
        # mutate dataset values
        if self.enable_mutate:
            for i_measurement in range(nmeasurements):
                # get data for model, only send this measurement, and only the nresults for this measurement
                data = self._data[i_measurement][0:self.nresults_array[i_measurement]]

                # get the name of the measurement
                measurement = self.measurements[i_measurement]

                # rpc to host to send data to the model
                self.mutate_datasets(i_point, poffset, measurement, point, data)
        # perform calculations
        if ncalcs > 0:
            # rpc to host
            self._calculate_all(i_point, measure_point)
        # analyze data
        self._analyze_data(i_point, last_pass, last_point)
        # callback
        self.after_scan_point(i_point, measure_point)
        self._after_scan_point(i_point, measure_point, mean)
        # async rpc to host loses about 20us slack can block other rpc calls though
        if self.enable_count_monitor:
            # cost: 2.7 ms
            self._set_counts(mean)
    # private: for scan.py
    def map_arguments(self):
        """Map coarse grained attributes to fine grained options."""

        if self.enable_fitting:
            # defaults
            self.do_fit = False
            self.save_fit = False
            self.fit_only = False

            if hasattr(self, 'fit_options'):
                if self.fit_options == 'No Fits':
                    self.do_fit = False
                    self.save_fit = False
                    self.fit_only = False
                if self.fit_options == 'Fit':
                    self.do_fit = True
                    self.save_fit = False
                    self.fit_only = False
                if self.fit_options == 'Fit and Save':
                    self.do_fit = True
                    self.save_fit = True
                    self.fit_only = False
                if self.fit_options == 'Fit Only':
                    self.do_fit = True
                    self.save_fit = False
                    self.fit_only = True
                if self.fit_options == 'Fit Only and Save':
                    self.do_fit = True
                    self.save_fit = True
                    self.fit_only = True

        self._map_arguments()

    # private: for scan.py
    def _init_storage(self):
        """initialize memory to record counts on core device"""

        #: 3D array of counts measured for a given scan point, i.e. nmeasurement*nrepeats*nresults
        self._data = np.zeros((self.nmeasurements, self.nresults,self.nrepeats),dtype=np.int32)
        self._logger.debug('initialized storage')

    # private: for scan.py
    def _attach_to_models(self):
        """Attach the scan to all models"""
        for i, entry in enumerate(self._model_registry):
            model = entry['model']
            self._attach_to_model(model, i)
            self._logger.debug("attached scan to model '{0}'".format(entry['name']))

    # private: for scan.py
    def _attach_to_model(self, model, i):
        """Attach the scan to a single model.
        Allows passing scan variables to the model at runtime"""
        model.attach(self)

    # private: for scan.py
    def _attach_models(self):
        """Attach a single model to the scan"""
        self.__load_x_offset()

    # private: for scan.py
    def __load_x_offset(self):
        self._x_offset = self.__get_x_offset()
        if self._x_offset:
            self._logger.debug("set _x_offset to {0}".format(self._x_offset))

    # private: for scan.py
    def __get_x_offset(self):
        # offset has been manually set by the user:
        if self._x_offset != None:
            return self._x_offset
        # automatic determination of x_offset:
        else:
            if self.enable_auto_tracking:
                for entry in self._model_registry:
                    model = entry['model']
                    if 'auto_track' in entry and entry['auto_track']:
                        # use the last performed fit
                        if entry['auto_track'] == 'fitresults' and hasattr(model, 'fit'):
                            return model.fit.fitresults[model.main_fit]
                        # use dataset value
                        elif entry['auto_track'] == 'fit' or entry['auto_track'] == True:
                            return model.get_main_fit(archive=False)

        # default to no offset if none of the above cases apply
        return 0.0

    # private: for scan.py
    def _init_simulations(self):
        for entry in self._model_registry:
            # measurement models...
            if entry['measurement']:
                # make a copy of simulation args to speed up simulations (don't have to recompute at each scan point)
                model=entry['model']
                if hasattr(model,"models"):
                    ###if hasattr models this is a multiresult model and will loop through all models in that multiresult model
                    models=model.models
                else:
                    ###else normal model, just make this an array so the for loop below behaves and only loops for the singular model
                    models=[model]
                for model in models:
                    try:
                        model._simulation_args = model.simulation_args
                        self._logger.debug('initialized model {0} simulation args to {1}'.format(model.__class__, model._simulation_args))
                    except NotImplementedError:
                        pass

        self._logger.debug('initialized simulations')

    # private: for scan.py
    def reset_model_states(self):
        # every registered model...
        for entry in self._model_registry:
            entry['model'].reset_state()

    # private: for scan.py
    def _init_model_datasets(self, shape, plot_shape, points, x, y, init_local, write_datasets):
        """Set the contents and handling modes of all datasets in the scan."""

    # RPC
    # private: for scan.py
    def _timeit(self, event):
        if event == 'compile':
            elapsed = time.time() - self._profile_times['before_compile']
            self._logger.warning('core scan compiled in {0} sec'.format(elapsed))

    # private: for scan.py
    @portable
    def _rewind(self, num_points):
        """Rewind the cursor from the current pass and point indices by the specified number of points.  The cursor can
          be rewound into a previous pass.  The cursor cannot be rewound past the first point of the first pass.

          :param num_points: The current cursor will be moved to this number of scan points before its current value.
        """

        # get new i_point, i_pass indices
        if num_points > 0:
            self._idx -= num_points
            if self._idx < 0:
                if self._i_pass == 0:
                    self._idx = 0
                else:
                    self._i_pass -= 1
                    self._idx = self.npoints + self._idx

    # private: for scan.py
    def _calculate(self, i_point, point, calculation, entry):
        """Perform calculations on collected data after each scan point"""
        model = entry['model']
        value,error = model.mutate_datasets_calc(i_point, point, calculation)
        if 'mutate_plot' in entry and entry['mutate_plot']:
            self._mutate_plot(entry, i_point, point, value,error)

    # ------------------- Interface Methods ---------------------

    # interface: for child class (optional)
    def build(self, **kwargs):
        """ Interface method (optional, has default behavior)

        Creates the :code:`scheduler` and :code:`core` devices and sets them to the attributes
        :code:`self.scheduler` and :code:`self.core` respectively.

        :param kwargs: Optional dictionary of class attributes when using the scan as a sub-component (i.e. the
                       scan does not inherit from :code:`EnvExperiment`).  Each entry will be set as an attribute of the scan.
        """
        self.__dict__.update(kwargs)

        # devices
        self.setattr_device('scheduler')
        self.setattr_device("core")

    # helper: for child class (optional)
    def run(self, resume=False):
        """Helper method

        Initializes the scan, executes the scan, yields to higher priority experiments,
        and performs fits on completion on the scan."""
        try:
            # start the profiler (if it's enabled)
            self._profile(start=True)

            # initialize the scan
            self._initialize(resume)
            # run the scan
            if not self.fit_only:
                if resume:
                    self._logger.debug(
                        'resuming scan at (i_pass, i_point) = ({0}, {1})'.format(self._i_pass, self._i_point))
                else:
                    self._logger.debug(
                        'starting scan at (i_pass, i_point) = ({0}, {1})'.format(self._i_pass, self._i_point))
                if self.run_on_core:
                    if self.enable_timing:
                        self._profile_times = {
                            'before_compile': time.time()
                        }
                    self._logger.debug("compiling core scan...")
                    self._run_scan_core(resume)
                else:
                    self._run_scan_host(resume)
                self._logger.debug("scan completed")

                # yield to other experiments
                if self._paused:
                    self._yield()  # self.run(resume=True) is called after other experiments finish and this scan resumes
                    return

            # callback
            self._logger.debug("executing _after_scan callback")
            if not self._after_scan():
                return

            # callback
            self._logger.debug("executing after_scan callback")
            self.after_scan()

            # perform fits
            self._logger.debug("executing _analyze")
            self._analyze()

            self.after_analyze()
            self.lab_after_analyze()

            # callback
            self._logger.debug("executing lab_after_scan callback")
            self.lab_after_scan()

        finally:
            # stop the profiler (if it's enabled)
            self._profile(stop=True)

        # callback with default behavior: for child class

    # interface: for child class or extension (required)
    def get_scan_points(self):
        """Interface method (required - except when inheriting from TimeFreqScan, TimeScan, or FreqScan)

        Returns the set of scan points that will be iterated over during the scan.
        See the _point_loop() method

        :returns: The list of scan points to scan over.
        :rtype:  A Python list or an ARTIQ Scannable type.
        """
        raise NotImplementedError('The get_scan_points() method needs to be implemented.')

    # interface: for child class (optional)
    def get_warmup_points(self):
        """Interface method (optional, has default behavior)

        Returns the set of warm-up points that will be iterated before scanning over the scan points.

        :returns: The list of warm-up points.
        :rtype:  A Python list or an ARTIQ Scannable type.
        """
        return [0 for _ in range(self.nwarmup_points)]

    # interface: for child class (optional)
    def create_logger(self):
        """Interface method (optional, has default behavior)

        Sets self.logger to an instance of a python logging.logger for writing log messages
        to the log window in the dashboard.
        """
        import logging
        self.logger = logging.getLogger(self._logger_name)
        self._logger = logging.getLogger("scan_framework.scans.scan")

    # interface: for child class
    def report(self, location='both'):
        """Interface method (optional, has default behavior)

        Logs details about the scan to the log window.
        Runs during initialization after the scan points and warmup points have been loaded but before datasets
        have been initialized.
        """

        if location == 'top' or location == 'both':
            if self.npasses == 1 and self.nrepeats == 1:
                self.logger.info('START {} / {} pass / {} repeat'.format(self._name, self.npasses, self.nrepeats))
            elif self.nrepeats > 1:
                self.logger.info('START {} / {} pass / {} repeats'.format(self._name, self.npasses, self.nrepeats))
            else:
                self.logger.info(
                    'START {} / {} passes / {} repeats'.format(self._name, self.npasses, self.nrepeats))

        if location == 'bottom' or location == 'both':
            # self.logger.info('Passes: %i' % self.npasses)
            # self.logger.info('Repeats: %i' % self.nrepeats)
            # self.logger.info('Bins: %i' % self.nbins)
            self._logger.debug('do_fit {0}'.format(self.do_fit))
            self._logger.debug('save_fit {0}'.format(self.save_fit))
            self._logger.debug('fit_only {0}'.format(self.fit_only))
            self._report()

    # interface: for child class (required)
    @portable
    def measure(self, point):
        """Interface method  (required)

        Performs a single measurement and returns the result of the measurement as an integer.

        :param point: Current scan point value
        :returns: The result of a single measurement
        :rtype: Integer
        """
        raise NotImplementedError('The measure() method needs to be implemented.')

    # interface: for child class (optional)
    @portable
    def warmup(self, point):
        """Interface method  (optional)

        Contains experimental code to execute at each warmup point.
        If this method is not implemented, each warmup point will execute the measure method.

        :param point: Current warmup point value
        """
        return self.do_measure(point)

    # interface: for child class (optional)
    @rpc(flags={"async"})
    def mutate_datasets(self, i_point, poffset, measurement, point, data):
        """Interface method  (optional, has default behavior)

        If this method is not overridden, all data collected for the specified measurement during the
        current scan point is passed to any model that has been registered for the given measurement.
        The :code:`mutate_datasets()` and :code:`_mutate_plot()` methods of these models will be called with :code:`data`
        passed as an argument. Thus, the registered models will calculate means and standard errors and plot these
        statistics to the current scan applet for the current scan point.

        Typically, the default implementation of this method is used, though it can be overridden in user scans
        to manually perform statistic calculation and plotting of measurement data at the end of each scan point.

        Notes
            - Always runs on the host device.

        :param i_point: Index of the current scan point.
        :param measurement: Name of the current measurement (For multiple measurements).
        :param point: Value of the current scan point.
        :param data: List of integers containing the values returned by :code:`measure()` at each repetition of the current scan point.
        """
        self.measurement = measurement
        for entry in self._model_registry:
            # model registered for this measurement
            if entry['measurement'] and entry['measurement'] == measurement:
                # mutate the stats for this measurement with the data passed from the core device
                mean,error = entry['model'].mutate_datasets(i_point, poffset, point, data)
                self._mutate_plot(entry, i_point, point, mean,error)

    # interface: for child class (optional)
    def analyze(self):
        """Interface method  (optional)

        :return:
        """
        if not self._analyzed and not self._terminated:
            self._analyze()

    # interface: for child class (optional)
    def _yield(self):
        """Interface method  (optional)

        Yield to scheduled experiments with higher priority
        """
        try:
            self.logger.warning("Yielding to higher priority experiment.")
            self.core.comm.close()
            self.scheduler.pause()

            # resume
            self.logger.warning("Resuming")
            self.run(resume=True)

        except TerminationRequested:
            self.logger.warning("Scan terminated.")
            self._terminated = True
            #Scan has ended, append remaining data collected to external hdf file if continuous scan saving enabled
            if self.continuous_save:
                first_pass=self.continuous_points>=int(self.continuous_index)
                ContinuousScan(self,self).continuous_logging(self,self.continuous_logger,first_pass)

    # interface: for child class (optional)
    # RPC
    @rpc(flags={"async"})
    def _set_counts(self, counts):
        """Interface method  (optional)

        Runs after a scan point completes.  By default, this method sets the :code:`counts` dataset
        to the value passed in on the :code:`counts` parameter of this method.  It therefore also
        updates the count monitor dataset with the average value measured at the current scan point
        while the scan is running.

        :param counts: Average value of all values returned from :code:`measure()` during the current scan point.

        Notes
            - Does not run if :code:`self.enable_count_monitor == False`
        """
        if self.counts_perc >= 0:
            counts = round(counts, self.counts_perc)
        self.set_dataset('counts', counts, broadcast=True, persist=True)

    # interface: for child class (optional)
    @rpc(flags={"async"})
    def _calculate_all(self, i_point, point):
        # for every registered calculation....
        for calculation in self.calculations:
            for entry in self._model_registry:
                # models that are registered for the calculation...
                if entry['calculation'] and entry['calculation'] == calculation:
                    # perform the calculation
                    if self.before_calculate(i_point, point, calculation):
                        self._calculate(i_point, point, calculation, entry)

    # interface: for child class
    def _get_fit_guess(self, fit_function):
        """Maps GUI arguments to fit guesses.  """
        guess = {}
        signature = inspect.getargspec(getattr(fit_function, 'value')).args
        # map gui arguments to fit guesses
        for key in self._fit_guesses.keys():
            g = self._fit_guesses[key]
            if g['use']:
                # generic fit guess gui arguments specified by position in the fit function signature
                if g['fit_param'] == None and g['param_index'] != None:
                    i = g['param_index']
                    if i < len(signature):
                        g['fit_param'] = signature[i]
                if g['fit_param'] != None:
                    guess[g['fit_param']] = g['value']
        return guess

    # interface: for child class (optional)
    def _analyze(self):
        """Interface method (optional, has default behavior)

        If this method is not overridden, fits will be performed automatically on the mean values calculated
        for each measurement of the scan.

        Calls :code:`before_analyze()`, checks to see if fits should be performed, and performs a fit using
        each model that has been registered as performing a fit (i.e. :code:`fit=True` when calling
        :code:`register_model()`).  After fits have been performed, :code:`after_fit()` and :code:`report_fit()`
        are called.
        """
        self.before_analyze()
        self._analyzed = True
        # should/can fits be performed? ...
        if self.do_fit and self.enable_fitting:

            #Perform a fit for each registered fit model and save the fitted params to datasets.
            #
            #If self.save_fit is true, the main fit is broadcast to the ARTIQ master,
            #persisted and saved.  If self.save_fit is False, the main fit is not broadcasted or persisted but is saved
            #so that it can still be retrieved using normal get_dataset methods before the experiment has completed.

            # for every registered model...
            for entry in self._model_registry:
                # registered fit models
                if entry['fit']:
                    model = entry['model']
                    if hasattr(model,"fit_models"):
                        ###if hasattr fit_models this is a multiresult model and will loop through all fit models in that multiresult model
                        models=model.fit_models
                    else:
                        ###else normal model, just make this an array so the for loop below behaves and only loops for the singular model
                        models=[model]
                    for model in models:
                        # callback
                        if self.before_fit(model) != False:
    
                            # what's the correct data source?
                            #   When fitting only (no scan is performed) the fit is performed on data from the last
                            #   scan that ran, which is assumed to be in the 'current_scan' namespace.
                            #   Otherwise, the fit is performed on data in the model's namespace.
                            use_mirror = model.mirror == True and self.fit_only
                            save = self.save_fit
    
                            # dummy values, these are only used in 2d scans
                            dimension = 0
                            i = 0
    
                            # perform the fit
                            self._logger.debug('performing fit on model \'{0}\''.format(entry['name']))
                            fit_performed, valid, main_fit_saved, errormsg = self._fit(entry, model,save, use_mirror, dimension, i)
    
                            entry['fit_valid'] = valid
    
                            # tell current scan to plot data...
                            model.set('plots.trigger', 1, which='mirror')
                            model.set('plots.trigger', 0, which='mirror')
    
                            # params not saved warning occurred
                            if save and not main_fit_saved:
                                self.logger.warning("Fitted params not saved.")
    
                            # callback
                            self._main_fit_saved = main_fit_saved
                            self._fit_valid = valid
                            if fit_performed:
                                self.after_fit(entry['fit'], valid, main_fit_saved, model)
    
                        # print the fitted parameters...
                        if self.enable_reporting and fit_performed:
                            self.report_fit(model)

    # interface: for extensions (required)
    def _write_datasets(self, entry):
        pass

    # interface: for extensions (required)
    def _load_points(self):
        pass

    # interface: for extensions (required)
    def _offset_points(self, x_offset):
        raise NotImplementedError('The _offset_points() method needs to be implemented.')

    # interface: for extensions (optional)
    def _report(self):
        pass

    # interface: for extensions (required)
    def _mutate_plot(self, entry, i_point, data, mean,error):
        raise NotImplementedError()

    # interface: for extensions (required)
    def calculate_dim0(self, dim1_model):
        """User callback (runs on host).

        Returns a value and its error from the dimension 1 sub-scan.  The returned value will be plotted
        as  the y-value in the dimension 0 plot and the returned error will weight the final fit along dimension 0.

        :param model: The model which just performed a fit along the dimension 1 sub-scan.  :code:`model.fit` points to
                      the :class:`Fit <scan_framework.analysis.curvefits.Fit>` object from the
                      :ref:`analysis <analysisapi>` package.
        :type model: ScanModel
        :returns: The calculated value and the error in the calculated value.
        :rtype: A two entry tuple where the first entry is the calculated value and the second entry is the error
                in the calculated value.
        """
        raise NotImplementedError

    # interface: for extensions (optional)
    @portable
    def do_measure(self, point):
        """Provides a way for subclasses to override the method signature of the measure method. You MUST return the result of the measuerment into 
        the self._measure_results array. If you only have one value to return, do _measure_results[0]=self.measure(point). If you have multiple results for
        a single measurement, iterate through the array for each result, while only calling measure once, ideally passing _measure_results as an array to modify"""
        self._measure_results[0]=self.measure(point)
    @portable
    def do_measure_nresults(self, point):
        """Provides a way for subclasses to override the method signature of the measure method. You MUST return the result of the measuerment into 
        the self._measure_results array. If you only have one value to return, do _measure_results[0]=self.measure(point). If you have multiple results for
        a single measurement, iterate through the array for each result, while only calling measure once, ideally passing _measure_results as an array to modify"""
        #multiresult model used in this scan, fill your results into the _measure_results list passed in the second argument of self.measure
        self.measure(point,self._measure_results)

    # ------------------- Helper Methods ---------------------
    # helper: for child class
    def setattr_argument(self, key, processor=None, group=None, show='auto'):
        if show == 'auto' and hasattr(self, key) and getattr(self, key) != None:
            return
        if show == False or key in self._hide_arguments:
            if not key in self._hide_arguments:
                self._hide_arguments[key] = True
            return

        # fit guesses
        if isinstance(processor, FitGuess):
            if group == None:
                group = 'Fit Settings'
            super().setattr_argument(key, NumberValue(default=processor.default_value,
                                                      ndecimals=processor.ndecimals,
                                                      step=processor.step,
                                                      unit=processor.unit,
                                                      min=processor.min,
                                                      max=processor.max,
                                                      scale=processor.scale), group)
            use = None
            if processor.use == 'ask':
                super().setattr_argument('use_{0}'.format(key), BooleanValue(default=processor.use_default), group)
                use = getattr(self, 'use_{0}'.format(key))
            else:
                use = processor.use

            self._fit_guesses[key] = {
                'fit_param': processor.fit_param,
                'param_index': processor.param_index,
                'use': use,
                'value': getattr(self, key)
            }
        else:
            super().setattr_argument(key, processor, group)

        # set attribute to default value when class is built but not submitted
        if hasattr(processor, 'default_value'):
            if not hasattr(self, key) or getattr(self, key) == None:
                setattr(self, key, processor.default_value)

    # helper: for child class
    def scan_arguments(self, npasses={}, nrepeats={}, nbins={}, fit_options={},continuous_scan={},continuous_points={},continuous_plot={},continuous_measure_point={},continuous_save={}, guesses=False):
        # assign default values for scan GUI arguments
        if npasses != False:
            for k,v in {'default': 1, 'ndecimals': 0, 'step': 1}.items():
                npasses.setdefault(k, v)
        if nrepeats != False:
            for k,v in {'default': 100, 'ndecimals': 0, 'step': 1}.items():
                nrepeats.setdefault(k, v)
        if nbins != False:
            for k,v in {'default': 50, 'ndecimals': 0, 'step': 1}.items():
                nbins.setdefault(k, v)
        if fit_options != False:
            for k,v in {'values': ['No Fits','Fit',"Fit and Save","Fit Only","Fit Only and Save"], 'default': 'Fit'}.items():
                fit_options.setdefault(k, v)

        if npasses != False:
            self.setattr_argument('npasses', NumberValue(**npasses), group='Scan Settings')
        if nrepeats != False:
            self.setattr_argument('nrepeats', NumberValue(**nrepeats), group='Scan Settings')
        if nbins != False:
            self.setattr_argument('nbins', NumberValue(**nbins), group='Scan Settings')
        
        ### Set continuous scan argument options
        if continuous_scan != False:
            for k,v in {'default': False}.items():
                continuous_scan.setdefault(k, v)
        if continuous_points != False:
            for k,v in {'default': 1000, 'ndecimals': 0, 'step': 1}.items():
                continuous_points.setdefault(k, v)
        if continuous_plot != False:
            for k,v in {'default': 50, 'ndecimals': 0, 'step': 1}.items():
                continuous_plot.setdefault(k, v)
        if continuous_measure_point != False:
            for k,v in {'default': 0.0}.items():
                continuous_measure_point.setdefault(k, v)
        if continuous_save != False:
            for k,v in {'default': False}.items():
                continuous_save.setdefault(k, v)
        if continuous_scan != False:
            self.setattr_argument('continuous_scan',BooleanValue(default=False),group='Continuous Scan')#, tooltip="make this a continuous scan.")
        if continuous_points != False:
            self.setattr_argument('continuous_points',NumberValue(default=1000,ndecimals=0,step=1),group='Continuous Scan')#, tooltip="number of points to save to stats datasets. Points are overriden after this replacing oldest point taken.")
        if continuous_plot != False:
            self.setattr_argument('continuous_plot',NumberValue(default=50,ndecimals=0,step=1),group='Continuous Scan')#, tooltip = "number of points to plot, plotted points scroll to the right as more are plotted, replacing the oldest point.")
        if continuous_measure_point != False:
            self.setattr_argument('continuous_measure_point',NumberValue(default=0.0),group='Continuous Scan')#, tooltip = "point value to be passed to the measure() method. Offset_points and self._x_offset are compatible with this")
        if continuous_save != False:
            self.setattr_argument('continuous_save',BooleanValue(default=False),group='Continuous Scan')#, tooltip = "Save points to external file when datasets will be overriden. Currently not implemented")
        
        if self.enable_fitting and fit_options != False:
            fovals = fit_options.pop('values')
            self.setattr_argument('fit_options', EnumerationValue(fovals, **fit_options), group='Fit Settings')
            if guesses:
                 if guesses == True:
                     for i in range(1, 6):
                         key = 'fit_guess_{0}'.format(i)
                         self.setattr_argument(key,
                                               FitGuess(default=1.0,
                                                        use_default=False,
                                                        ndecimals=6,
                                                        step=0.001,
                                                        fit_param=None,
                                                        param_index=i))
                 else:
                     for fit_param in guesses:
                        key = 'fit_guess_{0}'.format(fit_param)
                        self.setattr_argument(key,
                                              FitGuess(default=1.0,
                                                       use_default=True,
                                                       ndecimals=1,
                                                       step=0.001,
                                                       fit_param=fit_param,
                                                       param_index=None))
        if self.enable_simulations:
            group = 'Simulation'
            self.setattr_argument('simulate_scan', BooleanValue(default=False), group=group)
            self.setattr_argument('noise_level', NumberValue(default=1, ndecimals=2, step=0.1), group=group)
            self.setattr_argument('debug', NumberValue(default=0, ndecimals=0, scale=1, step=1), group=group)
            
        self._scan_arguments()

    # helper: for child class
    def register_model(self, model_instance, measurement=None, fit=None, calculation=None,
                       init_datasets=True,nresults=1, **kwargs):
        """Register a model with the scan.  Models can be registered as a measurement model, fit model,
        calculation model, or combinations of these.

        When registered as a measurement model, all data collected for the specified measurement is passed to the
        specified model instance's mutate_datasets() method via an RPC after it has been collected.

        When registered as a fit model, fitting will be performed by the specified model instance after the scan
        completes.  The model instance's fit_data(), validate_fit(), set_fits(), and save_main_fit() methods
        will be called.

        When registered as a calculation model, the specified model instance's mutate_datasets_calc() method will be
        called at the end of each scan point.

        :param model_instance: Instance of the scan model being registered
        :type model_instance: :class:`scan_framework.models.scan_model.ScanModel`
        :param measurement: The name of the measurement for which the model will calculate and save statistics.
                            When only a single measurement is performed by the scan, this can simply be set to True.
                            If not set to a string or to True, statistics will not be generated or saved. If set to
                            a string or True, the registered model's mutate_datasets() method will be called via an RPC after
                            each scan point completes.  The default behavior of this method is to calculate the
                            mean value measured at the scan point, calculate the standard error of this mean,
                            and to mutate the datasets storing these values under the model's namespace.  Additionally,
                            this updates the current scan applet to plot the new mean and error after each scan point
                            completes.  The mutate_datasets() method also mutates the 'counts' dataset, which
                            stores every value measured and returned by the scan's 'measure()' method, and optionally
                            mutates histogram datasets so that the histogram applets/plots are updated after each scan
                            point completes.  Defaults to None
        :type measurement: string or bool
        :param fit: The name of the measurement for which the model will perform fits.  When only a single measurement
                    is performed by the scan, this can simply be set to True.  If not set to a string or to True,
                    fitting will not be performed by the model.  If set to a string or True, the registered model's
                    fit_data() method will be called after the scan completes to perform a fit using the mean values
                    and standard errors stored under the model's namespace.  Typically, a model tthat is registered with
                    the fit argument set is also registered with the measurement set, though this is not strictly necessary
                    if the means and errors have been generated by some other means by the user.  Defaults to None
        :type fit: string or bool
        :param calculation: Name of a calculation that this model will perform at each scan point.  When set to
                            a string or to True, the model's mutate_datasets_calc() method is called after each
                            scan point with the calculation name passes in on the calculation argument.  The mutate_datasets_calc()
                            method, in turn calls the model's calculate() method which performs the calculation and
                            returns the calculated value along with its error.  The calculated value and its error is
                            then set to the datasets along with the value of the current scan point under the namespace
                            of the registered model.  Defaults to None
        :type calculation: string or bool
        :param init_datasets: If True, all datasets relevant to the scan are initialized under the model's namespace by
                            calling the model's init_datasets() method,  defaults to True
        :type init_datasets: bool
        :param validate: If True, all validation rules defined in the model will be applied to the data to be fit
                         and/or the fit params found by this model during fitting.  If False, no validations will be perforemd
                         by the model.
        :type validate: bool
        :param set: If True, all relevant data for a fit will be saved to the datasets by calling the model's set_fits() method.
                    The set_fits() method is only called if fits have been performed by the model.
        :type set: bool
        :param save: If True, the fit param specified by the model's 'main_fit' attribute will be saved to the datasets
                     when the fitted params pass all strong validation rules defined in the model.  If no strong validation
                     rules are defined, the main fit param is always saved as long as the fit was performed.  If validations
                     are disabled, the main fit param is always saved.
        """

        # map args
        if calculation == True:
            calculation = 'main'
        if measurement == True:
            measurement = 'main'
        if fit == True:
            fit = 'main'

        # maintain a list of all models registered so that, later, we can dynamically bind the scan to each model
        # and perform any other needed model initializations (this includes calc models)
        #if name not in self._models:
        #    self._models.append(name)

        # maintain a dynamic registry of all model instances so they can each be called after a scan point
        # has completed

        entry = {
            'model': model_instance,
            'init_datasets': init_datasets,
            'datasets_initialized': False,
            'measurement': measurement,
            'fit': fit,
            'calculation': calculation,
            'name': model_instance.__class__.__name__,
            'nresults':nresults
        }

        # tack on any additional user defined settings
        entry = {
            **kwargs, **entry
        }

        # default to dimension 0 for 1D scans
        if 'dimension' not in entry:
            entry['dimension'] = 0

        # register the model
        self._model_registry.append(entry)

        # debug logging
        if not measurement and not calculation and not fit:
            self._logger.debug('registered model \'{0}\' {1}'.format(entry['name'], entry))
        else:
            if measurement:
                self._logger.debug('registered measurement model \'{0}\' {1}'.format(entry['name'], entry))
            if calculation:
                self._logger.debug('registered calculation model \'{0}\' {1}'.format(entry['name'], entry))
            if fit:
                self._logger.debug('registered fit model \'{0}\' {1}'.format(entry['name'], entry))

        # auto-register calculations and measurements
        if calculation and calculation not in self.calculations:
            self.calculations.append(calculation)

        if measurement and measurement not in self.measurements:
            self.measurements.append(measurement)
            self.nresults_array.append(nresults)
            self.nmeasureresults+=nresults
    # helper method: for scan.py or child class
    @kernel
    def _run_scan_core(self, resume=False):
        """Helper Method:

        Executes the scan on the core device.
        Calls :code:`lab_before_scan_core()`, then :code:`_loop()`, followed by :code:`after_scan_core()` and
        :code:`lab_after_scan_core()`

        :param resume: Set to True if the scan is being resumed after being paused and to False if the scan is being
                       started for the first time.
        """
        if self.enable_timing:
            self._timeit('compile')
        if self.enable_pausing:
            # cost: 3.6 ms slack, is blocking. This just checks at start of experiment if you wanted to pause before running experiment
            self._check_pause = self.scheduler.check_pause()
        self._logger.debug("running scan on core device")
        self.lab_before_scan_core()
        self._loop(resume)
        self.after_scan_core()
        self.lab_after_scan_core()

    # helper method: for scan.py or child class
    def _run_scan_host(self, resume=False):
        """Helper Method:

        Executes the scan entirely on the host device.  The :code:`measure()` method of the scan must not have
        the @kernel decorator if this method is called or if :code:`self.run_on_core == False`
        Calls :code:`_loop()`

        :param resume: Set to True if the scan is being resumed after being paused and to False if the scan is being
                       started for the first time.
        """
        self._logger.debug("running scan on the host")
        self._loop(resume)

    # helper: for child class
    def simulate_measure(self, point):
        measurement=self.measurement
        for entry in self._model_registry:
            if entry['measurement'] and entry['measurement'] == measurement:
                model = entry['model']
                if hasattr(model,"models"):
                    ###if hasattr models this is a multiresult model and will loop through all models in that multiresult model
                    models=model.models
                else:
                    ###else normal model, just make this an array so the for loop below behaves and only loops for the singular model
                    models=[model]
                i=0
                for model in models:
                    if hasattr(model, '_simulation_args'):
                        simulation_args = model._simulation_args
                    else:
                        simulation_args = model.simulation_args
                    #if multiresult model model.simulate will loop through the array of simulation_args and set measure_results array with points,
                    #and return the first index to set _measure_results[0]. If normal model with only one result will simply ignore self._measure_results and return
                    #one vaule
                    self._measure_results[i]=model.simulate(point,self._measure_results, self.noise_level, simulation_args)
                    i+=1
        return None

    # -------------------- Callbacks --------------------

    # -- initialization callbacks

    # callback: for child class
    def prepare_scan(self):
        """User callback

        Runs during initialization after the scan points and warmup points have been loaded
        but before datasets have been initialized.

        Notes
            - Will be re-run when a scan is resumed after being paused.
            - Always runs on the host.
        """
        pass

    # callback: for child class
    def lab_prepare_scan(self):
        """User callback

        Runs on the host during initialization after the scan points and warmup points have been loaded
        but before datasets have been initialized.

        Meant to be implemented in a base class from which all of a lab's scans inherit.

        Notes
            - Runs after the :code:`prepare_scan()` callback.
            - Will be re-run when a scan is resumed after being paused.
            - Always runs on the host.

        :returns: None
        """
        pass

    # callback: for child class
    def before_scan(self):
        """User callback

        Run during initialization before datsets are initialized.

        Notes
            - always runs on the host
            - called after the 'prepare_scan' callback
        """
        pass

    # callback: for child class
    def before_analyze(self):
        """User callback

        Runs on the host before deciding if fits should be performed.

        Notes
            - Always runs on the host.
            - Will run even if fits have been disabled or performing a fit has not been selected in the GUI.
        """
        pass

    # callback reserved for child classes
    @portable
    def initialize_devices(self):
        """User callback

        Typically used to initialize devices on the core device before the scan loop begins.
        Runs after datasets have been initialized but before the scan loop begins.

        Notes
            - runs anytime _run_scan_core() or _run_scan_host() is called
            - runs on the host or the core device
            - called after the 'before_scan' callback
            - does not run if self.simulate_scan == True
        """
        pass

    @portable
    def _before_loop(self, resume):
        """Extension callback

        Called before the scan loop begins.
            - called after initialize_devices()
            - runs on the host or the core device
        """
        pass

    # callback: for child class
    @portable
    def before_pass(self, i_pass):
        """User callback

        Runs during the scan loop at the start of each pass.

        Notes
            - Does not run when the scan is resumed from being paused unless no scan points have yet executed.
            - Runs on the host or the core device.
        """
        pass

    # callback: for child class
    @portable
    def offset_point(self, i_point, point):
        """User callback

        Allows scan points to be dynamically modified in a scan.  The value returned by this method
        is used as the current scan point.  Runs before measurements are repeated at the current scan point.

        :param i_point: Index of the current scan point.
        :param point: Value of the scan point that will be executed next.
        :returns: Possibly modified value of the scan point that will be executed next.
        :rtype: Same datatype as a single scan point
        """
        return point

    # callback: for child class
    @portable
    def set_scan_point(self, i_point, point):
        """User callback

        Callback to set device parameter values (e.g. DDS frequencies) at the start of a scan point
        before the :code:`measure()` method is repeated self.nrepeats times at the current scan point.
        Runs during the scan loop at the start of each scan point.

        Notes
            - Runs on the host or the core device.
            - Runs before the 'before_measure' callback.
        """
        pass

    # callback: for child class
    @portable
    def before_measure(self, point, measurement):
        """User callback

        Runs at each repetition of a scan point immediately before the :code:`measure()` method is called.

        Notes
            - Runs on the host or the core device.
        """
        pass

    # callback: for child class
    @portable
    def lab_before_measure(self, point, measurement):
        """User callback

        Runs at each repetition of a scan point immediately before the :code:`measure()` method is called.

        Meant to be implemented in a base class from which all of a lab's scans inherit.

        Notes
            - Runs on the host or the core device.
        """
        pass

    # callback: for child class
    @portable
    def after_measure(self, point, measurement):
        """User callback

        Runs at each repetition of a scan point immediately after the :code:`measure()` method is called.

        Notes
            - Runs on the host or the core device.
        """
        pass

    # callback: for child class
    @portable
    def lab_after_measure(self, point, measurement):
        """User callback

        Runs at each repetition of a scan point immediately after the :code:`measure()` method is called.

        Meant to be implemented in a base class from which all of a lab's scans inherit.

        Notes
            - Runs on the host or the core device.
        """
        pass

    # callback: for child class
    def before_calculate(self, i_point, point, calculation):
        """User callback

        Runs during the scan loop after all data has been collected for a scan point but before calculations
        are performed.  Must return True for calculations to be performed.

        Notes
            - Always runs on the host.
            - Calculations will always run if this callback is not implemented.
            - Return False to skip calculations for the current scan point.
            - Return True to allow calculations to execute for the current scan point.
            - Runs before the :code:`after_scan_point()` callback

        :param i_point: Index of the current scan point.
        :param point: Value of the current scan point.
        :param calculation: Name of the calculation to perform.
        :returns: True: The calculation will be performed.  False: The calculation will not be performed.
        :rtype: Boolean
        """
        return True

    # callback: for child class
    @portable
    def after_scan_point(self, i_point, point):
        """User callback

        Runs during the scan loop after a scan point has completed.

        Notes
            - Run on host or core device.
            - Run after all data has been collected, datasets have been mutated, and 2 have run for
              a scan point.
            - Runs after the :code:`before_calculate()` callback.
        """
        pass

    # -- finalization & analysis callbacks

    # callback: for child class
    @portable
    def cleanup(self):
        """User callback

        This callback is meant to perform cleanup on the core device after a scan completes.  For
        example, resetting DDS frequencies or DAC values that have changed during the scan back to
        their appropriate default values.
        Called after the scan has completed and before data is fit.

        Notes
            - Runs on host or core device.
            - Called before the :code:`after_scan()` and the :code:`after_scan_core()` callbacks.
            - Always called before yielding to higher priority experiment.
            - This callback will still execute if an exception is thrown during the scan loop.
        """
        pass

    # callback: for child class
    @kernel
    def after_scan_core(self):
        """User callback

        Runs on the core device after the scan and any higher priority experiments have completed.

        Notes
            - Always runs on the core device.
            - Runs before data is fit.
            - This callback will not be called before yielding to higher priority experiment.
            - This callback will not be called if the scan is terminated.
        """
        pass

    # callback: for child class
    @kernel
    def lab_after_scan_core(self):
        """User callback

        Runs on the core device after the scan and any higher priority experiments have completed.

        Meant to be implemented in a base class from which all of a lab's scans inherit.

        Notes
            - Always runs on the core device.
            - Runs before data is fit.
            - This callback will not be called before yielding to higher priority experiment.
            - This callback will not be called if the scan is terminated.
        """
        pass

    # callback: for child class
    @kernel
    def lab_before_scan_core(self):
        """User callback

        Runs on the core device after datasets have been initialized but before the scan loop begins.

        Meant to be implemented in a base class from which all of a lab's scans inherit.
        """
        pass

    # callback: for child class
    def _after_scan(self):
        """Internal callback called after the scan and any higher priority experiments have completed.
            - always runs on the host
            - runs before data is fit
            - this callback will not be called before yielding to higher priority experiment
            - this callback will not be called if scan is terminated
        """
        return True

    # callback: for child class
    def after_scan(self):
        """User callback

        Runs on the host after the scan and any higher priority experiments have completed.

        Notes
            - Always runs on the host.
            - Runs before data is fit.
            - This callback will not be called before yielding to higher priority experiment.
            - This callback will not be called if scan is terminated.
        """
        pass

    def after_analyze(self):
        """User callback

        Runs on the host after the scan and any higher priority experiments have completed and after analysis
        (e.g. fitting) has been completed.

        Notes
            - always runs on the host
            - runs after data is fit
            - runs regardless of if the fit was successful
            - this callback will not be called before yielding to higher priority experiment
            - this callback will not be called if scan is terminated
        """
        pass

    def lab_after_analyze(self):
        """User callback

        Runs on the host after the scan and any higher priority experiments have completed and after analysis
        (e.g. fitting) has been completed.

        Meant to be implemented in a base class from which all of a lab's scans inherit.

        Notes
            - always runs on the host
            - runs after data is fit
            - runs regardless of if the fit was successful
            - this callback will not be called before yielding to higher priority experiment
            - this callback will not be called if scan is terminated
        """
        pass

    # callback: for child class
    def before_fit(self, model):
        """User callback

        Runs on the host before a fit is performed by a registered fit model.

        Notes
            - Always runs on the host.
            - Will not run if fitting has been disable or has not been selected in the GUI.

        :param model: Instance of the registered fit model.
        :type model: ScanModel
        :returns: False to prevent the fit from being performed.
        """
        pass

    # callback: for child class
    def after_fit(self, fit_name, valid, saved, model):
        """User callback

        Runs on the host after each registered fit model (i.e. all models registered with
        :code:`self.register_model(..., fit='<fit name'>`) has performed it's fit.

        Notes
            - :code:`model.fit` is used in this callback to access the
              :class:`Fit <scan_framework.analysis.curvefits.Fit>` object containing the fitted parameters and other
              useful information about the fit.
            - Always runs on the host.
            - Will not run if fit's are not performed for any reason

        :param fit_name: The name of the fit passed in on the :code:`fit` argument of :code:`register_model()`
        :param valid: False if any fit validation errors were raised during fitting.
        :param saved: True if the :code:`main_fit` fit parameter was saved to the model's top level namespace.
                      (a.k.a fits were saved)
        :param model: Instance of the registered fit model.
        :type model: ScanModel
        """
        pass

    # callback: for child class
    def report_fit(self, model):
        """User callback (has default behavior)

        If this method is not implemented :code:`model.report_fit()` will be called, which prints useful information
        about the fit (i.e. the fitted parameter values) to the Log window in the dashboard.

        Runs on the host after each registered fit model (i.e. all models registered with
        :code:`self.register_model(..., fit='<fit name'>`) has performed it's fit.

        Notes
            - Always runs on the host.
            - Will not run if fits are not performed for any reason.

        :param model: Instance of the registered fit model.
        :type model: ScanModel
        """
        model.report_fit()

    # callback: for child class
    def lab_after_scan(self):
        """User callback

        Runs on the host after the scan has completed, fits have been performed, and any higher priority experiments
        have completed.

        Meant to be implemented in a base class from which all of a lab's scans inherit.

        Notes
            - Always runs on the host.
            - Runs after data is fit.
            - This callback will not be called before yielding to higher priority experiment.
            - This callback will not be called if scan is terminated.
        """
        pass

    # -- callbacks for extensions

    # callback: for extensions
    def _scan_arguments(self):
        pass

    # callback: for extensions
    def _map_arguments(self):
        pass

    # callback: for extensions
    @portable
    def _after_scan_point(self, i_point, point, mean):
        """
        Scan extension callback executed during the scan loop after a scan point has completed.
            - executes on the core device
            - executes after all data has been collected, datasets have been mutated, calculations have been performed,
              and data has been analyzed.

        :param i_point: point index (integer for 1D scans, a list of two inetegers for 2D scans)
        :param point: the scan point (float for 1D scans, a list of two integers for 2D scans)
        :param mean: the mean number of counts collected at the scan point over all measurements.
        """
        pass

    # callback: for extensions
    @portable
    def _analyze_data(self, i_point, last_pass, last_point):
        pass


class Scan1D(Scan):
    """Extension of the :class:`~scan_framework.scans.scan.Scan` class for 1D scans.  All 1D scans should inherit from
    this class."""

    def __init__(self, managers_or_parent, *args, **kwargs):
        super().__init__(managers_or_parent, *args, **kwargs)
        self._dim = 1
        self._i_point = np.int64(0)

    def _load_points(self):
        # grab the points
        if self._points == None:
            points = list(self.get_scan_points())
        else:
            points = list(self._points)

        # warmup points
        if self._warmup_points == None:
            warmup_points = self.get_warmup_points()
        else:
            warmup_points = list(self._warmup_points)
        warmup_points = [p for p in warmup_points]

        # this turn's ARTIQ scan arguments into lists
        points = [p for p in points]

        # total number of scan points
        self.npoints = np.int32(len(points))
        self.nwarmup_points = np.int32(len(warmup_points))

        # initialize shapes (these are the authority on data structure sizes)...

        # shape of the stats.counts dataset
        self._shape = np.int32(self.npoints)

        # shape of the plots.x, plots.y, and plots.fitline datasets
        if self._plot_shape == None:
            self._plot_shape = np.int32(self.npoints)

        # initialize 1D data structures...

        # 1D array of scan points (these are saved to the stats.points dataset)
        self._points = np.array(points, dtype=np.float64)

        # flattened 1D array of scan points (these are looped over on the core)
        self._points_flat = np.array(points, dtype=np.float64)
        #edge case to help artiq compiler. Doesn't like looping through an empty array so always have a least warmup_points=[0], if nwarmup_points=0
        if self.nwarmup_points:
            self._warmup_points = np.array(warmup_points, dtype=np.float64)
        else:
            self._warmup_points = np.array([0],dtype=np.float64)


        # flattened 1D array of point indices as tuples
        # (these are used on the core to map the flat idx index to the 2D point index)
        self._i_points = np.array(range(self.npoints), dtype=np.int64)

    def _mutate_plot(self, entry, i_point, point, mean,error):
        model = entry['model']

        # mutate plot x/y datasets
        model.mutate_plot(i_point=i_point, x=point, y=mean,error=error)

        # tell the current_scan applet to redraw itself
        model.set('plots.trigger', 1, which='mirror')
        model.set('plots.trigger', 0, which='mirror')

    def _fit(self, entry, model, save, use_mirror, dimension, i):
        """Perform the fit"""

        #model = entry['model']
        x_data, y_data = model.get_fit_data(use_mirror)

        # for validation methods
        self.min_point = min(x_data)
        self.max_point = max(x_data)

        errors = model.stat_model.get('error', mirror=use_mirror)
        fit_function = model.fit_function

        guess = self._get_fit_guess(fit_function)

        return model.fit_data(
            x_data=x_data,
            y_data=y_data,
            errors=errors,
            fit_function=fit_function,
            guess=guess,
            validate=True,
            set=True,  # keep a record of the fit
            save=save,  # save the main fit to the root namespace?
            man_bounds=model.man_bounds,
            man_scale=model.man_scale
            )

    def _offset_points(self, x_offset):
        if x_offset != None:
            self._points += x_offset
            self._points_flat += x_offset

    def _write_datasets(self, entry):
        entry['model'].write_datasets(dimension=0)
        entry['datasets_written'] = True


class Scan2D(Scan):
    """Extension of the :class:`~scan_framework.scans.scan.Scan` class for 2D scans.  All 2D scans should inherit from
        this class. Beware that 2D scans have not thoroughly been tested, especially with new features as of version 3 of the scan_framework,
        namely continuous_scans and multiresult models have not been tested with 2D scans."""
    hold_plot = False

    def __init__(self, managers_or_parent, *args, **kwargs):
        super().__init__(managers_or_parent, *args, **kwargs)
        self._dim = 2
        self._i_point = np.array([0, 0], dtype=np.int64)

    # private: for scan.py
    def _load_points(self):
        # grab the points...
        if self._points == None:
            points = list(self.get_scan_points())
        else:
            points = list(self._points)

        # warmup points
        if self._warmup_points == None:
            warmup_points = self.get_warmup_points()
        else:
            warmup_points = list(self._warmup_points)
        warmup_points = [p for p in warmup_points]
        self.nwarmup_points = np.int32(len(warmup_points))
        #edge case to help artiq compiler. Doesn't like looping through an empty array so always have a least warmup_points=[0], if nwarmup_points=0
        if self.nwarmup_points:
            self._warmup_points = np.array(warmup_points, dtype=np.float64)
        else:
            self._warmup_points = np.array([0],dtype=np.float64)


        # this turn's ARTIQ scan arguments into lists
        points = [p for p in points[0]], [p for p in points[1]]

        # total number of scan points over both dimensions
        self.npoints = np.int32(len(points[0]) * len(points[1]))

        # initialize shapes (these are the authority on data structure sizes)...
        self._shape = np.array([len(points[0]), len(points[1])], dtype=np.int32)

        # shape of the current scan plot
        if self._plot_shape == None:
            self._plot_shape = np.array([self._shape[0], self._shape[1]], dtype=np.int32)

        # initialize 2D data structures...

        # 2D array of scan points (these are saved to the stats.points dataset)
        self._points = np.array([
            [[x1, x2] for x2 in points[1]] for x1 in points[0]
        ], dtype=np.float64)

        # flattened 1D array of scan points (these are looped over on the core)
        self._points_flat = np.array([
            [x1, x2] for x1 in points[0] for x2 in points[1]
        ], dtype=np.float64)

        # flattened 1D array of point indices as tuples
        # (these are used on the core to map the flat idx index to the 2D point index)
        self._i_points = np.array([
            (i1, i2) for i1 in range(self._shape[0]) for i2 in range(self._shape[1])
        ], dtype=np.int64)

    def _mutate_plot(self, entry, i_point, point, mean,error):
        """Mutates datasets for dimension 0 plots and dimension 1 plots"""
        if entry['dimension'] == 1:
            dim1_model = entry['model']
            dim1_scan_end = i_point[1] == self._shape[1] - 1
            dim1_scan_begin = i_point[1] == 0 and i_point[0] > 0
            dim1_model.set('plots.subplot.i_plot', i_point[0], which='mirror', broadcast=True, persist=True)

            # --- Beginning of dimension 1 scan ---
            #if dim1_scan_begin:
                #if not self.hold_plot:
                    # clear out plot data from previous dimension 1 plots
                #    dim1_model.init_plots(dimension=1)


            # --- Mutate Dimension 1 Plot ---

            # first store the point & mean to the dim1 plot x/y datasets
            # the value of the fitted parameter is plotted as the y value
            # at the current dimension-0 x value (i.e. x0)
            dim1_model.mutate_plot(i_point=i_point, x=point[1], y=mean, error=error, dim=1)



            # --- End of dimension 1 scan ---
            if dim1_scan_end:

                # --- Fit dimension 1 data ---
                # perform a fit over the dimension 1 data
                fit_performed = False
                try:
                    fit_performed, fit_valid, saved, errormsg = self._fit(entry,dim1_model,
                                                                              save=None,
                                                                              use_mirror=None,
                                                                              dimension=1,
                                                                              i=i_point[0])

                # handle cases when fit fails to converge so the scan doesn't just halt entirely with an
                # unhandeled error
                except RuntimeError:
                    fit_performed = False
                    fit_valid = False
                    saved = False
                    errormsg = 'Runtime Error'

                # fit went ok...
                if fit_performed:

                    # --- Plot Dimension 1 Fitline ---
                    # set the fitline to the dimension 1 plot dataset
                    dim1_model.mutate('plots.dim1.fitline', ((i_point[0], i_point[0]+1), (0, len(dim1_model.fit.fitline))), dim1_model.fit.fitline)

                    # --- Mutate Dimension 0 Plot ---

                    # get the name of the fitted parameter that will be plotted
                    param, error = self.calculate_dim0(dim1_model)

                    # find the dimension 0 model
                    for entry2 in self._model_registry:
                        if entry2['dimension'] == 0:
                            dim0_model = entry2['model']

                            # mutate the dimension 0 plot
                            dim0_model.mutate_plot(i_point=i_point, x=point[0], y=param, error=error, dim=0)

            # --- Redraw Plots ---
            # tell the current_scan applet to redraw itself
            dim1_model.set('plots.trigger', 1, which='mirror')
            dim1_model.set('plots.trigger', 0, which='mirror')

    def _fit(self, entry, model, save, use_mirror, dimension, i):
        """Performs fits on dimension 0 and dimension 1"""
        #model = entry['model']
        # dimension 1 fits
        if dimension == 1:
            # perform a fit on the completed dim1 plot and mutate the dim0 x/y datasets

            # get the x/y data for the fit on dimension 1
            x_data = model.stat_model.points[i, :, 1]  # these are unsorted
            y_data = model.stat_model.means[i, :]

            # use the errors in the dimension 1 mean values (std dev of mean) as the weights in the fit
            errors = model.stat_model.errors[i, :]

            # default fit arguments
            defaults = {
                'validate': True,
                'set': True,
                'save': False
            }
            guess = None

        # dimension 0 fits
        elif dimension == 0:
            # get the x/y data for the fit on dimension 0
            x_data, y_data, errors = model.get_plot_data(mirror=True)

            # default fit arguments
            defaults = {
                'validate': True,
                'set': True,
                'save': save
            }
            i = None
            guess = self._get_fit_guess(model.fit_function)

        # settings in 'entry' always override default values
        args = {**defaults, **entry}

        # perform the fit
        fit_function = model.fit_function
        validate = args['validate']
        set = args['set']  # save all info about the fit (fitted params, etc) to the 'fits' namespace?
        save = args['save']  # save the main fit to the root namespace?
        return model.fit_data(
            x_data=x_data,
            y_data=y_data,
            errors=errors,
            fit_function=fit_function,
            guess=guess,
            i=i,
            validate=validate,
            set=set,
            save=save,
            man_bounds=model.man_bounds,
            man_scale=model.man_scale
        )

    def _offset_points(self, offset):
        self._points[:, :, 1] += offset
        self._points_flat[:, 1] += offset

    def _write_datasets(self, entry):
        entry['model'].write_datasets(dimension=entry['dimension'])
        entry['datasets_written'] = True


# NOTE: MetaScan has been deprecated by Scan2D
class MetaScan(Scan1D):
    """Support for 2D scan of scan.  A top level scan is defined by inheriting from MetaScan.  That top level scan then
    executes a separate 1D scan that inherits from Scan1D."""
    scan_registry = {}  # dictionary containing instance of sub-scans that will be run by the top-level scan.

    def register_scan(self, scan, name=None, enable_pausing=False):
        """Register a sub scan.  By registering a scan, it's prepare(), _initialize_scan(), and prepare_scan() methods
        will automatically be called immediately before those methods are called on the top level scan.
        Scan's must be registered in the build method of the top level scan.
        :param scan: Instance of the scan to register
        :param name: Name of the scan to register, must be unique.
        :param enable_pausing: pausing/terminating sub-scans does not work with the current scan architecture,
        it is recommended to keep this set to False.  This will override the enable_pausing attribute of the passed
        in scan instance.
        """
        if name != None:
            if name in self.scan_registry:
                raise Exception("Cannot register the scan named '{0}' the name has already been used.  "
                                "You must pick a unique name to register this scan under.".format(name))
            scan.enable_pausing = enable_pausing
            self.scan_registry[name] = scan
            self.logger.debug('registered scan \'{0}\' of type \'{1}\''.format(name, scan.__class__.__name__))
        else:
            raise Exception("Cannot register scan.  The name argument is required.")

    # prepare sub scans
    def prepare(self):
        super().prepare()
        for name, s in self.scan_registry.items():
            self.logger.debug('calling \'{0}.prepare()\''.format(name))
            s.prepare()

    # sub scans are always initialized before top level scan
    def _initialize(self, resume):
        # initialize sub scans
        for name, s in self.scan_registry.items():
            self.logger.debug('calling \'{0}.initialize()\''.format(name))
            s._initialize(resume)

        # initialize top level scan
        super()._initialize(resume)

    # sub scans are always prepared before top level scan
    def prepare_scan(self):
        # prepare sub scans
        for name, s in self.scan_registry.items():
            self.logger.debug('calling \'{0}.prepare_scan()\''.format(name))
            s.prepare_scan()

        # prepare top level scan
        super().prepare_scan()
        
class ContinuousScan(HasEnvironment):
    def build(self,parent):
        self.parent=parent
    @portable
    def _loop(self,resume=False):
       parent = self.parent
       ncalcs = parent._ncalcs
       nmeasurements = parent.nmeasurements
       nrepeats = parent.nrepeats
       measurements = parent.measurements

       try:
           # callback
           parent._before_loop(resume)
           # callback
           parent.initialize_devices()
           
           poffset=0 #not used since there are no passes in continuous scan, just dummy variable
           while True:
               if not resume or parent._idx==0:
                   parent.before_pass(parent._i_pass)
               parent._repeat_loop(parent.continuous_index,parent.continuous_measure_point,parent._idx,nrepeats,nmeasurements,measurements,poffset,ncalcs)
               parent._idx+=1
               parent.continuous_index+=1
               #_idx is the index for accessing the points array, which gets overwritten after continuous_points scan points
               if parent._idx == parent.continuous_points:
                   #start overwritting scan points, keep track of number of points still in continuous_index however
                   parent._idx =0
                   if parent.continuous_save:
                       #save data to external hdf file after getting to end of index before overwriting it
                       #first_pass happens if number of points (continuous_index) is less than or equal to the size of the points array (continuous_points)
                       #need to know first pass to init the dataset in the external hdf file
                       first_pass=parent.continuous_points>=int(parent.continuous_index)
                       self.continuous_logging(parent,parent.continuous_logger,first_pass)
       except Paused:
           parent._paused = True
       finally:
           parent.cleanup()

    def _load_points(self):
        parent=self.parent
        # grab the points
        points = [i for i in range(parent.continuous_points)]

        # total number of scan points
        parent.npoints = np.int32(parent.continuous_points)

        # initialize shapes (these are the authority on data structure sizes)...

        # shape of the stats.counts dataset
        parent._shape = np.int32(parent.npoints)

        # shape of the plots.x, plots.y, and plots.fitline datasets
        if parent._plot_shape == None:
            parent._plot_shape = np.int32(parent.continuous_plot)

        # initialize 1D data structures...

        # 1D array of scan points (these are saved to the stats.points dataset)
        parent._points = np.array(points, dtype=np.float64)
        
        # flattened 1D array of scan points (these are looped over on the core)
        parent._points_flat = np.array(points, dtype=np.float64)
        
        parent.continuous_index=0.0

    def _mutate_plot(self, entry, i_point, point, mean,error):
        parent=self.parent
        model = entry['model']
        i_point = int(point % parent.continuous_plot)
        # mutate plot x/y datasets
        model.mutate_plot(i_point=i_point, x=point, y=mean,error=error)

        # tell the current_scan applet to redraw itself
        model.set('plots.trigger', 1, which='mirror')
        model.set('plots.trigger', 0, which='mirror')

    def _offset_points(self, x_offset):
        parent=self.parent
        if x_offset != None:
            parent.continuous_measure_point += x_offset
    @rpc(flags={"async"})
    def continuous_logging(self,parent,logger,first_pass):
        for entry in parent._model_registry:
            # look at every model, and if it's a measurement append it to external hdf dataset
            if entry['measurement']:
                model = entry['model']
                if hasattr(model,"models"):
                    ###if hasattr models this is a multiresult model and will loop through all models in that multiresult model
                    models=model.fit_models
                else:
                    ###else normal model, just make this an array so the for loop below behaves and only loops for the singular model
                    models=[model]
                for model in models:
                    # get counts for measurement of the measurement model
                    if parent._terminated:
                        # if terminated only append subset of counts corresponding to last taken points
                        counts = model.stat_model.counts[0:int(parent._idx)]
                    else:
                        counts = model.stat_model.counts
                        
                    name = model.stat_model.namespace +'.counts'
                    logger.append_continuous_data(counts, name, first_pass)
