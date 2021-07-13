import unittest
from artiq.master.databases import DeviceDB, DatasetDB
from artiq.master.worker_db import DeviceManager, DatasetManager
import os
from artiq.language import *
import artiq.master.worker_impl as worker


class TestCase(unittest.TestCase, HasEnvironment):

    def setUp(self, arguments=None):
        HasEnvironment.__init__(self, (None, None, None))

        # paths
        unit_test_path = os.path.abspath(os.path.dirname(__file__))
        ddb_path = os.path.join(unit_test_path, 'unit_test_device_db.py')
        dsdb_path = os.path.join(unit_test_path, 'unit_test_dataset_db.pyon')

        self.dataset_db = DatasetDB(dsdb_path)
        self.device_db = DeviceDB(ddb_path)
        self.argument_mgr = worker.ProcessArgumentManager(arguments)
        scheduler = worker.Scheduler()
        scheduler.rid = 0
        self._HasEnvironment__dataset_mgr = DatasetManager(self.dataset_db)
        self._HasEnvironment__device_mgr = DeviceManager(self.device_db,
                                                         virtual_devices={"scheduler": scheduler})
        self._HasEnvironment__argument_mgr = self.argument_mgr

    def set_arguments(self, arguments):
        self.argument_mgr.unprocessed_arguments = arguments

    def run_experiment(self, experiment):
        experiment.prepare()
        experiment.run()
        experiment.analyze()

    def run_scan(self, cls, arguments={}):
        exception = ""
        compiled = False
        ran_ok = False
        try:
            self.set_arguments(arguments)
            scan = cls(self)
            scan.enable_pausing = False
            self.run_experiment(scan)
            ran_ok = True
        except OSError as msg:
            exception = msg
            compiled = True
        except Exception as msg:
            exception = msg
        return ran_ok, compiled, exception

if __name__ == '__main__':
    unittest.main()
