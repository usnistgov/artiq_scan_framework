from artiq_scan_framework.scans.scan import *
from artiq_scan_framework.snippets import *
import time
import importlib
from collections import OrderedDict


class BetaScan(Scan):
    kernel_invariants = {'nbins'}

    def load_component(self, name, *args, **kwargs):
        # create instance of component
        module = importlib.import_module('artiq_scan_framework.beta.components.{}'.format(name))
        class_name = ''.join(x.capitalize() for x in name.split('_'))
        class_ = getattr(module, class_name)
        instance = class_(self, self, *args, **kwargs)
        #self.components.append(instance)

    def build(self, **kwargs):
        self.print('BetaScan::build()', 2)
        self.__dict__.update(kwargs)
        self.setattr_device('scheduler')
        self.setattr_device("core")
        super().build(**kwargs)
        self.print('BetaScan::build()', -2)

    def scan_arguments(self, classes=[], init_only=False, **kwargs):
        if type(classes) != list:
            classes = [classes]
        self.print('BetaScan.scan_arguments(classes={}, init_only={}, kwargs={})'.format([c.__name__ for c in classes], init_only, kwargs), 2)

        if not hasattr(self, '_argdefs'):
            self._argdefs = []
        for c in classes:
            self._argdefs.append(c.argdef())

        if init_only:
            self.print('BetaScan.scan_arguments()', -2)
            return
        #print('self._argdefs')
        #pp.pprint(self._argdefs)

        # default scan arugments
        kwargs_default = OrderedDict()
        kwargs_default['nbins'] = {
                'processor': NumberValue,
                'processor_args': {'default': 50, 'ndecimals': 0, 'step': 1},
                'group': 'Scan Settings',
                'tooltip': None
            }
        kwargs_default['fit_options'] = {
                'processor': EnumerationValue,
                'processor_args': {
                    'choices': ['No Fits', 'Fit', "Fit and Save", "Fit Only", "Fit Only and Save"],
                    'default': 'Fit'
                },
                'group': "Fit Settings",
                'tooltip': None
            }
        kwargs_default['guesses'] = False
        for argdef in self._argdefs:
            kwargs_default.update(argdef)
        for k, v in kwargs.items():
            if k in kwargs_default:
                if v is False:
                    del(kwargs_default[k])
                else:
                    if type(v) == dict:
                        user_processor_args = {kk:v for kk,v in v.items() if kk not in ['group']}
                        kwargs_default[k]['processor_args'].update(user_processor_args)

                        user_defaults = {kk: v for kk, v in v.items() if kk in ['group']}
                        kwargs_default[k].update(user_defaults)
        kwargs = kwargs_default
        if self.enable_fitting and 'fit_options' in kwargs and kwargs['fit_options'] is not False:
            # fit_options = kwargs['fit_options']
            # fovals = fit_options.pop('values')
            # self.setattr_argument('fit_options', EnumerationValue(fovals, **fit_options), group='Fit Settings')
            # del kwargs['fit_options']
            guesses = kwargs['guesses']
            if guesses:
                if guesses is True:
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
            del(kwargs['guesses'])

        for key, argdef in kwargs_default.items():
            if key == 'fit_options' and not self.enable_fitting:
                continue
            if 'processor_args' not in argdef:
                processor_args = {}
            else:
                processor_args = argdef['processor_args'].copy()
            if 'condition' not in argdef or argdef['condition'](self):
                if 'default_args' in processor_args:
                    default = processor_args['default'](**processor_args['default_args'])
                else:
                    default = processor_args['default']
                del(processor_args['default'])
                setattr_argument(self, key=key, processor=argdef['processor'](default, **processor_args), group=argdef['group'], tooltip=argdef['tooltip'])
        self._scan_arguments(**kwargs)
        self.print('BetaScan.scan_arguments', -2)

    def setattr_argument(self, key, processor=None, group=None, show='auto', tooltip=None):
        if show is 'auto' and hasattr(self, key) and getattr(self, key) is not None:
            return
        if show is False or key in self._hide_arguments:
            if not key in self._hide_arguments:
                self._hide_arguments[key] = True
            return

        # fit guesses
        if isinstance(processor, FitGuess):
            if group is None:
                group = 'Fit Settings'
            super().setattr_argument(key, NumberValue(default=processor.default_value,
                                                      ndecimals=processor.ndecimals,
                                                      step=processor.step,
                                                      unit=processor.unit,
                                                      min=processor.min,
                                                      max=processor.max,
                                                      scale=processor.scale), group)
            use = None
            if processor.use is 'ask':
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
            #print('got here', key)
            super().setattr_argument(key, processor, group)

        # set attribute to default value when class is built but not submitted
        if hasattr(processor, 'default_value'):
            if not hasattr(self, key) or getattr(self, key) is None:
                setattr(self, key, processor.default_value)

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

    # disable printing
    #@portable
    #def print(self, msgs, level=0):
    #    pass

    @property
    def npoints(self):
        return self.looper.itr.npoints

    def _timeit(self, event, start):
        if not hasattr(self, '_profile_times'):
            self._profile_times = {}
        if start:
            self._profile_times[event] = {'start': time.time()}
        else:
            self._profile_times[event]['end'] = time.time()
            elapsed = self._profile_times[event]['end'] - self._profile_times[event]['start']
            self._profile_times[event]['elapsed'] = elapsed
            self._logger.warning('{} took {:0.2} sec'.format(event, elapsed))
    def run(self, resume=False):
        """Helper method
        Initializes the scan, executes the scan, yields to higher priority experiments,
        and performs fits on completion on the scan."""
        if self.enable_timing:
            self._timeit('run', True)
        self.print('**** Start Scan {} ****'.format(self.__class__.__name__))
        self.print('Scan::run(resume={})'.format(resume), 2)

        try:
            # start the profiler (if it's enabled)
            self._profile(start=True)

            # initialize the scan
            self._initialize(resume)
            self.print('scan initialized.  Iterator is ')
            self.print(self.looper.itr)

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
            self._analyze()

            self.after_analyze()
            self.lab_after_analyze()

            # callback
            self.lab_after_scan()

        finally:
            # stop the profiler (if it's enabled)
            self._profile(stop=True)
            self.print('Scan::run()', -2)
            if self.enable_timing:
                self._timeit('run', False)

    def _initialize(self, resume):
        """Initialize the scan"""
        self.print("Scan::_initialize(resume={})".format(resume), level=2)
        self._paused = False                            # initialize _paused state variable
        self.measurement = ""                           # initialize measurement state variable
        if not resume:
            self.looper.init('load_points')             # -- Load points
        self.prepare_scan()                             # Callback: user callback (self.npoints must be available)
        self.lab_prepare_scan()                         # Callback: user callback (self.npoints must be available)
        location ='top' if not resume else 'both'       # -- Report
        self.report(location=location)
        if not resume:                                  # -- Attach models, init storage, reset model states
            self._private_map_arguments()               # map gui arguments to class variables
            self._attach_models()                       # attach models to scan
            if not self.measurements:
                self.measurements = ['main']            # there must be at least one measurement
            self.looper.init('offset_points', self._x_offset)   # -- Offset points: self._x_offset must be set
            self._attach_to_models()                    # -- Attach scan to models
            # self._init_simulations()                  # initialize simulations (needs self._x_offset/self.frequency_center)
            self.report(location='bottom')              # display scan info
            self.reset_model_states()                   # reset model states
        self.before_scan()                              # Callback: user callback
                                                        # -- Initialize or write datasets
        if not self.fit_only:                           # datasets are only initialized/written when a scan can run
            for entry in self._model_registry:          # for every registered model...
                if not resume:                          # datasets are only initialized when the scan begins
                    if entry['init_datasets']:          # initialize datasets if requested by the user
                        self.looper.init('init_datasets', entry)
                        entry['datasets_initialized'] = True
                if resume:                              # datasets are only written when resuming a scan
                    self.looper.init('write_datasets', entry)         # restore data when resuming a scan by writing the model's
                    entry['datasets_written'] = True
                                                        # local variables to it's datasets
        if not (hasattr(self, 'scheduler')):            # we must have a scheduler
            raise NotImplementedError('The scan has no scheduler attribute.  Did you forget to call super().build()?')
        self.looper.init('init_loop',                             # -- Initialize looper --
            ncalcs=len(self.calculations),
            measurements=self.measurements
        )
        self.print("return: Scan::_initialize()", -2)

    def _yield(self):
        """Interface method  (optional)

        Yield to scheduled experiments with higher priority
        """
        try:
            #self.logger.warning("Yielding to higher priority experiment.")
            self.print('Scan::_yield()', 2)
            self.print(self.looper.itr)
            self.core.comm.close()
            self.scheduler.pause()

            # resume
            self.print('*** Resuming ***')
            self.print(self.looper.itr)
            self.logger.warning("Resuming")
            self.run(resume=True)

        except TerminationRequested:
            self.print('*** Terminated ***')
            self.logger.warning("Scan terminated.")
            self._terminated = True
            self.looper.terminate()
        finally:
            self.print('Scan::_yield()', -2)

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
            self.print("_run_scan_core()", 2)
            self.print('on core device')

            # callback: lab_before_scan_core
            #self.print('lab_before_scan_core()', 2)
            self.lab_before_scan_core()
            #self.print('lab_before_scan_core()', -2)

            # for comp in self.components:
            #     comp.before_loop(resume)

            # callback: initialize_devices
            #self.print('call initialize_devices()', 2)
            self.initialize_devices()
            #self.print('initialize_devices()', -2)

            # main loop
            self.print('call loop()', 2)
            self.looper.loop(
                resume=resume
            )
            self.print('loop()', -2)
        except Paused:
            self.print('loop()', -2)
            self.print('caught Paused exception')
            self._paused = True
        finally:

            self.print('cleanup()', 2)
            self.cleanup()
            self.print('cleanup()', -2)

        # callback: after_scan_core
        #self.print('after_scan_core()', 2)
        self.after_scan_core()
        #self.print('after_scan_core()', -2)

        # callback: lab_after_scan_core
        #self.print('lab_after_scan_core()', 2)
        self.lab_after_scan_core()
        #self.print('lab_after_scan_core()', -2)

        self.print("return: _run_scan_core()", -2)

    def _run_scan_host(self, resume=False):
        """Helper Method:

        Executes the scan entirely on the host device.  The :code:`measure()` method of the scan must not have
        the @kernel decorator if this method is called or if :code:`self.run_on_core == False`
        Calls :code:`_loop()`

        :param resume: Set to True if the scan is being resumed after being paused and to False if the scan is being
                       started for the first time.
        """
        try:
            self.print("_run_scan_host()", 2)
            self.print('on host device')

            # for comp in self.components:
            #     comp.before_loop(resume)

            # main loop
            self.print('call loop()', 2)
            self.looper.loop(
                resume=resume
            )
            self.print('loop()', -2)
        except Paused:
            self.print('loop()', -2)
            self.print('caught Paused exception')
            self._paused = True

        self.print("return: _run_scan_host()", -2)

    @portable
    def _rewind(self, num_points):
        return self.looper.itr.rewind(num_points)

    # interface: for child class
    def report(self, location='both'):
        if self.enable_reporting:
            self.looper.init('report', location)
            if location == 'bottom' or location == 'both':
                self._report()

    @portable
    def _analyze_data(self, i_point, itr, data):
        pass

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
            #so that it can still be retrieved using normal get_datset methods before the experiment has completed.

            # for every registered model...
            for entry in self._model_registry:
                # registered fit models
                if entry['fit']:
                    model = entry['model']

                    # callback
                    if self.before_fit(model) is not False:

                        # what's the correct data source?
                        #   When fitting only (no scan is performed) the fit is performed on data from the last
                        #   scan that ran, which is assumed to be in the 'current_scan' namespace.
                        #   Otherwise, the fit is performed on data in the model's namespace.
                        use_mirror = model.mirror is True and self.fit_only
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
                            self.logger.warning("Fitted params not saved.")

                        # callback
                        self._main_fit_saved = main_fit_saved
                        self._fit_valid = valid
                        if fit_performed:
                            self.after_fit(entry['fit'], valid, main_fit_saved, model)

                    # print the fitted parameters...
                    if self.enable_reporting and fit_performed:
                        self.report_fit(model)


