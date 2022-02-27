from artiq.experiment import *
from lib.detection import *
from lib.cooling import *
import time
import lib.device_params as params
import sys
import numpy as np
from lib.models.loading_model import *
from time import time, sleep
from class_library.lib import *


class NoPI(Exception):
    pass


class IonLoaded(Exception):
    pass


class Timeout(Exception):
    pass


class Terminate(Exception):
    pass


class Loading(Lib):
    # general
    debug = 0
    repeats = 100
    timeout = 120*s
    windows = 2
    detect_time = params.detect_time
    detect_with_pi = True

    # analysis
    pi_threshold = 5
    loading_threshold = 1

    # oven
    oven_current = 1.13

    oven_warmup_current = 1.15
    oven_warmup_time = 20*s
    second_warmup = 10*s

    # stats
    _events = []  #: Events seen which were either positive or negative indicators of an ion being in the trap.
    positive_events = 0
    negative_events = 0
    messages = []
    loaded = False  #: Ion was successfully loaded by the last call to _load_ion()
    timedout = False
    no_pi = False
    start_time = np.int64(0)
    elapsed = 0.0
    max_attempts = 3

    def build(self, detection, microwaves, cooling, oven=True, **kwargs):
        self.__dict__.update(kwargs)
        self.model = LoadingModel(self, **kwargs)

        # devices
        self.setattr_device('core')
        self.setattr_device('scheduler')
        self.setattr_device('ttl_PI_shutter')
        self.setattr_device('ttl_pmt')
        self.setattr_device('ttl_init_exp')
        if oven:
            self.setattr_device('oven')
        self.setattr_device('dds_bdd')

        # libs
        self.detection = detection
        self.microwaves = microwaves
        self.cooling = cooling

        self.events = [-1.0 for _ in range(self.windows)]
        self.secondary_events = [-1.0]

    def load_oven(self):
        self.setattr_device('oven')

    def can_load(self):
        if self.model.get('attempts') >= self.model.get('max_attempts'):
            self.model.reset_attempts()
            print("max ion load attempts reached, waiting...")
            return False
        return True

    def schedule_wait_experiment(self, synchronous=True):
        self.scheduler.submit(
            pipeline_name='main',
            priority=1000,
            expid={'class_name': 'IonMonitor',
                   'repo_rev': 'N/A',
                   'file': 'startup/ion_monitor.py',
                   'log_level': 30,
                   'arguments': {
                   }
                   },
            due_date=time(),
            flush=False
        )
        if synchronous:
            self._do_block()

    def schedule_load_ion(self, due_date, debug=False, synchronous=True):
        self.model.load()
        self.scheduler.submit(
            pipeline_name='main',
            priority=999,
            expid={'class_name': 'LoadIon',
                   'repo_rev': 'N/A',
                   'file': 'startup/load_ion.py',
                   'log_level': 30,
                   'arguments': {
                       'loading_threshold': self.model.loading_threshold,
                       'pi_threshold': self.model.pi_threshold,
                       'timeout': self.model.timeout,
                       'windows': self.model.windows,
                       'repeats': self.model.repeats,
                       'detect_time': self.model.detect_time,
                       'detect_with_pi':self.model.detect_with_pi,
                       'debug': debug
                   }
            },
            due_date=None,
            flush=False
        )
        if synchronous:
            self._do_block()

    def _do_block(self):
        # block until a previously scheduled experiment has been seen by the scheduler
        max_ = 20
        t = 0
        while not self.scheduler.check_pause():
            sleep(1)
            t += 1
            if t > max_:
                break

    @kernel
    def load_ion(self):
        """Auto load ion"""
        self.timedout = False
        self.loaded = False
        self.no_pi = False

        # max attempts reached, stop and schedule high priority ion monitor
        # to pause all other experiments
        try:
            if self.debug > 1:
                self.oven.set_debug(True)
            self.oven.init()

            print("Oven is warming up...")
            self.oven.on(self.oven_warmup_current)
            start = self.core.get_rtio_counter_mu()
            elap = 0
            while(self.core.mu_to_seconds(elap) < self.oven_warmup_time):
                elap = self.core.get_rtio_counter_mu() - start

            print("Lowering oven current.")
            self.oven.set_remote_control(1)
            self.oven.set_current(self.oven_current)

            start = self.core.get_rtio_counter_mu()
            elap = 0
            while(self.core.mu_to_seconds(elap) < self.second_warmup):
                elap = self.core.get_rtio_counter_mu() - start
            print("Opening PI shutter.")
            self.core.break_realtime()

            self.dds_bdd.set(params.dds_bdd_freq, amplitude=params.dds_bdd_load_amp)
            delay(100*us)
            self.open_pi_shutter()
            self.elapsed = 0.0
            self.start_time = now_mu()
            while self.elapsed < self.timeout:
                if self.scheduler.check_pause():  # yield / terminate
                    raise Terminate

                self._clear_events()

                # pi on during detection
                if self.detect_with_pi:
                    if self._check_with_pi():
                        print("checking with no PI")
                        if self._check_without_pi():
                            raise IonLoaded
                # pi off during detection (e.g. pi scatter rate is high)
                else:
                    if not self._check_for_pi():
                        raise NoPI
                    if self._check_without_pi():
                        raise IonLoaded
                    delay(1*s)

                # update timer
                self.elapsed = self.core.mu_to_seconds(now_mu() - self.start_time)

            raise Timeout
        #except SystemExit:
        #    pass
        #except TerminationRequested:
        #    pass
        except Timeout:
            self.timedout = True
        except NoPI:
            self.no_pi = True
        except IonLoaded:
            self.loaded = True
        except RTIOUnderflow:
            print("RTIO Underflow")
        except RTIOOverflow:
            print("RTIO Overflow")
        except RTIOSequenceError:
            print("RTIO Sequence Error")
        # removed in artiq 3.6
        #except RTIOCollision:
        #    print("RTIO Collision")
        except Terminate:
            pass
        except:
            print("Unknown exception occurred in load_ion")
        finally:
            # cleanup
            self.oven.off()
            self.core.break_realtime()
            self.close_pi_shutter()
            delay(10*us)
            self.dds_bdd.set(params.dds_bdd_freq, amplitude = params.dds_bdd_cool_amp)
            delay(10*us)
            print("Oven is off and PI shutter is closed.")

            # print state
            if self.no_pi:
                print("No PI.")
            if self.timedout:
                print("Timed Out.")
            if self.loaded:
                self.set_dataset('load_ion', True)
                print("Ion Loaded Successfully.")
                print("Took:")
                self.model.reset_attempts()
                print(self.elapsed)

                # 8/13/20 save time it took to load so it can be plotted in Graphana
                self.set_dataset('loading.last_elapsed', self.elapsed, broadcast=True, persist=True, archive=True)
            else:
                # increment attempts
                self.model.increment_attempts()
                self.set_dataset('ion_loaded', False)
            return self.loaded

    @kernel
    def _check_for_pi(self):
        return True
        #counts = [0.0, 0.0]
        #self.measure_counts(counts)
        #if counts[0] < self.pi_threshold:
        #    return False
        #return True

    @kernel
    def _clear_events(self):
        for w in range(self.windows):
            self.events[w] = -1.0
        self.secondary_events[0] = -1.0

    @kernel
    def _check_with_pi(self):
        counts = [0.0, 0.0]
        for w in range(self.windows):
            self.core.break_realtime()
            diff = self.measure_counts(counts)

            # record event
            self.events[w] = diff

            if self.debug > 0:
                print(self.events)

            # check for PI
            if counts[0] < self.pi_threshold:
                print(counts)
                raise NoPI
        if self.analyze(self.events, self.loading_threshold):
            return True
        else:
            return False

    @kernel
    def _check_without_pi(self):
        self.core.break_realtime()
        self.close_pi_shutter()
        counts = [0.0, 0.0]

        self.measure_counts(counts, count_pi=False)
        self.secondary_events[0] = counts[1]

        # ion loaded
        if self.debug > 0:
            print(self.secondary_events)

        if self.analyze(self.secondary_events, self.loading_threshold):
            return True
        # false positive, resume
        else:
            self.core.break_realtime()
            self.open_pi_shutter()
            return False

    @kernel
    def open_pi_shutter(self):
        self.cooling.contain()
        self.ttl_PI_shutter.on()
        delay(15 * ms)

    @kernel
    def close_pi_shutter(self):
        self.cooling.contain()
        self.ttl_PI_shutter.off()
        delay(15 * ms)

    @kernel
    def analyze(self, events, threshold):
        """Analyze events to determine if an ion is in the trap."""
        self.positive_events = 0
        self.negative_events = 0

        for avg_counts in events:
            if avg_counts > threshold:
                self.positive_events += 1
            else:
                self.negative_events += 1

        if self.positive_events == len(events):
            return True
        return False

    @kernel
    def ion_present(self, repeats=100, threshold=0.35):
        """Measure the bright rate to determine if an ion is present"""
        bright_rate = self.measure_bright_rate(repeats)
        return bright_rate > threshold

    @kernel
    def measure_bright_rate(self, repeats=100):
        """Measure bright count rate (counts per detection in the bright state)"""
        counts = np.int64(0)
        for i in range(repeats):
            delay(100 * us)  # loop overhead, not optimized
            self.core.break_realtime()

            # cool
            self.cooling.doppler()

            # detect
            counts += self.detection.detect()
            self.cooling.contain()
        return counts / repeats

    @kernel
    def measure_dark_rate(self, repeats=100):
        """Measure dark count rate (counts per detection in the dark state)"""
        counts = np.int64(0)
        for i in range(repeats):
            delay(100 * us)  # loop overhead, not optimized
            self.core.break_realtime()

            # cool
            self.cooling.doppler()

            # to dark state
            self.microwaves.transition_1()

            # detect
            counts += self.detection.detect()
            self.cooling.contain()
        return counts / repeats

    @kernel
    def measure_counts(self, counts, count_pi=True):
        """Collect PMT counts for PI scatter rate and Ion events"""
        pi_counts = 0
        ion_counts = 0

        for i in range(self.repeats):
            delay(100 * us)  # loop overhead, not optimized
            self.ttl_init_exp.pulse(10*us)
            self.cooling.doppler()
            self.detection.reset()

            # count pi
            if count_pi:
                self.ttl_pmt.gate_rising(self.detect_time)
                pi_counts += self.detection.count()

            # count ion
            with parallel:
                # detect with no noise eater
                self.ttl_pmt.gate_rising(self.detect_time)
                self.detection.ttl_bd.pulse(self.detect_time)
            ion_counts += self.detection.count()

        counts[1] = ion_counts / self.repeats
        if count_pi:
            counts[0] = pi_counts / self.repeats
            diff = counts[1] - counts[0]
        else:
            counts[0] = 0.0
            diff = counts[1]

        self.set_dataset('counts', diff, broadcast=True, persist=True)
        return diff
