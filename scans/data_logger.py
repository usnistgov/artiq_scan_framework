import time, os
import h5py
from sipyco import pyon
from artiq import __version__ as artiq_version


class DataLogger:
    def __init__(self, experiment):
        self.exp = experiment
        start_time = time.localtime()
        self.filep = ''.join([
            os.path.abspath('.'),
            '\\',
            '{:09}-{}_Log.h5'.format(
                self.exp.scheduler.rid, experiment.__class__.__name__)
        ])
        with h5py.File(self.filep, 'a') as f:
            f.create_group('datasets')
            f['artiq_version'] = artiq_version
            f['rid'] = self.exp.scheduler.rid
            f['start_time'] = int(time.mktime(start_time))
            f['expid'] = pyon.encode(self.exp.scheduler.expid)

    def append_continuous_data(self, data, name, first_pass):
        with h5py.File(self.filep, 'a') as f:
            data_i=data.shape[0]
            data_j=data.shape[1]
            dataset = f['datasets']
            if first_pass:
                previous_data = dataset.create_dataset(name, data.shape,maxshape=(None,data_j))
                dataset_i=0
            else:
                previous_data = dataset[name]
                dataset_i=previous_data.shape[0]
                previous_data.resize((dataset_i+data_i,data_j))
            previous_data[dataset_i:dataset_i+data_i]=data