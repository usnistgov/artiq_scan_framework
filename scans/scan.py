from artiq.experiment import *
import numpy as np
import time
import cProfile, pstats
from ..language import *
from collections import OrderedDict
from ..components.fit_arguments import FitArguments
import traceback


# allows @portable methods that use delay_mu to compile
def delay_mu(duration):
    pass


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

    ###nresults version
    #kernel_invariants = {'npasses', 'nbins', 'nrepeats', 'npoints', 'nmeasurements', 'nresults',
    #                     'do_fit', 'save_fit', 'fit_only','nresults_array','nmeasureresults'
    kernel_invariants = {'nbins'}

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
    _hide_arguments = {}

    # ------------------- Private Methods ---------------------
    def __init__(self, managers_or_parent, *args, **kwargs):
        if self._name == None:
            self._name = self.__class__.__name__
        if self._logger_name == None:
             self._logger_name = ''
        self.create_logger()

        # components
        self.fit_arguments = FitArguments()

        # initialize variables

        ###nresults version

        #self._measure_results = []
        #self.nresults = 1 #Number of results to return per measurement
        #self.result_names=None
        #self.nresults = None

        self.dtype = np.int32
        self._measure_results = np.array([0], dtype=self.dtype) #array of measure results sized by default to 1, otherwise sized to the maximum number of results for any measurement.
        self.nresults = 1 # maximum number of results for any measurement, default to 1
        #self.result_names=None

        self.nmeasurements = 0
        #self.npoints = 0
        #self.npasses = 1  #: Number of passes

        #multiresult models use the below initializations
        self.nresults_array=np.array([], dtype=np.int32) #list of number of results for each measurement
        self.nmeasureresults=0 #total number of measurement results (sum of above list)
        #self.nresults=1 #maximum number of results for any measurement, default to 1

        # --- \start Bryce's original changes for reference
        #multiresult models use the below initializations
        #self.nresults_array=[] #list of number of results for each measurement
        #self.nmeasureresults=0 #total number of measurement results (sum of above list)
        #self.nresults=1 #maximum number of results for any measurement, default to 1
        #self._measure_results = [0] #array of measure results sized by default to 1, otherwise sized to the maximum number of results for any measurement.

        #self.nmeasurements = 0
        #self.npoints = 0
        # --- \end Bryce's changes

        # PK 01/13/2023 temporary monkey patch for new looper component
        try:
            #self.npoints = None
            self.npasses = None
            self.nrepeats = None
        except AttributeError:
            pass

        self.nbins = None
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
        self._error = False  #: an error occured during the scan
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
        self.scan_points = None
        self.warmup_points = None
        self.warming_up = False
        self._check_pause = False

        # this stores "flat" idx point index when a scan is paused.  the idx index is then restored from
        # this variable when the scan resumes.
        self._idx = np.int64(0)
        self._i_pass = np.int64(0)
        self._i_measurement = np.int64(0)

        super().__init__(managers_or_parent, *args, **kwargs)

    # interface: for child class (optional)
    def build(self, **kwargs):
        """ Interface method (optional, has default behavior)

                Creates the :code:`scheduler` and :code:`core` devices and sets them to the attributes
                :code:`self.scheduler` and :code:`self.core` respectively.
                :param kwargs: Optional dictionary of class attributes when using the scan as a sub-component (i.e. the
                               scan does not inherit from :code:`EnvExperiment`).  Each entry will be set as an attribute of the scan.
                """
        self.__dict__.update(kwargs)
        self.setattr_device('scheduler')
        self.setattr_device("core")
        super().build()

    # helper: for child class (optional)
    def run(self, resume=False):
        """Helper method
        Initializes the scan, executes the scan, yields to higher priority experiments,
        and performs fits on completion on the scan."""
        if self.enable_timing:
            self._timeit('run', True)

        try:
            # start the profiler (if it's enabled)
            self._profile(start=True)

            # initialize the scan
            self._initialize(resume)

            # run the scan
            if not self.fit_only:
                if self.run_on_core:
                    if self.enable_timing:
                        self._timeit('compile', True)
                    self._run_scan_core(resume)
                else:
                    self._run_scan_host(resume)

                # yield to other experiments
                if self._paused:
                    self._yield()  # self.run(resume=True) is called after other experiments finish and this scan resumes
                    return

            # callback
            if not self._after_scan():
                return

            # callback
            self.after_scan()

            # perform fits
            if self._error:
                self.logger.warning('Warning: The _analyze() method was not called by the scan framework because of a prior error that occurred in the run() method.')
                self.logger.warning("         This means that fits were not performed for this scan.")
            elif self._analyzed:
                self.logger.warning('Warning: The _analyze() method was not called by the scan framework because it has already been called.')
                self.logger.warning("         This means that fits might not have been performed for this scan.")
            elif self._terminated:
                self.logger.warning('Warning: The _analyze() method was not called by the scan framework because the scan was terminated.')
                self.logger.warning("         This means that fits were not performed for this scan.")
            else:
                self._analyze()

            self.after_analyze()
            self.lab_after_analyze()

            # callback
            self.lab_after_scan()
        except Exception as e:
            self._error = True
            self.logger.error("An error occurred in the run() method provided by the scan framework.")
            self.logger.error(traceback.format_exc())
        finally:
            # stop the profiler (if it's enabled)
            self._profile(stop=True)
            if self.enable_timing:
                self._timeit('run', False)
        # callback with default behavior: for child class

    # Phil's version (Bryce's nresults changes have been merged into this method)
    # private: for scan.py
    def _initialize(self, resume):
        """Initialize the scan"""
        # Warn user that they need to call self.scan_arguments()
        if not resume and self.nrepeats == None:
            self.logger.error("Unable to execute scan.  Number of repeats is unknown.  Did you forget to call self.scan_arguments() in build?")
        self._logger.debug("_initialize()")

        # initialize state variables
        self._paused = False
        self.measurement = ""

        # callback
        self._logger.debug("executing prepare_scan callback")
        if not resume:
            # \begin removed by Phil for custom loops
            ###This is run first call of _initialize (resume=False), override and initialize anything needed at start of experiment
            #if self.continuous_scan:
            #    self._init_continuous()
            # \end removed by Phil for custom loops

            # \begin added by Bryce for nresults
            #Check if nresults is greater than one, resize the _measure_results array to account for the maximum number of results for any individual measurement
            if self.nresults_array:
                self.nresults=max(self.nresults_array)
            else:
                self.nresults_array = np.array([1], dtype=np.int32)
                self.nmeasureresults = 1
            if self.nresults>1:
                self._measure_results=[0 for _ in range(self.nresults)]
                #Override the do_measure function to call measure(point,results) to give a results list (_measure_results) to output results
                self.do_measure=self.do_measure_nresults
            #check simulation, if true set run_on_host true and overwrite do_measure with simulate_measure
            if self.simulate_scan:
                self.run_on_core=False
                self.do_measure=self.simulate_measure
            #\end added by Bryce for nresults

            # \begin added by Phil for custom loops
            # load scan points
            self.looper.itr.reset()
            self.looper.init('load_points')  # -- Load points
            # \begin added by Phil for custom loops
            self._logger.debug('loaded points')

        self.prepare_scan()  # Callback: user callback (self.npoints must be available)
        self.lab_prepare_scan()  # Callback: user callback (self.npoints must be available)
        location = 'top' if not resume else 'both'  # -- Report
        self.report(location=location)
        if not resume:  # -- Attach models, init storage, reset model states
            self._private_map_arguments()  # map gui arguments to class variables

            for i, entry in enumerate(self._model_registry):  # -- Attach scan to models
                model = entry['model']
                model.attach()
                self._logger.debug("attached scan to model '{0}'".format(entry['name']))

            self._attach_models()  # -- Attach models to scan
            if not self.measurements:
                self.measurements = ['main']  # there must be at least one measurement
            self.looper.init('offset_points', self._x_offset)  # -- Offset points: self._x_offset must be set

            # self._init_simulations()                  # initialize simulations (needs self._x_offset/self.frequency_center)
            if self.simulate_scan:
                self._init_simulations()
            self.report(location='bottom')  # display scan info
            self.reset_model_states()  # reset model states
        self.before_scan()  # Callback: user callback
        # -- Initialize or write datasets
        if not self.fit_only:  # datasets are only initialized/written when a scan can run
            for entry in self._model_registry:  # for every registered model...
                if not resume:  # datasets are only initialized when the scan begins
                    if entry['init_datasets']:  # initialize datasets if requested by the user
                        self.looper.init('init_datasets', entry)
                        entry['datasets_initialized'] = True
                if resume:  # datasets are only written when resuming a scan
                    self.looper.init('write_datasets', entry)  # restore data when resuming a scan by writing the model's
                    entry['datasets_written'] = True
                    # local variables to it's datasets
        if not (hasattr(self, 'scheduler')):  # we must have a scheduler
            raise NotImplementedError('The scan has no scheduler attribute.  Did you forget to call super().build()?')
        self.looper.init('init_loop',  # -- Initialize looper --
                         ncalcs=len(self.calculations),
                         measurements=self.measurements
                         )

    @staticmethod
    def argdef(kwargs):
        argdef = OrderedDict()
        argdef['nbins'] = {
            'processor': NumberValue,
            'processor_args': {'default': 50, 'ndecimals': 0, 'step': 1},
            'group': 'Scan Settings',
            'tooltip': None
        }
        argdef['fit_options'] = {
            'processor': EnumerationValue,
            'processor_args': {
                'choices': ['No Fits', 'Fit', "Fit and Save", "Fit Only", "Fit Only and Save"],
                'default': 'Fit'
            },
            'group': "Fit Settings",
            'tooltip': None,
            'condition': lambda scan, kwargs: scan.enable_fitting
        }
        # fit guesses
        # fit_options = kwargs['fit_options']
        # fovals = fit_options.pop('values')
        # self.setattr_argument('fit_options', EnumerationValue(fovals, **fit_options), group='Fit Settings')
        # del kwargs['fit_options']

        if 'guesses' in kwargs:
            if kwargs['guesses'] == True:
                for i in range(1, 6):
                    argdef['fit_guess_{0}'.format(i)] = {
                        'processor': FitGuess,
                        'processor_args': {
                            'default': 1.0,
                            'use_default': False,
                            'ndecimals': 6,
                            'step': 0.001,
                            'fit_param': None,
                            'param_index': i
                        },
                        'condition': lambda scan, kwargs: scan.enable_fitting and kwargs['guesses'] and (
                                'fit_options' not in kwargs or kwargs['fit_options'] != False)
                    }
            else:
                for fit_param in kwargs['guesses']:
                    argdef['fit_guess_{0}'.format(fit_param)] = {
                        'processor': FitGuess,
                        'processor_args': {
                            'default': 1.0,
                            'use_default': False,
                            'ndecimals': 1,
                            'step': 0.001,
                            'fit_param': fit_param,
                            'param_index': None
                        },
                        'condition': lambda scan, kwargs: scan.enable_fitting and kwargs['guesses'] and (
                                'fit_options' not in kwargs or kwargs['fit_options'] != False)
                    }
        return argdef

    def setattr_argument(self, key, processor=None, group=None, show='auto', tooltip=None, scan_points=None, warmup_points=None):
        if show is 'auto' and hasattr(self, key) and getattr(self, key) != None:
            return
        if show == False or key in self._hide_arguments:
            if not key in self._hide_arguments:
                self._hide_arguments[key] = True
            return
        if not self.fit_arguments.setattr_argument(self, key, processor, group, show, tooltip):
            super().setattr_argument(key, processor, group)

        # set attribute to default value when class is built but not submitted
        if hasattr(processor, 'default_value'):
            if not hasattr(self, key) or getattr(self, key) is None:
                setattr(self, key, processor.default_value)

        if scan_points is not None:
            if type(scan_points) is bool:
                self.scan_points = getattr(self, key)
            else:
                if self.scan_points is None:
                    self.scan_points = {}
                self.scan_points[scan_points] = getattr(self, key)

        if warmup_points is not None:
            if type(warmup_points) is bool:
                self.warmup_points = getattr(self, key)
            else:
                if self.warmup_points is None:
                    self.warmup_points = {}
                self.warmup_points[warmup_points] = getattr(self, key)

    # helper: for child class
    def scan_arguments(self, classes=[], init_only=False, **kwargs):
        if type(classes) != list:
            classes = [classes]

        # collect argdefs from other classes; i.e. loops, extensions, etc.
        if not hasattr(self, '_argdefs'):
            self._argdefs = []
        for c in classes:
            self._argdefs.append(c.argdef())

        # early exit; only initing self._argdefs, not actually creating the arguments
        if init_only:
            return

        # full list of argdefs from all classes
        argdefs = Scan.argdef(kwargs)
        for d in self._argdefs:
            argdefs.update(d)

        # user overrides, specified as keyword arguments to scan_arguments()
        for k, v in kwargs.items():
            if k in argdefs:
                # user doesn't want to show this argument
                if v == False:
                    del (argdefs[k])
                else:
                    # user has overridden the default options for the argument
                    if type(v) == dict:
                        for uk, uv in v.items():
                            # overrides of the processor options
                            if uk in argdefs[k]['processor_args']:
                                argdefs[k]['processor_args'][uk] = uv
                            # overrides of the argument options
                            if uk in argdefs[k]:
                                argdefs[k][uk] = uv
                            # overrides of the default arguments
                            if 'default_args' in argdefs[k]:
                                if uk in argdefs[k]['default_args']:
                                    argdefs[k]['default_args'][uk] = uv

        # create the GUI arguments and set them as attributes of the scan
        for key, argdef in argdefs.items():
            if 'condition' not in argdef or argdef['condition'](self, kwargs):
                if 'processor_args' not in argdef:
                    argdef['processor_args'] = {}
                if 'default_args' in argdef:
                    argdef['processor_args']['default'] = argdef['processor_args']['default'](**argdef['default_args'])
                    del (argdef['default_args'])
                setattr_argument(self,
                                 key=key,
                                 processor=argdef['processor'](**argdef['processor_args']),
                                 group=argdef['group'] if 'group' in argdef else None,
                                 tooltip=argdef['tooltip'] if 'tooltip' in argdef else None)
        self._scan_arguments(**kwargs)

    # helper: for child class
    def register_model(self, model_instance, measurement=None, fit=None, calculation=None,
                       init_datasets=True, nresults=1, **kwargs):
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
        :type model_instance: :class:`artiq_scan_framework.models.scan_model.ScanModel`
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
        entry['model']._scan = self
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
            self.nresults_array = np.array(np.append(self.nresults_array, nresults), dtype=np.int32)
            self.nmeasureresults+=nresults
    @property
    def npoints(self):
        return self.looper.itr.npoints

    @npoints.setter
    def npoints(self, val):
        self.looper.iter.npoints = val

    def print(self, msgs, level=0):
        if type(msgs) != str:
            msgs = str(msgs)
        msgs = msgs.split("\n")
        for msg in msgs:
            if not hasattr(self, 'print_level'):
                self.print_level = 0
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

    def load_component(self, name, *args, **kwargs):
        # create instance of component
        module = importlib.import_module('artiq_scan_framework.beta.components.{}'.format(name))
        class_name = ''.join(x.capitalize() for x in name.split('_'))
        class_ = getattr(module, class_name)
        instance = class_(self, self, *args, **kwargs)
        self.components.append(instance)

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
                    #p.strip_dirs()
                    p.sort_stats('time')
                    p.print_stats(10)
                    p.sort_stats('cumulative')
                    p.print_stats(20)

    # private: for scan.py
    def _private_map_arguments(self):
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

    def _attach_models(self):
        """Attach a single model to the scan"""
        # load x_offset
        if self._x_offset is None:  # offset has not been manually set by the user
            # automatic determination of x_offset
            if self.enable_auto_tracking:
                for entry in self._model_registry:
                    model = entry['model']
                    if 'auto_track' in entry and entry['auto_track']:
                        # use the last performed fit
                        if entry['auto_track'] == 'fitresults' and hasattr(model, 'fit'):
                            self._x_offset = model.fit.fitresults[model.main_fit]
                            self.logger.warning('offset x by {} (from fit results)'.format(self._x_offset))
                            return
                        # use dataset value
                        elif entry['auto_track'] == 'fit' or entry['auto_track'] == True:
                            self._x_offset = model.get_main_fit(archive=False)
                            self.logger.warning('offset x by {} (from fits)'.format(self._x_offset))
                            return

            # default to no offset if none of the above cases apply
            self._x_offset = 0.0

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
    # def _init_model_datasets(self, shape, plot_shape, points, x, y, init_local, write_datasets):
    #     """Set the contents and handling modes of all datasets in the scan."""

    # RPC
    # private: for scan.py

    def _timeit(self, event, start):
        if not hasattr(self, '_profile_times'):
            self._profile_times = {}
        if start:
            self._profile_times[event] = {'start': time.time()}
        else:
            self._profile_times[event]['end'] = time.time()
            elapsed = self._profile_times[event]['end'] - self._profile_times[event]['start']
            self._profile_times[event]['elapsed'] = elapsed
            self._logger.warning('It took {:0.2f} seconds to {}.'.format(elapsed, event))

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
            # measure compilation time
            if self.enable_timing:
                self._timeit('compile', False)
            # callback: lab_before_scan_core
            self.lab_before_scan_core()
            self._before_loop(resume)
            # callback: initialize_devices
            self.initialize_devices()
            # main loop
            self.looper.loop(
                resume=resume
            )
        except Paused:
            self._paused = True
        finally:
            self.cleanup()
        # callback: after_scan_core
        self.after_scan_core()
        # callback: lab_after_scan_core
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
        try:
            # main loop
            self.looper.loop(
                resume=resume
            )
        except Paused:
            self._paused = True

    # private: for scan.py
    def _calculate(self, i_point, i_pass, point, calculation, entry):
        """Perform calculations on collected data after each scan point"""
        model = entry['model']
        ###nresults version possibly
        # for i_result in range(self.nresults):
        #     value = model.mutate_datasets_calc(i_point, point, calculation)
        #     if 'mutate_plot' in entry and entry['mutate_plot']:
        #         self._mutate_plot(entry, i_point, point, value)
        value = model.mutate_datasets_calc(i_point, i_pass, point, calculation)
        if 'mutate_plot' in entry and entry['mutate_plot']:
            self._mutate_plot(entry, i_point, point, value)

    @portable
    def run_warmup(self, warmup_points, nmeasurements, measurements):
        self.warming_up = True
        for wupoint in warmup_points:
            for i_measurement in range(nmeasurements):
                self.measurement = measurements[i_measurement]
                self.warmup(wupoint)
        self.warming_up = False

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
        self._logger = logging.getLogger("")

    # interface: for child class
    def report(self, location='both'):
        if self.enable_reporting:
            self.looper.init('report', location)
            if location == 'bottom' or location == 'both':
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
    # @rpc(flags={"async"})
    # def mutate_datasets(self, i_point, i_pass, poffset, measurement, point, data):
    #     """Interface method  (optional, has default behavior)
    #
    #     If this method is not overridden, all data collected for the specified measurement during the
    #     current scan point is passed to any model that has been registered for the given measurement.
    #     The :code:`mutate_datasets()` and :code:`_mutate_plot()` methods of these models will be called with :code:`data`
    #     passed as an argument. Thus, the registered models will calculate means and standard errors and plot these
    #     statistics to the current scan applet for the current scan point.
    #
    #     Typically, the default implementation of this method is used, though it can be overridden in user scans
    #     to manually perform statistic calculation and plotting of measurement data at the end of each scan point.
    #
    #     Notes
    #         - Always runs on the host device.
    #
    #     :param i_point: Index of the current scan point.
    #     :param measurement: Name of the current measurement (For multiple measurements).
    #     :param point: Value of the current scan point.
    #     :param data: List of integers containing the values returned by :code:`measure()` at each repetition of the current scan point.
    #     """
    #     self.measurement = measurement
    #
    #     for entry in self._model_registry:
    #         # model registered for this measurement
    #         if entry['measurement'] and entry['measurement'] == measurement:
    #             # grab the model for the measurement from the registry
    #             # if measurement in self._model_registry['measurements']:
    #             #    entry = self._model_registry['measurements'][measurement]
    #
    #             # mutate the stats for this measurement with the data passed from the core device
    #             mean, error = entry['model'].mutate_datasets(i_point, i_pass, poffset, point, data)
    #             self._mutate_plot(entry, i_point, point, mean, error)
    #

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
            # self.logger.warning("Yielding to higher priority experiment.")
            self.core.comm.close()
            self.scheduler.pause()

            # resume
            self.logger.warning("Resuming")
            self.run(resume=True)

        except TerminationRequested:
            self.logger.warning("Scan terminated.")
            self._terminated = True
            self.looper.terminate()
        finally:
            pass

    # interface: for child class (optional)
    # RPC

    # interface: for child class (optional)
    @rpc(flags={"async"})
    def _calculate_all(self, i_point, i_pass, point):
        # for every registered calculation....
        for calculation in self.calculations:
            for entry in self._model_registry:
                # models that are registered for the calculation...
                if entry['calculation'] and entry['calculation'] == calculation:
                    # perform the calculation
                    if self.before_calculate(i_point, point, calculation):
                        self._calculate(i_point, i_pass, point, calculation, entry)

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

            # Perform a fit for each registered fit model and save the fitted params to datasets.
            #
            # If self.save_fit is true, the main fit is broadcast to the ARTIQ master,
            # persisted and saved.  If self.save_fit == False, the main fit is not broadcasted or persisted but is saved
            # so that it can still be retrieved using normal get_datset methods before the experiment has completed.

            # for every registered model...
            for entry in self._model_registry:
                # registered fit models
                if entry['fit']:
                    model = entry['model']
                    if hasattr(model, "fit_models"):
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
                            fit_performed, valid, main_fit_saved, errormsg = self.looper.fit(entry, save, use_mirror, dimension, i)

                            entry['fit_valid'] = valid

                            # tell current scan to plot data...
                            model.set('plots.trigger', 1, which='mirror')
                            model.set('plots.trigger', 0, which='mirror')

                            # params not saved warning occurred
                            if save and not main_fit_saved:
                                self.logger.warning("Main fit param was not saved.")

                            # print the fitted parameters...
                            if self.enable_reporting and fit_performed:
                                self.report_fit(model)

                            # callback
                            self._main_fit_saved = main_fit_saved
                            self._fit_valid = valid
                            if fit_performed:
                                self.after_fit(entry['fit'], valid, main_fit_saved, model)

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

    def _mutate_plot(self, entry, i_point, data, mean, error=None):
        raise NotImplementedError()

    # interface: for extensions (required)
    def calculate_dim0(self, dim1_model):
        """User callback (runs on host).

        Returns a value and its error from the dimension 1 sub-scan.  The returned value will be plotted
        as  the y-value in the dimension 0 plot and the returned error will weight the final fit along dimension 0.

        :param model: The model which just performed a fit along the dimension 1 sub-scan.  :code:`model.fit` points to
                      the :class:`Fit <artiq_scan_framework.analysis.curvefits.Fit>` object from the
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
        self._measure_results[0] = self.measure(point)

    @portable
    def do_measure_nresults(self, point):
        """Provides a way for subclasses to override the method signature of the measure method. You MUST return the result of the measuerment into 
        the self._measure_results array. If you only have one value to return, do _measure_results[0]=self.measure(point). If you have multiple results for
        a single measurement, iterate through the array for each result, while only calling measure once, ideally passing _measure_results as an array to modify"""
        #multiresult model used in this scan, fill your results into the _measure_results list passed in the second argument of self.measure
        self.measure(point,self._measure_results)

    # helper method: for scan.py or child class

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
              :class:`Fit <artiq_scan_framework.analysis.curvefits.Fit>` object containing the fitted parameters and other
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
    def _scan_arguments(self, *args, **kwargs):
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
    def _analyze_data(self, i_point, itr, data):
        pass