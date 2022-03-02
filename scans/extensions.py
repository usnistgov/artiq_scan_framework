# Extensions to the base scan class which provide commonly used features.

from artiq.language.core import *
from .scan import *
from scan_framework.scans.loading_interface import *
from scipy.fftpack import fft


class TimeScan(Scan):
    """Scan class for scanning over time values."""

    def scan_arguments(self, times={}, npasses={}, nrepeats={}, nbins={}, fit_options={}, guesses=False):
        # assign default values for scan GUI arguments
        for k, v in {'start': 0, 'stop': 10 * us, 'npoints': 50, 'unit': 'us', 'scale': 1 * us, 'global_step': 10 * us,
                     'ndecimals': 3}.items():
            times.setdefault(k, v)

        # create core scan arguments
        super().scan_arguments(npasses=npasses, nrepeats=nrepeats, nbins=nbins, fit_options=fit_options, guesses=guesses)

        # create scan arguments for time scans
        self.setattr_argument('times', Scannable(
            default=RangeScan(
                start=times['start'],
                stop=times['stop'],
                npoints=times['npoints']
            ),
            unit=times['unit'],
            scale=times['scale'],
            global_step=times['global_step'],
            ndecimals=times['ndecimals']
        ), group='Scan Range')

    def get_scan_points(self):
        return self.times


class FreqScan(Scan):
    """Scan class for scanning over frequency values."""
    _freq_center_manual = None

    def scan_arguments(self, frequencies={}, npasses={}, nrepeats={}, nbins={}, fit_options={}, guesses=False):
        # assign default values for scan GUI arguments
        for k, v in {'start': -5*MHz, 'stop': 5*MHz, 'npoints': 50, 'unit': 'MHz', 'scale': 1 * MHz, 'ndecimals':4}.items():
            frequencies.setdefault(k, v)

        # crate core scan arguments
        super().scan_arguments(npasses=npasses,
                               nrepeats=nrepeats,
                               nbins=nbins,
                               fit_options=fit_options,
                               guesses=guesses)

        # create scan arguments for frequency scans
        group = 'Scan Range'
        self.setattr_argument('frequencies', Scannable(
            default=RangeScan(
                start=frequencies['start'],
                stop=frequencies['stop'],
                npoints=frequencies['npoints']
            ),
            unit=frequencies['unit'],
            scale=frequencies['scale'],
            ndecimals=frequencies['ndecimals']
        ), group=group)

    def get_scan_points(self):
        return self.frequencies


class TimeFreqScan(Scan):
    """Allows a scan experiment to scan over either a set of time values or a set of frequency values."""
    frequency_center = None  # default must be None so it can be overriden in the scan
    pulse_time = None  # default must be None so it can be overriden in the scan
    enable_auto_tracking = True

    def scan_arguments(self, times={}, frequencies={}, frequency_center={}, pulse_time={}, npasses={}, nrepeats={}, nbins={}, fit_options={}, guesses=False):
        # assign default values for scan GUI arguments
        for k,v in {'start': 0, 'stop': 10 * us, 'npoints': 50, 'unit': 'us', 'scale': 1 * us, 'global_step': 10 * us, 'ndecimals':3}.items():
            times.setdefault(k, v)
        for k, v in {'start': -5*MHz, 'stop': 5*MHz, 'npoints': 50, 'unit': 'MHz', 'scale': 1 * MHz, 'ndecimals':4}.items():
            frequencies.setdefault(k, v)
        for k, v in {'unit': 'MHz', 'scale': MHz, 'default': 100 * MHz, 'ndecimals': 4}.items():
            frequency_center.setdefault(k, v)
        for k, v in {'unit': 'us', 'scale': us, 'default': 100 * us, 'ndecimals': 4}.items():
            pulse_time.setdefault(k, v)

        # create GUI argument to select if scan is a time or a frequency scan
        self.setattr_argument('scan', EnumerationValue(['frequency', 'time'], default='frequency'))

        # create core scan arguments
        super().scan_arguments(npasses=npasses, nrepeats=nrepeats, nbins=nbins, fit_options=fit_options, guesses=guesses)

        # create remaining scan arguments for time and frequency scans
        if frequencies is not False:
            self.setattr_argument('frequencies', Scannable(
                default=RangeScan(
                    start=frequencies['start'],
                    stop=frequencies['stop'],
                    npoints=frequencies['npoints']
                ),
                unit=frequencies['unit'],
                scale=frequencies['scale'],
                ndecimals=frequencies['ndecimals']
            ), group='Scan Range')

        # auto tracking is disabled...
        # ask user for the frequency center
        if not self.enable_auto_tracking:
            if self.frequency_center is None:
                if frequency_center != False:
                    self.setattr_argument('frequency_center', NumberValue(**frequency_center), group='Scan Range')

            if self.pulse_time is None:
                if pulse_time != False:
                    self.setattr_argument('pulse_time', NumberValue(**pulse_time), group='Scan Range')
        self.setattr_argument('times', Scannable(
            default=RangeScan(
                start=times['start'],
                stop=times['stop'],
                npoints=times['npoints']
            ),
            unit=times['unit'],
            scale=times['scale'],
            global_step=times['global_step'],
            ndecimals=times['ndecimals']
        ), group='Scan Range')

    def _attach_models(self):
        self.__bind_models()
        if not self.fit_only:
            self.__load_frequency_center()

        # tell scan to offset x values by the frequency_center
        # this is done even when not auto-tracking in case the user has manually set frequency_center
        if self.scan == 'frequency' and self.frequency_center is not None:
            self._x_offset = self.frequency_center
            self._logger.debug("set _x_offset to frequency_center value of {0}".format(self.frequency_center))

    def __bind_models(self):
        # bind each registered model to the scan type (frequency or time)
        for entry in self._model_registry:
            # tell the model if this a frequency or time scan
            entry['model'].type = self.scan

            # bind model namespace to scan type
            if ('bind' in entry and entry['bind']) or (
                    self.enable_auto_tracking and 'auto_track' in entry and entry['auto_track']):
                entry['model'].bind()

    def __load_frequency_center(self):
        # frequency or pulse time manually set in the scan, state that in the debug logs
        if self.frequency_center is not None:
            self.logger.debug("frequency_center manually set to {0}".format(self.frequency_center))

        if self.pulse_time is not None:
            self.logger.debug("pulse_time manually set to {0}".format(self.pulse_time))

        # the frequency center is auto loaded from the fits by this class...
        if self.enable_auto_tracking:
            for entry in self._model_registry:
                model = entry['model']
                if 'auto_track' in entry and entry['auto_track']:

                    # fetch the last fitted frequency and time values from the datasets
                    fitted_freq, fitted_time = self._get_main_fits(model)

                    # hasn't been set yet, ok to auto load
                    if self.frequency_center is None:
                        # set frequency center from saved fit values
                        self.frequency_center = fitted_freq
                        self._logger.debug("auto set frequency_center to {0} from fits".format(fitted_freq))

                    # hasn't been set yet, ok to auto load
                    if self.pulse_time is None:
                        # set pulse time from saved fit values
                        self.pulse_time = fitted_time
                        self._logger.debug("auto set pulse_time to {0} from fits".format(fitted_time))

    def _get_main_fits(self, model):
        """Get's the last fitted frequency and time values"""

        if hasattr(model, 'type'):
            restore = model.type
        else:
            restore = None

        # get the last fitted frequency
        model.type = 'frequency'
        model.bind()
        freq = model.get_main_fit(archive=False)

        # get the last fitted time
        model.type = 'time'
        model.bind()
        time = model.get_main_fit(archive=False)

        # rebind the model to it's original namespace
        model.type = restore
        model.bind()

        return freq, time

    def get_scan_points(self):
        if self.scan == 'time':
            return self.times
        if self.scan == 'frequency':
            return self.frequencies

    @portable
    def do_measure(self, point):
        # time scan
        if self.scan == 'time':
            pulse_time = point
            return self.measure(pulse_time, self.frequency_center)

        # frequency scan
        if self.scan == 'frequency':
            return self.measure(self.pulse_time, point)
        return 0

    def report(self, location='both'):
        super().report(location)
        if location == 'bottom':
            self.logger.info("Type: %s scan" % self.scan)
            if self.scan == 'frequency':
                if self.frequency_center is not None:
                    self.logger.info('Frequency Center: %f MHz' % (self.frequency_center / MHz))
                if self.pulse_time is not None:
                    self.logger.info("Pulse Time: %f us" % (self.pulse_time / us))
            if self.scan == 'time':
                if self.frequency_center is not None:
                    self.logger.info('Frequency: %f MHz' % (self.frequency_center / MHz))


class ReloadingScan(Scan):
    """Allows detection of lost ion, pausing scan, reloading ion, and resuming scan"""

    # -- settings
    enable_reloading = True  #: Reload ion when it is lost?

    # -- scan state
    _lost_ion = False  #: ion has been lost

    # -- loading defaults
    loading_threshold = 1.0
    loading_pi_threshold = 5
    loading_timeout = 120 * s
    loading_windows = 2
    loading_repeats = 100

    # -- ion checking & loading
    measure_background = True
    perc_of_dark = 90  #: Percentage of dark rate at which background rate is set.
    perc_of_dark_second = 150  #: Percentage of dark rate at which ion present detection threshold is set.
    ion_windows = 2  #: Number of lost ion signals seen in data before a detection check is performed
    ion_threshold = 0.6  #: default value is always overwritten when background is measured
    ion_second_threshold = 2.0  # default value is always overwritten when background is measured
    ion_failures = 0
    check_for_ion = False
    lose_ion_at = -1

    # ====== Scan Interface Methods ======

    def _scan_arguments(self):
        if self.enable_reloading:
            self.setattr_argument("check_for_ion", BooleanValue(default=False), 'Reloading')
        #if self.enable_simulations:
        #    self.setattr_argument('lose_ion_at', NumberValue(default=-1, ndecimals=0, step=1), group='Simulation')

    def _map_arguments(self):
        """Map coarse grained attributes to fine grained options."""
        if not self.enable_reloading:
            self.check_for_ion = False
            self.measure_background = False
        if not self.check_for_ion:
            self.measure_background = False
        if self.simulate_scan:
            self.measure_background = False

    def _initialize(self, resume):
        super()._initialize(resume)
        self._lose_ion_at = self.lose_ion_at
        if self.enable_reloading and not hasattr(self, 'loading'):
            raise Exception(
                "An instance of the Loading subcomponent needs to be assigned to self.loading to use reloading.")
        if not hasattr(self, 'loading'):
            # hack so kernel methods can compile, artiq complains that there is no self.loading variable even though
            # the code is unreachable
            self.loading = LoadingInterface(self)

    def _report(self, location='both'):
        """Print details about the scan"""
        if location == 'both':
            self._logger.debug('enable_reloading is {0}'.format(self.enable_reloading))

    def _reset_state(self, resume):
        self._lost_ion = False
        self.ion_failures = 0

    @portable
    def _before_loop(self, resume):
        if self.simulate_scan:
            if resume:
                self._lose_ion_at = -1

        if self.measure_background and not resume:
            # check if ion is present before measuring background
            if self._check_ion_experiment(repeats=2):
                # measure the background
                self.logger.debug('> measuring background.')
                self._measure_ion_threshold()
            # no ion is present, can't measure background
            else:
                self.logger.warning("Can't measure background because no ion is present.")
                self._lost_ion = True
                self._schedule_load_ion()
                raise Paused
        else:
            self.logger.debug('Skipping background measurement.')

    @portable
    def _analyze_data(self, i_point, last_pass, last_point):
        # lost ion?
        if self.check_for_ion:
            # force a detection check on the very last scan point as data based checks can fail
            # to signal an ion lost at the end of a scan
            if last_pass and last_point:
                force_detection_check = True
            else:
                force_detection_check = False

            if not self._check_ion(i_point, force_detection_check=force_detection_check):
                # rewind to the scan point where the ion was first lost.
                self._rewind(num_points=self.ion_windows)

                # set state
                self._lost_ion = True

                # schedule ion reload
                self.logger.error("Lost ion.")
                self._schedule_load_ion()

                # break main loop in scan.py
                raise Paused

    def _state_string(self):
        return "lost_ion=%s" % self._lost_ion

    # ====== Local Methods ======
    def _schedule_load_ion(self):
        # try to load or wait if tried too many times

        # ion loading can't be performed for some reason
        if not self.loading.can_load():

            # schedule a high priority experiment (e.g. ion_monitor) that will pause this scan
            # until the issue can be fixed.
            self.logger.warning("Can't load ion, scheduling blocking experiment until issue is fixed.")
            self.loading.schedule_wait_experiment()
            self._yield()
            self._schedule_load_ion()
            return
        else:
            # schedule the load ion experiment
            self.logger.warning("Scheduling ion reload.")
            self.loading.schedule_load_ion(due_date=time(), synchronous=True)

    @kernel
    def _measure_ion_threshold(self):
        """Measure dark rate and  set self._ion_threshold to a percentage of the measured rate"""
        dark_rate = self.loading.measure_dark_rate()
        self.ion_threshold = (self.perc_of_dark / 100.0) * dark_rate
        self.ion_second_threshold = (self.perc_of_dark_second / 100.0) * dark_rate

        self.logger.debug("dark_rate measured at")
        self.logger.debug(dark_rate)
        self.logger.debug("ion_threshold set to")
        self.logger.debug(self.ion_threshold)
        self.logger.debug("ion_second_threshold set to")
        self.logger.debug(self.ion_second_threshold)

    @portable
    def _check_ion(self, i_point, force_detection_check=False):
        """Return true if ion is present"""
        if force_detection_check:
            do_detection_check = True

        # -- data based checks:
        # analyze data and signal for a detection based check after n successive failures
        else:
            do_detection_check = False
            for i_measurement in range(self.nmeasurements):
                if not self._check_ion_data(i_measurement, i_point):
                    self.ion_failures += 1
                    if self.ion_failures == self.ion_windows:
                        do_detection_check = True
                        break
                else:
                    self.ion_failures = 0

        # -- detection based check:
        # check for ion via detection
        if do_detection_check:
            self.logger.debug("")
            self.ion_failures = 0
            if self._check_ion_experiment():
                present = True
            else:
                present = False
        else:
            present = True
        return present

    @portable
    def _check_ion_data(self, i_measurement, i_point):
        """Return true if data collected indicates that the ion is still present"""
        #offset = self._data.address(pos=[i_measurement, i_point])
        #offset =
        #offset = offset + i_pass * self.nrepeats
        sum_ = 0.0
        for i in range(self.nrepeats):
            sum_ += self._data[self._idx][i_measurement][self.nrepeats*self._i_pass + i]
        mean = sum_ / self.nrepeats
        if mean >= self.ion_threshold:
            present = True
        else:
            present = False

        # lose ion at
        #if self.simulate_scan and not self._resuming:
        #    if i_pass * self.npoints + i_point >= self._lose_ion_at - 1:
        #        present = False
        return present

    @portable
    def _check_ion_experiment(self, repeats=1):
        """Return true if the loading.ion_present experiment indicates that the ion is still present"""
        #if self.simulate_scan:
        #    if i_pass * self.npoints + i_point == self._lose_ion_at:
        #        return False
        #    else:
        #        return True
        self.logger.debug(">>> calling loading.ion_present() with ion threshold set to ")
        self.logger.debug(self.ion_second_threshold)
        return self.loading.ion_present(repeats, threshold=self.ion_second_threshold)

class MultiResultScan(Scan1D):
    """Scan class for multiple results per measurement."""
    kernel_invariants = {'npasses', 'nbins', 'nrepeats', 'npoints', 'nmeasurements', 'nresults',
                         'do_fit', 'save_fit', 'fit_only','nresults_array','nmeasureresults'}
    nresults_array=[]
    nmeasureresults=0
    nresults=1
    _measure_results = [0]
    @portable
    def do_measure(self,point):
        self.measure(point,self._measure_results)
    def _init_storage(self):
        """initialize memory to record counts on core device"""
        #: 3D array of counts measured for a given scan point, i.e. nmeasurement*nrepeats*nresults
        self._data = np.zeros((self.nmeasurements,self.nresults, self.nrepeats),dtype=np.int32)
    def register_model(self, model_instance, measurement=None, fit=None, calculation=None,
                       init_datasets=True, nresults=1,**kwargs):
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
        if calculation is True:
            calculation = 'main'
        if measurement is True:
            measurement = 'main'
        if fit is True:
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
            'name': model_instance.__class__.__name__
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
            self.nresults=max(self.nresults_array)
            self._measure_results=[0 for _ in range(self.nresults)]
            self.nmeasureresults+=nresults
    # private: for scan.py
    @portable
    def _repeat_loop(self, point, measure_point, i_point, nrepeats, nmeasurements, measurements, poffset, ncalcs,
                     last_point=False, last_pass=False):

        # check for higher priority experiment or termination requested
        if self.enable_pausing:

            # cost: 3.6 ms
            check_pause = self.scheduler.check_pause()
            if check_pause:
                # yield
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
        
        # cost: 18 ms per point
        # mutate dataset values
        if self.enable_mutate:
            for i_measurement in range(nmeasurements):
                # get data for model, only send newly generated data array 0:nrepeats
                data = self._data[i_measurement][0:self.nresults_array[i_measurement]]
                
                # get the name of the measurement
                measurement = self.measurements[i_measurement]
                
                # rpc to host
                # send data to the model
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

        # rpc to host
        if self.enable_count_monitor:
            # cost: 2.7 ms
            self._set_counts(mean)      
          
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
                    if hasattr(model,"fit_models"):
                        ###if hasattr fit_models this is a multiresult model and will loop through all fit models in that multiresult model
                        models=model.fit_models
                    else:
                        ###else normal model, just make this an array so the for loop below behaves and only loops for the singular model
                        models=[model]
                    for model in models:
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
    def simulate_measure(self, point, measurement):
        for entry in self._model_registry:
            if entry['measurement'] and entry['measurement'] == measurement:
                model = entry['model']
                #model = self._model_registry['measurements'][measurement]['model']
                if hasattr(model, '_simulation_args'):
                    simulation_args = model._simulation_args
                else:
                    simulation_args = model.simulation_args
                # self._logger.debug('simulating measurement')
                # self._logger.debug('simulation_args = {0}'.format(simulation_args))
                model.simulate(point,self._measure_results, self.noise_level, simulation_args)
        return None