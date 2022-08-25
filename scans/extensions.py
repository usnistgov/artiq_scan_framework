# Extensions to the base scan class which provide commonly used features.

from artiq.language.core import *
from .scan import *
from .loading_interface import *
from ..lib.ion_checker import *
from ..exceptions import *


class TimeScan(Scan):
    """Scan class for scanning over time values."""

    def scan_arguments(self, times={}, npasses={}, nrepeats={}, nbins={}, fit_options={}, guesses=False, **kwargs):
        # assign default values for scan GUI arguments
        if times is not False:
            for k, v in {'start': 0, 'stop': 10 * us, 'npoints': 50, 'unit': 'us', 'scale': 1 * us, 'global_step': 10 * us,
                         'ndecimals': 3}.items():
                times.setdefault(k, v)

        # create core scan arguments
        super().scan_arguments(npasses=npasses, nrepeats=nrepeats, nbins=nbins, fit_options=fit_options, guesses=guesses, **kwargs)

        # create scan arguments for time scans
        if times is not False:
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

    def scan_arguments(self, frequencies={}, npasses={}, nrepeats={}, nbins={}, fit_options={}, guesses=False, **kwargs):
        # assign default values for scan GUI arguments
        if frequencies is not False:
            for k, v in {'start': -5*MHz, 'stop': 5*MHz, 'npoints': 50, 'unit': 'MHz', 'scale': 1 * MHz, 'ndecimals':4}.items():
                frequencies.setdefault(k, v)

        # crate core scan arguments
        super().scan_arguments(npasses=npasses,
                               nrepeats=nrepeats,
                               nbins=nbins,
                               fit_options=fit_options,
                               guesses=guesses, **kwargs)

        # create scan arguments for frequency scans
        if frequencies is not False:
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

    def scan_arguments(self, times={}, frequencies={}, frequency_center={}, pulse_time={}, npasses={}, nrepeats={}, nbins={}, fit_options={}, guesses=False, scan={}, **kwargs):
        # assign default values for scan GUI arguments
        if times is not False:
            for k,v in {'start': 0, 'stop': 10 * us, 'npoints': 50, 'unit': 'us', 'scale': 1 * us, 'global_step': 10 * us, 'ndecimals':3}.items():
                times.setdefault(k, v)
        if frequencies is not False:
            for k, v in {'start': -5*MHz, 'stop': 5*MHz, 'npoints': 50, 'unit': 'MHz', 'scale': 1 * MHz, 'ndecimals':4}.items():
                frequencies.setdefault(k, v)
        if frequency_center is not False:
            for k, v in {'unit': 'MHz', 'scale': MHz, 'default': 100 * MHz, 'ndecimals': 4}.items():
                frequency_center.setdefault(k, v)
        if pulse_time is not False:
            for k, v in {'unit': 'us', 'scale': us, 'default': 100 * us, 'ndecimals': 4}.items():
                pulse_time.setdefault(k, v)
        if scan is not False:
            for k, v in {'default': 'frequency', 'group': 'Scan Range'}.items():
                scan.setdefault(k, v)

        # create core scan arguments
        super().scan_arguments(npasses=npasses, nrepeats=nrepeats, nbins=nbins, fit_options=fit_options, guesses=guesses, **kwargs)

        # create GUI argument to select if scan is a time or a frequency scan
        if scan is not False:
            group = scan['group']
            del scan['group']
            self.setattr_argument('scan', EnumerationValue(['frequency', 'time'], **scan), group)


        # create remaining scan arguments for time and frequency scans
        if frequencies != False:
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
            if self.frequency_center == None:
                if frequency_center != False:
                    self.setattr_argument('frequency_center', NumberValue(**frequency_center), group='Scan Range')

            if self.pulse_time == None:
                if pulse_time != False:
                    self.setattr_argument('pulse_time', NumberValue(**pulse_time), group='Scan Range')
        if times is not False:
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
            self._load_frequency_center()

        # tell scan to offset x values by the frequency_center
        # this is done even when not auto-tracking in case the user has manually set frequency_center
        if self.scan == 'frequency' and self.frequency_center != None:
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

    def _load_frequency_center(self):
        # frequency or pulse time manually set in the scan, state that in the debug logs
        if self.frequency_center != None:
            self._logger.warn("frequency_center manually set to {0}".format(self.frequency_center))

        if self.pulse_time != None:
            self._logger.warn("pulse_time manually set to {0}".format(self.pulse_time))

        # the frequency center is auto loaded from the fits by this class...
        if self.enable_auto_tracking:
            for entry in self._model_registry:
                model = entry['model']
                if 'auto_track' in entry and entry['auto_track']:

                    # fetch the last fitted frequency and time values from the datasets
                    fitted_freq, fitted_time = self._get_main_fits(model)

                    # hasn't been set yet, ok to auto load
                    if self.frequency_center == None:
                        # set frequency center from saved fit values
                        self.frequency_center = fitted_freq
                        self._logger.warn("auto set frequency_center to {0} from fits".format(fitted_freq))

                    # hasn't been set yet, ok to auto load
                    if self.pulse_time == None:
                        # set pulse time from saved fit values
                        self.pulse_time = fitted_time
                        self._logger.warn("auto set pulse_time to {0} from fits".format(fitted_time))

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
            self._measure_results[0]= self.measure(pulse_time, self.frequency_center)

        # frequency scan
        if self.scan == 'frequency':
            self._measure_results[0]= self.measure(self.pulse_time, point)
    @portable
    def do_measure_nresults(self,point):
        # time scan
        if self.scan == 'time':
            pulse_time = point
            #multiresult model used in this scan, fill your results into the _measure_results list passed in the third argument of self.measure
            self.measure(pulse_time, self.frequency_center,self._measure_results)

        # frequency scan
        if self.scan == 'frequency':
            #multiresult model used in this scan, fill your results into the _measure_results list passed in the third argument of self.measure
            self.measure(self.pulse_time, point,self._measure_results)

    def report(self, location='both'):
        super().report(location)
        if location == 'bottom':
            self.logger.info("Type: %s scan" % self.scan)
            if self.scan == 'frequency':
                if self.frequency_center != None:
                    self.logger.info('Frequency Center: %f MHz' % (self.frequency_center / MHz))
                if self.pulse_time != None:
                    self.logger.info("Pulse Time: %f us" % (self.pulse_time / us))
            if self.scan == 'time':
                if self.frequency_center != None:
                    self.logger.info('Frequency: %f MHz' % (self.frequency_center / MHz))


class ReloadingScan(Scan):
    """Allows detection of lost ion, pausing scan, reloading ion, and resuming scan"""

    # -- settings
    enable_reloading = True  #: Set to False to disable all features of this extension.  Set to True to enable lost ion checking and automated reloading.

    # -- loading defaults
    loading_threshold = 1.0
    loading_pi_threshold = 5
    loading_timeout = 120 * s
    loading_windows = 2
    loading_repeats = 100

    # ====== Scan Interface Methods ======

    def _scan_arguments(self, check_for_ion={'default': True}):
        if self.enable_reloading:
            if check_for_ion is not False:
                for k, v in {'default': False, 'group': 'Ion Checker'}.items():
                    check_for_ion.setdefault(k, v)
                group = check_for_ion['group']
                del check_for_ion['group']
                self.setattr_argument("check_for_ion", BooleanValue(**check_for_ion), group)
            
    def _map_arguments(self):
        """Map coarse grained attributes to fine grained options."""
        if self.enable_reloading:
            if not self.check_for_ion:
                self.measure_thresholds = False
        else:
            self.check_for_ion = False
            self.measure_thresholds = False

    def _initialize(self, resume):
        super()._initialize(resume)
        if self.enable_reloading and not hasattr(self, 'loading'):
            raise Exception(
                "An instance of the Loading subcomponent needs to be assigned to self.loading to use reloading.")
        if not hasattr(self, 'loading'):
            # hack so kernel methods can compile, artiq complains that there is no self.loading variable even though
            # the code is unreachable
            self.loading = LoadingInterface(self)
            
        if self.enable_reloading and not hasattr(self, 'ion_checker'):
            raise Exception(
                "An instance of an IonChecker subcomponent needs to be assigned to self.ion_checker to use reloading.")
        if not hasattr(self, 'loading'):
            # hack so kernel methods can compile, artiq complains that there is no self.ion_checker variable even though
            # the code is unreachable
            self.ion_checker = IonChecker(self, logger=self.logger, loading=self.loading)

    @portable
    def _before_loop(self, resume):
        try:
            self.ion_checker.initialze(resume)
        except LoadIon:
            self._schedule_load_ion()
            raise Paused

    @portable
    def _analyze_data(self, i_point, last_pass, last_point):
        
        if self.check_for_ion:
            try:
                # iterate over scan points in the same order as is done in scan.py
                for i_measurement in range(self.nmeasurements):
                    self.ion_checker.ion_present(self._data[i_measurement], self.nrepeats, last_point=(last_pass and last_point)) 
            except LostIon:
                # rewind to the earliest scan point where the ion could have been lost.
                self._rewind(num_points=self.ion_checker.rewind_num_points)

                # Schedule an experiment to load an ion.
                self.logger.error("Ion lost, reloading...")
                self._schedule_load_ion()

                # break main loop in scan.py
                raise Paused
            except IonPresent:
                pass

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
            self.loading.schedule_load_ion(due_date=time.time(), synchronous=True)
