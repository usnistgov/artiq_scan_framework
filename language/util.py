import time
import inspect
from artiq.experiment import *


# for debugging purposes
def print_caller():
    frm = inspect.stack()[2]
    mod = inspect.getmodule(frm[0])
    print('Caller: {1}.{0}'.format(frm[3], mod.__name__))


def block(self, msg=None):
    """Block the caller until the user performs some action and manually sets the 'wait' dataset to 0"""
    import os
    rid = self.scheduler.submit(
        pipeline_name='main',
        priority=999,
        expid={'class_name': "Block",
           'repo_rev': 'N/A',
           'file': os.path.abspath(__file__),
           'log_level': self.scheduler.expid['log_level'],
           'arguments': {
               'message': msg
           }
        },
        due_date=None,
        flush=False
    )
    while rid not in self.scheduler.get_status():
        time.sleep(1)
    while self.scheduler.get_status()[rid]['status'] is not 'prepare_done':
        time.sleep(1)
    self.core.comm.close()
    self.scheduler.pause()


class Block(EnvExperiment):

    def build(self):
        self.setattr_device('scheduler')
        self.setattr_argument('message', StringValue(default=""))

    def run(self):
        if self.message:
            print(self.message)
        else:
            print('blocking...')
        while True:
            if self.scheduler.check_pause():
                return