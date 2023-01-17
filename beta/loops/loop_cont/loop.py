from artiq_scan_framework.beta.loop import *
from artiq_scan_framework.beta.snippets import *
from artiq_scan_framework.beta.data import *
import numpy as np
from .data_logger import *
from .iter import *



class LoopCont(Loop):
    kernel_invariants = {'nrepeats', 'npoints', 'nmeasurements'}

    def build(self, scan, nrepeats, continuous_points, continuous_plot, continuous_measure_point, continuous_save):
        self.scan = scan
        scan._dim = 1
        self.dtype = np.int32
        self.save = continuous_save
        self.nrepeats = nrepeats
        self.cont_logger = None
        if self.save:
            self.cont_logger = DataLogger(self.scan)
        self.itr = IterCont(self,
                          meas_point=continuous_measure_point,
                          nds=continuous_points,
                          nplot=continuous_plot
                          )


    def init(self, nmeasurements, ncalcs, measurements):
        self.measurements = measurements
        self.ncalcs = ncalcs
        self.nmeasurements = nmeasurements
        self.measurements = []
        for m in self.scan.measurements:
            self.measurements.append(m)

        # init storage
        self.data = Data(shape=(nmeasurements, self.nrepeats),
                         dtype=self.dtype)

    def load_points(self):
        points = [i for i in range(self.itr.nds)]           # grab the points
        self.npoints = np.int32(self.itr.nds)               # total number of scan points
        self.shape = np.int32(self.itr.nds)                 # shape of the stats.counts dataset
        self.plot_shape = np.int32(self.itr.nplot)          # shape of the plots.x, plots.y, and plots.fitline datasets
        self.points = np.array(points, dtype=np.float64)    # 1D array of scan points (these are saved to the stats.points dataset)

    def offset_points(self, x_offset):
        self.itr.offset_points(x_offset)

    def report(self, location='both'):
        if location == 'top' or location == 'both':
            if self.nrepeats == 1:
                self.scan.logger.info('START {} / {} repeat'.format(self.scan._name, self.nrepeats))
            else:
                self.scan.logger.info('START {} / {} repeats'.format(self.scan._name, self.nrepeats))

    @portable
    def loop(self, resume=False):
        ret = [0.0]
        while not self.itr.done(ret):
            self.scan._i_pass = 1
            self.scan._i_point = self.itr.i_ds
            meas_point = ret[0]

            if self.scan.enable_pausing:
                check_pause(self.scan) #*******

            meas_point = self.scan.offset_point(self.itr.i_ds, meas_point) # user callback
            self.scan.set_scan_point(self.itr.i_ds, meas_point)  # user callback

            self.data.zero_val()
            for i_repeat in range(self.nrepeats):
                for i_measurement in range(self.nmeasurements):
                    measurement = self.measurements[i_measurement]
                    self.scan.measurement = measurement
                    self.scan.before_measure(meas_point, measurement)             # user callback
                    self.scan.lab_before_measure(meas_point, measurement)         # user callback
                    val = self.scan.measure(meas_point)                           # call measure
                    self.data.store([i_measurement, i_repeat], val)                 # store value
                    self.scan.after_measure(meas_point, measurement)              # user callback
                    self.scan.lab_after_measure(meas_point, measurement)          # user callback
            if self.scan.enable_mutate: #*******
                self.mutate_datasets(self.itr.i, self.itr.i_ds, self.itr.i_plot, self.data.data)
            if self.ncalcs > 0:
                self.scan._calculate_all(self.itr.i_ds, i_pass, meas_point) #*******
            for comp in self.scan.components:
                comp.analyze(
                    i_point=self.itr.i_ds,
                    last_pass=self.itr.last_pass(),
                    last_point=self.itr.last_point(),
                    data=self.data.data
                )                                                                   # component hook
            self.scan.after_scan_point(self.itr.i_ds, meas_point)                 # user callback
            mean = self.data.mean(self.nmeasurements*self.nrepeats)
            self.scan._after_scan_point(self.itr.i_ds, meas_point, mean)          # user callback
            if self.scan.enable_count_monitor:
                set_counts(self, mean) #*******
            if self.save and self.itr.at_wrap():
                self.log_data()
            self.itr.step()

    @rpc(flags={"async"})
    def mutate_datasets(self, i, i_point, i_plot, data):
        for i_meas, meas in enumerate(self.measurements):
            for entry in get_registered_models(self.scan, meas):
                model = entry['model']
                # mutate stats
                mean, error = model.mutate_datasets(i_point=i_point, i_pass=0, poffset=0, point=i, counts=data[i_meas])
                # mutate plot
                model.mutate_plot(i_point=i_plot, x=i, y=mean)

                # tell the current_scan applet to redraw itself
                model.set('plots.trigger', 1, which='mirror')
                model.set('plots.trigger', 0, which='mirror')

    def log_data(self):
        for model in get_meas_models(self.scan):
            if self.scan._terminated:
                counts = entry['model'].stat_model.counts[0:int(self.idx)]
            else:
                counts = entry['model'].stat_model.counts

            name = entry['model'].stat_model.namespace + '.counts'
            self.cont_logger.append(counts, name)

    def terminate(self):
        if self.save:
            self.log_data()