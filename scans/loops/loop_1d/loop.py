from artiq_scan_framework.language import *
from artiq.experiment import *
import numpy as np
from .iter import *
from .data import *
from ..loop import Loop
from collections import OrderedDict


class Loop1D(Loop):
    kernel_invariants = {'nmeasurements'}

    def build(self, scan, dtype=np.int32):
        self.scan = scan
        scan._dim = 1
        scan._i_point = np.int32(0)
        self.dtype = dtype  # data type of values returned by measure() and stored in self.data.data
        self.itr = Iter1D(self, looper=self)
        self.measurement = ""

    def set_kernel_invariants(self):
        self.scan.kernel_invariants.add('nrepeats')
        self.scan.kernel_invariants.add('npasses')

    @staticmethod
    def argdef():
        """Define GUI arguments"""
        argdef = OrderedDict()
        argdef['npasses'] = {
            'processor': NumberValue,
            'processor_args': {'default': 1, 'ndecimals': 0, 'step': 1},
            'group': 'Scan Settings',
            'tooltip': None
        }
        argdef['nrepeats'] = {
            'processor': NumberValue,
            # default values, can be overridden by the user in their scan by passing arguments to self.scan_arguments().
            # for example: self.scan_arguments(nrepeats={'default': 50}) changes the default number of repeats to 50 (instead of 100)
            # for example: self.scan_arguments(nrepeats={'group': 'Looper'}) will place the argument in the group named 'Looper' (instead of 'Scan Settings')
            'processor_args': {'default':100, 'ndecimals':0, 'step':1},
            'group': 'Scan Settings',
            'tooltip': None
        }
        return argdef

    def init(self, switch, *args, **kwargs): #nmeasurements, ncalcs, measurements):
        # order of execution:
        # 1. load_points, 2. report, 3. offset_points, 4. init_datasets or write_datasets, 5. init_loop
        def load_points(self):
            # scan points
            points = get_scan_points(self.scan)
            self.itr.load_points(points)
            # warmup points
            load_warmup_points(self)
        def report(self, location='both'):
            if location == 'top' or location == 'both':
                if self.scan.nrepeats == 1:
                    self.scan.logger.info('START {} / {} repeat'.format(self.scan._name, self.scan.nrepeats))
                else:
                    self.scan.logger.info('START {} / {} repeats'.format(self.scan._name, self.scan.nrepeats))
        def offset_points(self, x_offset):
            if x_offset is not None:
                self.itr.offset_points(x_offset)
        def init_datasets(self, entry):
            entry['model'].init_datasets(
                shapes={
                    'itr': self.itr.shape,
                    'plot': self.itr.shape,
                    'pass_means': (self.scan.npasses, self.itr.shape),
                    'stats.counts': (self.itr.shape, self.scan.npasses * self.scan.nrepeats),
                    'stats.hist': (self.itr.shape, self.scan.nbins)
                },
                points=self.itr.points,
                dtype=self.dtype,
                dimension=entry['dimension']
            )
        def write_datasets(self, entry):
            model = entry['model']
            model.write_datasets(dimension=0)
        def init_loop(self, ncalcs, measurements):
            self.set_kernel_invariants()
            self.measurements = measurements
            self.nmeasurements = len(measurements)
            self.ncalcs = ncalcs
            self.data = Data(shape=(self.nmeasurements, self.scan.nrepeats), dtype=self.dtype)
        if switch == 'load_points':
            return load_points(self, *args, **kwargs)
        elif switch == 'report':
            return report(self, *args, **kwargs)
        elif switch == 'offset_points':
            return offset_points(self, *args, **kwargs)
        elif switch == 'init_datasets':
            return init_datasets(self, *args, **kwargs)
        elif switch == 'write_datasets':
            return write_datasets(self, *args, **kwargs)
        elif switch == 'init_loop':
            return init_loop(self, *args, **kwargs)

    @portable
    def loop(self, resume=False):
        nmeasurements = self.nmeasurements
        nrepeats = self.scan.nrepeats
        ncalcs = self.ncalcs
        self.scan.run_warmup(                                                   # run warmup points
            self.warmup_points,
            self.nmeasurements,
            self.measurements
        )
        ret = [0.0]
        while not self.itr.done(ret):                                           # iterate over each measure point (a.k.a. scan point)

            meas_point = ret[0]                                                 # get the measure point (a.k.a. scan point)
            self.data.reset()                                                   # zero the accumulators in the data store object
            i_point = self.itr.i_point                                          # init local variables
            i_pass = self.itr.i_pass
            #print(self.itr.i)
            # print(i_point)
            # print(i_pass)
            #self.scan._i_pass = i_pass                                         # legacy
            #self.scan._i_point = i_point
            if self.scan.enable_pausing:
                check_pause(self.scan)                                          # yield to another experiment or terminate this experiment
            if self.itr.i_point == 0:                                           # the pass starts when i_point is zero
                self.scan.before_pass(i_pass)                                   # user callback
            meas_point = self.scan.offset_point(i_point, meas_point)            # user callback
            self.scan.set_scan_point(i_point, meas_point)                       # user callback
            for i_repeat in range(nrepeats):                                    # loop over each repeat
                for i_meas in range(nmeasurements):                             # loop over each measurement
                    self.scan.measurement = self.measurements[i_meas]                            # get the name of the current measurement so that it can be passed to the user callbacks

                    # throws AttributeError: 'NoneType' object has no attribute 'begin' commenting out for now
                    #self.scan.measurement = meas                                # legacy
                    self.scan.before_measure(meas_point, self.scan.measurement)                  # user callback
                    self.scan.lab_before_measure(meas_point, self.scan.measurement)              # user callback
                    val = self.scan.do_measure(meas_point)                      # call the user's measure() method
                    self.data.store([i_meas, i_repeat], val)                    # store the value returned by measure() into the data store object
                    self.scan.after_measure(meas_point, self.scan.measurement)                   # user callback
                    self.scan.lab_after_measure(meas_point, self.scan.measurement)               # user callback
            mean = self.data.mean(nmeasurements * nrepeats)                     # get the mean value returned by measure() over all repeats & all measurements
            if self.scan.enable_count_monitor:
                self.set_counts(mean)                                          # set the mean value to the count monitor dataset
            if self.scan.enable_mutate:
                for i_meas in range(nmeasurements):
                    self.mutate_datasets(i_meas,                                # mutate the stats & plots datasets
                                         i_point,
                                         i_pass,
                                         self.itr.i_pass * nrepeats, #poffset
                                         meas_point,
                                         self.data.data[i_meas])
            if ncalcs > 0:
                self.calculate(i_point, i_pass, meas_point)                      # user callback
            self.scan.after_scan_point(i_point, meas_point)                      # user callback
            self.scan._after_scan_point(i_point, meas_point, mean)               # user callback
            ok = self.scan._analyze_data(i_point, itr=self.itr, data=self.data)  # extension callback (e.g. ReloadingScan)
            if ok:
                self.itr.step()                                                      # move to the next scan point

    @rpc(flags={"async"})
    def set_counts(self, mean, digits=-1):
        if digits >= 0:
            mean = round(mean, digits)
        self.set_dataset('counts', mean, broadcast=True, persist=True)

    @rpc(flags={"async"})
    def mutate_datasets(self, i_meas, i_point, i_pass, poffset, meas_point, data):
        model = None
        for entry in get_registered_models(self.scan, measurement=self.measurements[i_meas]):
            model = entry['model']
            mean, err = mutate_stats(model, i_point, i_pass, poffset,
                                       meas_point, data)                        # mutate stats datasets
            mutate_plot(model, i_point=i_point, x=meas_point, y=mean,           # mutate plot x/y datasets
                        error=err)
        if model:
            trigger_plot(model)                                                     # tell the current_scan applet to redraw itself

    @rpc(flags={"async"})
    def calculate(self, i_point, i_pass, meas_point):
        for entry in get_registered_models(self.scan, calculation=self.scan.calculations):
            if self.scan.before_calculate(i_point, meas_point,
                                          entry['calculation']):                # user callback
                model = entry['model']
                calced_value = mutate_datasets_calc(model, i_point, i_pass,
                                                    meas_point,
                                                    entry['calculation'])
                if 'mutate_plot' in entry and entry['mutate_plot']:
                    mutate_plot(model, i_point=i_point, x=meas_point, y=calced_value, error=None)
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
            man_scale=model.man_scale)

    def terminate(self):
        pass
