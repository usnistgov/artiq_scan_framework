from artiq_scan_framework.language import *
from artiq.experiment import *
from .data import *
import numpy as np
from .data_logger import *
from .iter import *
from collections import OrderedDict
from ..loop import Loop


class LoopCont(Loop):
    kernel_invariants = {'nmeasurements'}

    def build(self, scan):
        scan.print('Loop1D.build(scan={})'.format(scan.__class__.__name__), 2)
        self.scan = scan
        scan._dim = 1
        self.dtype = np.int32  # data type of the values returned by measure() and stored in self.data.data
        self.cont_logger = None
        self.itr = IterCont(self, looper=self)
        self.measurement = ""
        #self.scan.print('Loop1D.build()', -2)

    def set_kernel_invariants(self):
        self.scan.kernel_invariants.add('nrepeats')

    @staticmethod
    def argdef():
        """Define GUI arguments.  This method is called when LoopCont is passed as an argument to self.scan_arguments in the user
        scan class.  It returns a dictionary that specifies what GUI arguments are to be presented to the user for running this type of loop.

        For example:
        in the user scan class, calling  ```self.scan_arguments(LoopCont)```  will create GUI arguments named:
            'nrepeats', 'continuous_scan', 'continuous_points', 'continuous_plot', 'continuous_measure_point', and 'continuous_save'
        each of these will be assigned to the scan object.
        For example:
        in the user scan class, self.continous_scan will be set to the GUI argument value after calling self.scan_arguments(LoopCont)
        """
        argdef = OrderedDict()
        argdef['nrepeats'] = {
            'processor': NumberValue,
            'processor_args': {'default': 100, 'ndecimals': 0, 'step': 1},
            'group': 'Scan Settings',
            'tooltip': None
        }

        argdef['continuous_points'] = {
            'processor': NumberValue,
            'processor_args': {'default': 1000, 'ndecimals': 0, 'step': 1},
            'group': 'Continuous Scan',
            'tooltip': "number of points to save to stats datasets. Points are overriden after this replacing oldest point taken."
        }
        argdef['continuous_plot'] = {
            'processor': NumberValue,
            'processor_args': {'default': 50, 'ndecimals': 0, 'step': 1},
            'group': 'Continuous Scan',
            'tooltip': "number of points to plot, plotted points scroll to the right as more are plotted, replacing the oldest point."
        }
        argdef['continuous_measure_point'] = {
            'processor': NumberValue,
            # default values, can be overridden by the user in their scan by passing arguments to self.scan_arguments().
            # for example: self.scan_arguments(LoopCont, continuous_measure_point={'unit': 'us', 'scale': us}) adds a unit and scale
            #   to the GUI argument, which are not set by default since they cannot be known in general
            # for example: self.scan_arguments(LoopCont, continuous_measure_point={'group': 'Scan Settings'}) will place the argument in
            #   the group named 'Looper' (instead of 'Continuous Scan')
            'processor_args': {'default': 0.0},
            'group': 'Continuous Scan',
            'tooltip': "point value to be passed to the measure() method. Offset_points and self._x_offset are compatible with this."
        }
        argdef['continuous_save'] = {
            'processor': BooleanValue,
            'processor_args': {'default': False},
            'group': 'Continuous Scan',
            'tooltip': "Save points to external file when datasets will be overriden."
        }
        return argdef

    def init(self, switch, *args, **kwargs):
        """Performs all actions needed to initialize the loop before the scan starts.
            sub-functions are called in the following order:
            1. load_points -- load warmup points
            2. report -- report info to user
            3. offset_points -- offset the scan points
            4. init_datasets or write_datasets -- initialize all datasets when scan starts or restore datasets when scan resumes from being paused
            5. init_loop --
        """
        # 1.
        def load_points(self):
            #self.scan.print('Loop1D.init.load_points')
            # warmup points
            load_warmup_points(self)
        # 2.
        def report(self, location='both'):
            if location == 'top' or location == 'both':
                if self.scan.nrepeats == 1:
                    self.scan.logger.info('START {} / {} repeat'.format(self.scan._name, self.scan.nrepeats))
                else:
                    self.scan.logger.info('START {} / {} repeats'.format(self.scan._name, self.scan.nrepeats))
        def offset_points(self, x_offset):
            self.itr.offset_points(x_offset)
        def init_datasets(self, entry):
            import pprint
            pp = pprint.PrettyPrinter(indent=4)
            #self.scan.print('LoopCont.init.init_datasets(model={}, dimension={})'.format(entry['model'].__class__.__name__, entry['dimension']))
            # initialize the model's datasets
            #self.scan.print('{}::init_datasets('.format(entry['model'].__class__.__name__))
            #self.scan.print('   shapes={}'.format(
            #     pp.pformat({
            #         'itr': self.scan.continuous_points,
            #         'plot': self.scan.continuous_plot,
            #         'pass_means': (1, self.scan.continuous_points),
            #         'stats.counts': (self.scan.continuous_points, self.scan.nrepeats),
            #         'stats.hist': (self.scan.continuous_points, self.scan.nbins)
            #     })
            # ))
            #self.scan.print('   points={}'.format(
            #    self.itr.points,
            #))
            #self.scan.print('   dtype={}'.format(
            #    self.dtype,
            #))
            #self.scan.print('   dimension={})'.format(
            #    entry['dimension']
            #))
            entry['model'].init_datasets(
                shapes={
                    'itr': self.scan.continuous_points,
                    'plot': self.scan.continuous_plot,
                    'pass_means': (1, self.scan.continuous_points),
                    'stats.counts': (self.scan.continuous_points, self.scan.nrepeats),
                    'stats.hist': (self.scan.continuous_points, self.scan.nbins)
                },
                points=self.itr.points,
                dtype=self.dtype,
                dimension=entry['dimension']
            )
        def write_datasets(self, entry):
            model = entry['model']
            #self.scan.print('Loop1D.init.write_datasets(model={})'.format(model.__class__.__name__))
            model.write_datasets(dimension=0)
        def init_loop(self, ncalcs, measurements):
            self.set_kernel_invariants()

            if self.scan.continuous_save:
                self.cont_logger = DataLogger(self.scan)
            self.ncalcs = ncalcs
            self.nmeasurements = len(measurements)
            self.measurements = []
            for m in measurements:
                self.measurements.append(m)
            # init storage
            self.data = Data(shape=(self.nmeasurements, self.scan.nrepeats), dtype=self.dtype)
        if switch == 'report':
            return report(self, *args, **kwargs)
        elif switch == 'load_points':
            return load_points(self, *args, **kwargs)
        elif switch == 'offset_points':
            return offset_points(self, *args, **kwargs)
        elif switch == 'init_datasets':
            return init_datasets(self, *args, **kwargs)
        elif switch == 'write_datasets':
            return write_datasets(self, *args, **kwargs)
        elif switch == 'init_loop':
            return init_loop(self, *args, **kwargs)
        else:
            raise Exception("Unknown switch value for LoopCont::init()")

    @portable
    def loop(self, resume=False):
        nmeasurements = self.nmeasurements
        nrepeats = self.scan.nrepeats
        continuous_save = self.scan.continuous_save
        self.scan.run_warmup(                                                   # run warmup points
            self.warmup_points,
            nmeasurements,
            self.measurements
        )
        ret = [0.0]
        while not self.itr.done(ret):                                           # iterate over each measure point (a.k.a. scan point)
            meas_point = ret[0]                                                 # get the measure point (a.k.a. scan point)
            self.data.reset()                                                   # zero the accumulators in the data store object
            #self.scan._i_pass = 1                                              # legacy
            #self.scan._i_point = self.itr.i_ds
            i_point = self.itr.i_point                                          # init local variables
            if self.scan.enable_pausing:
                check_pause(self.scan)                                          # yield to another experiment or terminate this experiment
            meas_point = self.scan.offset_point(i_point, meas_point)            # user callback
            self.scan.set_scan_point(i_point, meas_point)                       # user callback
            for i_repeat in range(nrepeats):                                    # loop over each repeat
                for i_meas in range(nmeasurements):                             # loop over each measurement
                    self.measurement = self.measurements[i_meas]                            # get the name of the current measurement so that it can be passed to the user callbacks
                    #self.scan.measurement = meas                               # legacy
                    self.scan.before_measure(meas_point, self.measurement)                  # user callback
                    self.scan.lab_before_measure(meas_point, self.measurement)              # user callback
                    val = self.scan.measure(meas_point)                         # call measure
                    self.data.store([i_meas, i_repeat], val)                    # store value
                    self.scan.after_measure(meas_point, self.measurement)                   # user callback
                    self.scan.lab_after_measure(meas_point, self.measurement)               # user callback
            mean = self.data.mean(nmeasurements * nrepeats)                     # get the mean value returned by measure() over all repeats & all measurements
            if self.scan.enable_count_monitor:
                self.set_counts(mean)                                     # RPC: set the mean value to the count monitor dataset
            if self.scan.enable_mutate:
                for i_meas in range(nmeasurements):
                    self.mutate_datasets(i_meas,                                # RPC: mutate the stats & plots datasets
                                         self.itr.i,
                                         i_point,
                                         self.itr.i_plot,
                                         self.data.data[i_meas])
            if self.ncalcs > 0:
                self.calculate(i_point, meas_point)                             # RPC: user callback
            self.scan._analyze_data(i_point, itr=self.itr, data=self.data)      # extension callback (e.g. ReloadingScan)
            self.scan.after_scan_point(i_point, meas_point)                     # user callback
            self.scan._after_scan_point(i_point, meas_point, mean)              # user callback
            if continuous_save and self.itr.at_wrap():                     # next iteration will wrap around and overwrite old data,
                self.log_data()                                                 # so archive to an hdf5 file all data since the last wrap so it isn't lost
            self.itr.step()                                                     # move to the next iteration

    @rpc(flags={"async"})
    def set_counts(self, mean, digits=-1):
        if digits >= 0:
            mean = round(mean, digits)
        self.set_dataset('counts', mean, broadcast=True, persist=True)

    @rpc(flags={"async"})
    def mutate_datasets(self, i_meas, i, i_point, i_plot, data):
        model = None
        for entry in get_registered_models(self.scan, measurement=self.scan.measurements[i_meas]):
            model = entry['model']

            # self.scan.print('mutate_stats({}, i_point={}, i_pass={}, poffset={}, point={}, counts={}'.format(
            #     model.__class__.__name__, i_point, 0, 0, i, data))
            # mutate stats datasets
            mean, err = mutate_stats(model=model, i_point=i_point, i_pass=0, poffset=0, meas_point=i, data=data)
            # mutate plot x/y datasets
            mutate_plot(model, i_point=i_plot, x=i, y=mean, error=err)
        if model:
            trigger_plot(model)

    # interface: for child class (optional)
    @rpc(flags={"async"})
    def calculate(self, i, i_point, i_plot, meas_point):
        for entry in get_registered_models(self.scan, calculation=self.scan.calculations):
            if self.scan.before_calculate(i_point, meas_point, entry['calculation']):  # user callback
                model = entry['model']
                calced_value = model.mutate_datasets_calc(
                    i_point=i_point, i_pass=0, point=meas_point,
                    calculation=entry['calculation'])
                if 'mutate_plot' in entry and entry['mutate_plot']:
                    mutate_plot(model, i_point=i_plot, x=i, y=calced_value, error=None)
                    trigger_plot(model)

    def fit(self, entry, save, use_mirror, dimension, i):
        """Perform the fit"""
        model = entry['model']
        x_data, y_data, errors = get_fit_data(model, use_mirror)

        # for validation methods
        self.scan.min_point = min(x_data)
        self.scan.max_point = max(x_data)

        return model.fit_data(
            x_data=x_data,
            y_data=y_data,
            errors=errors,
            fit_function=model.fit_function,
            guess=self.scan.fit_arguments.guesses(model.fit_function),
            hold=self.scan.fit_arguments.holds(model.fit_function),
            validate=True,
            set=True,  # keep a record of the fit
            save=save,  # save the main fit to the root namespace?
            man_bounds=model.man_bounds,
            man_scale=model.man_scale
        )

    def log_data(self):
        for entry in get_registered_models(self.scan, measurement=True):
            model = entry['model']
            if self.scan._terminated:
                counts = model.counts[0:int(self.i_point)]
            else:
                counts = model.counts
            name = model.namespace + '.counts'
            self.cont_logger.append(counts, name)

    def terminate(self):
        if self.scan.continuous_save:
            self.log_data()