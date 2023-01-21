from artiq.language.core import *
from artiq_scan_framework.beta.scan import Scan
#from artiq_scan_framework.lib.ion_checker import *
from artiq_scan_framework.exceptions import *
from artiq_scan_framework.lib.loading_interface import *
import time

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

    def build(self):
        self.print('beta.ReloadingScan::build()', 2)
        super().build()
        self.print('beta.ReloadingScan::build()', -2)

    # ====== Scan Interface Methods ======

    def _scan_arguments(self, check_for_ion={'default': True}, *args, **kwargs):
        if self.enable_reloading:
            if check_for_ion is not False:
                for k, v in {'default': False, 'group': 'Ion Checker'}.items():
                    check_for_ion.setdefault(k, v)
                group = check_for_ion['group']
                del check_for_ion['group']
                self.setattr_argument("check_for_ion", BooleanValue(**check_for_ion), group)
        super()._scan_arguments(*args, **kwargs)

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
        if self.check_for_ion:
            try:
                self.ion_checker.initialze(resume)
            except LoadIon:
                self._schedule_load_ion()
                raise Paused

    @portable
    def _analyze_data(self, i_point, itr, data):
        if self.check_for_ion:
            try:
                # iterate over scan points in the same order as is done in scan.py
                for i_measurement in range(self.looper.nmeasurements):
                    self.ion_checker.ion_present(data.data[i_measurement], self.nrepeats, last_point=itr.last_itr())
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
            self.logger.error("Can't load ion, scheduling blocking experiment until issue is fixed.")
            self.loading.schedule_wait_experiment()
            self._yield()
            self._schedule_load_ion()
            return
        else:
            # schedule the load ion experiment
            # self.logger.warning("Scheduling ion reload.")
            self.loading.schedule_load_ion(due_date=time.time(), synchronous=True)