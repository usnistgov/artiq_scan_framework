from artiq_scan_framework.scans import *
from artiq_scan_framework.models import *
from artiq_scan_framework.scans.looper.continuous_loop import ContinuousLooper



class ContinuousScan(Scan1D, EnvExperiment):
    """Continuous scan using composition over inheritance"""

    def build(self):
        self.print_level = 0
        self.debug = True
        self.setattr_device("core")
        self.setattr_device('scheduler')
        self.scan_arguments()
        self.looper = ContinuousLooper(self,
                                       parent=self,
                                       nrepeats=self.nrepeats,
                                       continuous_points=self.continuous_points,
                                       continuous_plot=self.continuous_plot,
                                       continuous_measure_point=self.continuous_measure_point,
                                       continuous_save=self.continuous_save
                                       )

    def prepare(self):
        self.model = ScanModel(self, namespace='beta')
        self.register_model(self.model, measurement=True, fit=True, bind=True)

    def get_scan_points(self):
        return [i for i in range(10)]

    @kernel
    def initialize_devices(self):
        self.core.reset()

    @kernel
    def measure(self, point):
        return 0

    # ------- framework overrides (for now) -----------

    def print(self, msg, level=0):
        if level < 0:
            self.print_level += level
        s = ""
        for l in range(self.print_level):
            s += " "
        if level > 0:
            s += ">> "
        if level < 0:
            s += "<< "
        print(s + msg)
        if level > 0:
            self.print_level += level

    def __init__(self, managers_or_parent, *args, **kwargs):
        if self._name is None:
            self._name = self.__class__.__name__
        if self._logger_name is None:
            self._logger_name = ''
        self.create_logger()

        # initialize variables

        ###nresults version
        # self._measure_results = []
        # self.nresults = 1 #Number of results to return per measurement
        # self.result_names=None
        # self.nresults = None

        self.dtype = np.int32
        self.nmeasurements = 0
        #self.npoints = None
        # self.npasses = 1  #: Number of passes
        self.npasses = None
        # self.nbins = 50  #: Number of histogram bins
        self.nbins = None
        # self.nrepeats = 1  #: Number of repeats
        self.nrepeats = None
        self._x_offset = None
        self.debug = 0

        self.continuous_scan = None

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
        self.min_point = None
        self.max_point = None
        self.tick = None
        self._warmup_points = []
        self.warming_up = False

        # this stores "flat" idx point index when a scan is paused.  the idx index is then restored from
        # this variable when the scan resumes.
        self._idx = np.int32(0)
        self._i_pass = np.int32(0)
        self._i_measurement = np.int32(0)

        super().__init__(managers_or_parent, *args, **kwargs)

    @property
    def npoints(self):
        return self.looper.npoints

    def _mutate_plot(self, entry, i_point, data, mean, error=None):
        return self.looper.mutate_plot(entry, i_point, data, mean, error)

    # def run(self, resume=False):
    #     """Helper method
    #
    #     Initializes the scan, executes the scan, yields to higher priority experiments,
    #     and performs fits on completion on the scan."""
    #     self.print_level = 0
    #     self.print("call: run()", 2)
    #     try:
    #         # start the profiler (if it's enabled)
    #         self._profile(start=True)
    #
    #         # initialize the scan
    #         self._initialize(resume)
    #
    #         # run the scan
    #         if not self.fit_only:
    #             if resume:
    #                 self._logger.debug(
    #                     'resuming scan at (i_pass, i_point) = ({0}, {1})'.format(self._i_pass, self._i_point))
    #             else:
    #                 self._logger.debug(
    #                     'starting scan at (i_pass, i_point) = ({0}, {1})'.format(self._i_pass, self._i_point))
    #             if self.run_on_core:
    #                 if self.enable_timing:
    #                     self._profile_times = {
    #                         'before_compile': time()
    #                     }
    #                 self._logger.debug("compiling core scan...")
    #                 self._run_scan_core(resume)
    #                 self.print('back on host')
    #             else:
    #                 self._run_scan_host(resume)
    #             self._logger.debug("scan completed")
    #
    #             # yield to other experiments
    #             self.print('checking if self._paused == True')
    #             if self._paused:
    #                 self.print('self._paused is True')
    #                 self._yield()  # self.run(resume=True) is called after other experiments finish and this scan resumes
    #                 return
    #
    #         # callback
    #         self._logger.debug("executing _after_scan callback")
    #         if not self._after_scan():
    #             return
    #
    #         # callback
    #         self._logger.debug("executing after_scan callback")
    #         self.after_scan()
    #
    #         # perform fits
    #         self._logger.debug("executing _analyze")
    #         self._analyze()
    #
    #         self.after_analyze()
    #         self.lab_after_analyze()
    #
    #         # callback
    #         self._logger.debug("executing lab_after_scan callback")
    #         self.lab_after_scan()
    #
    #     finally:
    #         # stop the profiler (if it's enabled)
    #         self._profile(stop=True)
    #
    #     self.print("return: run()", -2)


    def _yield(self):
        """Interface method  (optional)

        Yield to scheduled experiments with higher priority
        """
        try:
            #self.logger.warning("Yielding to higher priority experiment.")
            self.core.comm.close()
            self.scheduler.pause()

            # resume
            self.logger.warning("Resuming")
            self.run(resume=True)

        except TerminationRequested:
            self.logger.warning("Scan terminated.")
            self._terminated = True
            self.looper.terminate()

    def _initialize(self, resume):
        """Initialize the scan"""
        self._logger.debug("_initialize()")

        ###nresults version
        # if self.nresults is not None and self.result_names is None:
        #    self.result_names = ["result_{0}".format(i) for i in range(self.nresults)]

        # initialize state variables
        self._paused = False
        self.measurement = ""

        # callback
        self._logger.debug("executing prepare_scan callback")

        if not resume:
            #self.continuous_logger = None
            # if self.continuous_scan:
            #     self._continuous_scan_obj = ContinuousScan(self, self)
            #     # Set _load_points,_loop,_mutate_plot, _offset_points to be continuous versions
            #     self._load_points = self._continuous_scan_obj._load_points
            #     self._loop = self._continuous_scan_obj._loop
            #     self._mutate_plot = self._continuous_scan_obj._mutate_plot
            #     self._offset_points = self._continuous_scan_obj._offset_points
            #     if self.continuous_save:
            #         self.continuous_logger = DataLogger(self)
            #     else:
            #         self.continuous_logger = None
            ###nresults version
            # self._measure_results = [0 for _ in range(self.nresults)]

            # load scan points
            self.looper.load_points()
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
            self._private_map_arguments()

            self._attach_models()

            # there must be at least one measurement
            if not self.measurements:
                self.measurements = ['main']
            self.nmeasurements = len(self.measurements)

            # expects self._x_offset has been set
            self.looper.offset_points(self._x_offset)
            self._logger.debug("offset points by {0}".format(self._x_offset))

            # initialize storage
            self._init_storage()

            # attach scan to models (expects self.npoints has been set)
            self._attach_to_models()

            # initialize simulations (needs self._x_offset/self.frequency_center)
            # self._init_simulations()

            # display scan info
            if self.enable_reporting:
                self.report(location='bottom')

            # reset model states
            self.reset_model_states()

        # callback
        self._logger.debug("executing before_scan callback")
        self.before_scan()

        # -- Initialize Datasets

        # these have been deprecated
        # init_local = not (self.fit_only or resume)
        # write_datasets = resume
        # write_done = []

        shape = self.looper.shape
        plot_shape = self.looper.plot_shape

        # datasets are only initialized/written when a scan can run
        if not self.fit_only:

            # for every registered model...
            for entry in self._model_registry:
                # each type (e.g. rsb, bsb, etc)
                # for type, entry in entries.items():

                # datasets are only initialized when the scan begins
                if not resume:
                    # initialize datasets if requested by the users
                    if entry['init_datasets']:
                        # initialize the model's datasets
                        entry['datasets_initialized'] = True
                        self.print('call: {}::init_datasets(shape={}, plot_shape={}, points={}, dimension={})'.format(
                            entry['model'].__class__.__name__,
                            shape,
                            plot_shape,
                            self.looper.points,
                            entry['dimension']
                        ), 2)
                        entry['model'].init_datasets(
                            shape,
                            plot_shape,
                            self.looper.points,
                            dimension=entry['dimension']
                        )
                        self.print('return: {}::init_datasets'.format(entry['model'].__class__.__name__), -2)

                        # debug logging
                        self._logger.debug("initialized datasets of model '{0}' {1}".format(entry['name'], entry))

                        # # run once
                        # if entry['name'] in done:
                        #     entry['datasets_initialized'] = True
                        # else:
                        #     entry['model'].init_datasets(shape, plot_shape, points, dimension=entry['dimension'])
                        #
                        #     # mark done
                        #     done.append(entry['name'])
                        #     entry['datasets_initialized'] = True

                # datasets are only written when resuming a scan
                if resume:
                    # restore data when resuming a scan by writing the model's local variables to it's datasets
                    self._write_datasets(entry)

                    # debug logging
                    self._logger.debug("wrote datasets of model '{0}' {1}".format(entry['model'], entry))

        self._ncalcs = len(self.calculations)

        if not (hasattr(self, 'scheduler')):
            raise NotImplementedError('The scan has no scheduler attribute.  Did you forget to call super().build()?')


        # initialize looper
        self.looper.initialize(self.nmeasurements, self.nrepeats)

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
        self._logger.debug("running scan on core device")
        self.lab_before_scan_core()

        self.after_scan_core()
        self.lab_after_scan_core()

    @kernel
    def _run_scan_core(self, resume=False):
        """Helper Method:

        Executes the scan on the core device.
        Calls :code:`lab_before_scan_core()`, then :code:`_loop()`, followed by :code:`after_scan_core()` and
        :code:`lab_after_scan_core()`

        :param resume: Set to True if the scan is being resumed after being paused and to False if the scan is being
                       started for the first time.
        """
        try:
            self.print("call: _run_scan_core()", 2)
            self.print('on core device')

            # measure compilation time
            if self.enable_timing:
                self._timeit('compile')
            self._logger.debug("running scan on core device")

            # callback: lab_before_scan_core
            self.print('call: lab_before_scan_core()', 2)
            self.lab_before_scan_core()
            self.print('return: after_after_core()', -2)

            # callback: _before_loop
            self.print('call _before_loop()', 2)
            self._before_loop(resume)
            self.print('return: _before_loop()', -2)

            # callback: initialize_devices
            self.print('call initialize_devices()', 2)
            self.initialize_devices()
            self.print('return: initialize_devices()', -2)

            # main loop
            self.print('call loop()', 2)
            self.looper.loop(
                ncalcs=self._ncalcs,
                nmeasurements=self.nmeasurements,
                nrepeats=self.nrepeats,
                measurements=self.measurements,
                resume=resume
            )
            self.print('return: loop()', -2)
        except Paused:
            self.print('return: loop()', -2)
            self.print('caught Paused exception')
            self._paused = True
        finally:

            self.print('call: cleanup()', 2)
            self.cleanup()
            self.print('return: cleanup()', -2)

        # callback: after_scan_core
        self.print('call: after_scan_core()', 2)
        self.after_scan_core()
        self.print('return: after_scan_core()', -2)

        # callback: lab_after_scan_core
        self.print('call: lab_after_scan_core()', 2)
        self.lab_after_scan_core()
        self.print('return: lab_after_scan_core()', -2)

        self.print("return: _run_scan_core()", -2)

    @portable
    def _rewind(self, num_points):
        """Rewind the cursor from the current pass and point indices by the specified number of points.  The cursor can
          be rewound into a previous pass.  The cursor cannot be rewound past the first point of the first pass.

          :param num_points: The current cursor will be moved to this number of scan points before its current value.
        """
        return self.looper.rewind(num_points)

    # interface: for child class
    def report(self, location='both'):
        """Interface method (optional, has default behavior)

        Logs details about the scan to the log window.
        Runs during initialization after the scan points and warmup points have been loaded but before datasets
        have been initialized.
        """
        self.looper.report(location)
        if location == 'bottom' or location == 'both':
            self._report()




