from artiq_scan_framework.scans.scan import *
import importlib


class BetaScan(Scan):

    def load_component(self, name, *args, **kwargs):
        # create instance of component
        module = importlib.import_module('artiq_scan_framework.beta.components.{}'.format(name))
        class_name = ''.join(x.capitalize() for x in name.split('_'))
        class_ = getattr(module, class_name)
        instance = class_(self, self, *args, **kwargs)
        self.components.append(instance)

    def build(self):
        self.components = []
        self.setattr_device("core")
        self.setattr_device('scheduler')
        self.scan_arguments()

    def print(self, msg, level=0):
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

    @property
    def npoints(self):
        return self.looper.itr.npoints

    def _initialize(self, resume):
        """Initialize the scan"""
        self.print("call: _initialize()", 2)
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
            self.nmeasurements = len(self.measurements)
            self.looper.init('offset_points', self._x_offset)   # -- Offset points: self._x_offset must be set
            self._init_storage()                        # -- Init storage
            self._attach_to_models()                    # -- Attach scan to models
            # self._init_simulations()                  # initialize simulations (needs self._x_offset/self.frequency_center)
            self.report(location='bottom')              # display scan info
            self.reset_model_states()                   # reset model states
        self.before_scan()                              # Callback: user callback
                                                        # -- Init datasets
        if not self.fit_only:                           # datasets are only initialized/written when a scan can run
            for entry in self._model_registry:          # for every registered model...
                if not resume:                          # datasets are only initialized when the scan begins
                    if entry['init_datasets']:          # initialize datasets if requested by the user
                        self.looper.init('init_datasets',
                            model=entry['model'],
                            dimension=entry['dimension']
                        )
                        entry['datasets_initialized'] = True
                if resume:                              # datasets are only written when resuming a scan
                    self.looper.write_datasets(**entry)         # restore data when resuming a scan by writing the model's
                    entry['datasets_written'] = True
                                                        # local variables to it's datasets
        if not (hasattr(self, 'scheduler')):            # we must have a scheduler
            raise NotImplementedError('The scan has no scheduler attribute.  Did you forget to call super().build()?')
        self.looper.init('init',                             # -- Initialize looper --
            nmeasurements=self.nmeasurements,
            ncalcs=len(self.calculations),
            measurements=self.measurements
        )
        self.print("return: _initialize()", -2)

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

            # callback: lab_before_scan_core
            self.print('call: lab_before_scan_core()', 2)
            self.lab_before_scan_core()
            self.print('return: after_after_core()', -2)

            for comp in self.components:
                comp.before_loop(resume)

            # callback: initialize_devices
            self.print('call initialize_devices()', 2)
            self.initialize_devices()
            self.print('return: initialize_devices()', -2)

            # main loop
            self.print('call loop()', 2)
            self.looper.loop(
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

    def _run_scan_host(self, resume=False):
        """Helper Method:

        Executes the scan entirely on the host device.  The :code:`measure()` method of the scan must not have
        the @kernel decorator if this method is called or if :code:`self.run_on_core == False`
        Calls :code:`_loop()`

        :param resume: Set to True if the scan is being resumed after being paused and to False if the scan is being
                       started for the first time.
        """
        try:
            self.print("call: _run_scan_host()", 2)
            self.print('on host device')

            for comp in self.components:
                comp.before_loop(resume)

            # main loop
            self.print('call loop()', 2)
            self.looper.loop(
                resume=resume
            )
            self.print('return: loop()', -2)
        except Paused:
            self.print('return: loop()', -2)
            self.print('caught Paused exception')
            self._paused = True

        self.print("return: _run_scan_host()", -2)

    @portable
    def _rewind(self, num_points):
        return self.looper.rewind(num_points)

    # interface: for child class
    def report(self, location='both'):
        if self.enable_reporting:
            self.looper.init('report', location)
            if location == 'bottom' or location == 'both':
                self._report()

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
                        self._logger.debug('performing fit on model \'{0}\''.format(entry['name']))
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


