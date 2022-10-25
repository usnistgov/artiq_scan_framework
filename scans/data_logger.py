import time, os
import h5py
from artiq import __version__ as artiq_version

if float(artiq_version[0])<4:
    from artiq.protocols import pyon
else:
    from sipyco import pyon


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
            data_shape=list(data.shape) #n element list for size of counts array, should be continuous_points*nrepeats or continuous_point*number of scan points of dim1 scan*nrepeats for 2D scan
            data_i=data.shape[0] #number of continuous_points
            dataset = f['datasets'] #dictionary of datasets in the created logging file
            if first_pass:
                max_shape=data_shape.copy() #make a copy of input data shape to set maxshape size tuple
                max_shape[0]=None #number of continuous points is None for maxshape tuple
                previous_data = dataset.create_dataset(name, data.shape,maxshape=tuple(max_shape)) #this creates a new dataset of the name given, with a chunk of data size of data.shape, with unlimited extension allowed of data[i] i index (added in chunks)
                dataset_i=0 #no previous data so set previous_data[0:data_i]=data
            else:
                previous_data = dataset[name] #get previous logged data
                dataset_i=previous_data.shape[0] #get length of first index logged points
                resize_shape=data_shape.copy() #create resize shape list to make a tuple  to resize array with new data
                resize_shape[0]+=dataset_i #increase first index by number of previous data points
                previous_data.resize(tuple(resize_shape))
            previous_data[dataset_i:dataset_i+data_i]=data #set previous data array at new chunk entries to incoming data