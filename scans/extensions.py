# -*- coding: utf8 -*-
#
# Author: Philip Kent / NIST Ion Storage & NIST Quantum Processing
# 2016-2021
#
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
    frequency_center = None  # default must be None so it can be overriden in the scan
    enable_auto_tracking = False

    def scan_arguments(self, frequencies={}, npasses={}, nrepeats={}, nbins={}, fit_options={}, guesses=False):
        # assign default values for scan GUI arguments
        for k, v in {'start': -5*MHz, 'stop': 5*MHz, 'npoints': 50, 'unit': 'MHz', 'scale': 1 * MHz, 'ndecimals':4}.items():
            frequencies.setdefault(k, v)

        # crate core scan arguments
        super().scan_arguments(npasses=npasses, nrepeats=nrepeats, nbins=nbins, fit_options=fit_options, guesses=guesses)

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

    def report(self, location='both'):
        super().report(location)
        if self.enable_auto_tracking:
            if location == 'bottom':
                self.logger.info('Frequency Center: %f MHz' % (self.frequency_center / MHz))

    def _attach_models(self):
        self.__load_frequency_center()

        # has a frequency center been specified (either auto or manually)?
        if self.frequency_center is not None:
            # offset scan points by the frequency center
            self._x_offset = self.frequency_center
            self._logger.debug("set _x_offset to frequency_center value of {0}".format(self.frequency_center))

    def __load_frequency_center(self):
        # frequency is manually set in the scan, state that in the debug logs.
        if self.frequency_center is not None:
            self.logger.debug("frequency_center manually set to {0}".format(self.frequency_center))

        # the frequency center is auto loaded from the fits by this class...
        if self.enable_auto_tracking:
            for entry in self._model_registry:
                model = entry['model']
                if 'auto_track' in entry and entry['auto_track']:

                    # hasn't been set yet, ok to auto load
                    if self.frequency_center is None:
                        # load the frequency center from fit just performed
                        if entry['auto_track'] == 'fitresults':
                            self.frequency_center = model.fit.fitresults[model.main_fit]
                            self.logger.debug("frequency_center loaded from fit results and "
                                              "set to {0}".format(self.frequency_center))
                        # load the frequency center from saved dataset value
                        else:
                            self.frequency_center = model.get_main_fit(archive=False)
                            self.logger.debug("frequency_center loaded from datasets and set to {0}".format(
                                self.frequency_center))


class TimeFreqScan(Scan):
    """Allows a scan experiment to scan over either a set of time values or a set of frequency values."""
    frequency_center = None  # default must be None so it can be overriden in the scan
    pulse_time = None  # default must be None so it can be overriden in the scan
    enable_auto_tracking = False

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
        self.__load_frequency_center()

        # tell scan to offset x values by the frequency_center
        # this is done even when not auto-tracking in case the user has manually set frequency_center
        if self.scan == 'frequency' and self.frequency_center is not None:
            self._x_offset = self.frequency_center
            self._logger.debug("set _x_offset to frequency_center value of {0}".format(self.frequency_center))

    def __bind_models(self):
        # bind each registered model to the scan type (frequency or time)
        for entry in self._model_registry:
            model = entry['model']

            # bind model namespace to scan type
            if ('bind' in entry and entry['bind']) or (
                    self.enable_auto_tracking and 'auto_track' in entry and entry['auto_track']):
                # tell the model if this a frequency or time scan
                model.type = self.scan
                model.bind()
                self._logger.debug("set model.type to '{1}' and rebound namespace.  "
                                   "namespace is now '{2}'".format(model._name, self.scan, model.namespace))

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
        # TODO- can we use debugs to show these print statements instead of always
        # print("measuring dark rate")
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
