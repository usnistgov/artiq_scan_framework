from artiq.experiment import *
from artiq_scan_framework.lib.ion_checker import *
from artiq_scan_framework.lib.loading_interface import *
from artiq_scan_framework.exceptions import Paused
import time


class IonLoad(HasEnvironment):
    """Allows detection of lost ion, pausing scan, reloading ion, and resuming scan"""

    def build(self, scan, ion_checker, check_for_ion={'default': True}):
        self.scan = scan
        self.ion_checker = ion_checker
        if check_for_ion is not False:
            for k, v in {'default': False, 'group': 'Ion Checker'}.items():
                check_for_ion.setdefault(k, v)
            group = check_for_ion['group']
            del check_for_ion['group']
            self.setattr_argument("check_for_ion", BooleanValue(**check_for_ion), group)
        if not self.check_for_ion:
            self.measure_thresholds = False

    # hook
    @portable
    def before_loop(self, resume):
        if self.check_for_ion:
            try:
                self.ion_checker.initialze(resume)
            except LoadIon:
                self.schedule()
                raise Paused

    # hook
    @portable
    def analyze(self, i_point, last_itr, data):
        #print('IonLoad::analyze', i_point, last_itr, data)
        if self.check_for_ion:
            try:
                # iterate over scan points in the same order as is done in scan.py
                for i_measurement in range(self.scan.nmeasurements):
                    self.ion_checker.ion_present(data[i_measurement], self.scan.nrepeats, last_point=last_itr)
            except LostIon:
                # rewind to the earliest scan point where the ion could have been lost.
                self.scan.looper.itr.rewind(num_points=self.ion_checker.rewind_num_points)

                # Schedule an experiment to load an ion.
                self.scan.logger.error("Ion lost, reloading...")
                self.schedule()

                # break main loop in scan.py
                raise Paused
            except IonPresent:
                pass

    def schedule(self):
        # try to load or wait if tried too many times

        # ion loading can't be performed for some reason
        if not self.ion_checker.loading.can_load():

            # schedule a high priority experiment (e.g. ion_monitor) that will pause this scan
            # until the issue can be fixed.
            self.scan.logger.error("Can't load ion, scheduling blocking experiment until issue is fixed.")
            self.ion_checker.loading.schedule_wait_experiment()
            self.scan._yield()
        else:
            # schedule the load ion experiment
            # self.logger.warning("Scheduling ion reload.")
            self.ion_checker.loading.schedule_load_ion(due_date=time.time(), synchronous=True)
