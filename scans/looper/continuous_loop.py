from artiq.experiment import *
import numpy as np
from artiq_scan_framework.exceptions import Paused
import time, os
import h5py
from artiq.protocols import pyon
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


class ContinuousLooper(HasEnvironment):
    kernel_invariants = {'nrepeats', 'npoints', 'nmeasurements'}

    # -------- Runs on host --------

    def build(self, parent, nrepeats, continuous_points, continuous_plot, continuous_measure_point, continuous_save):
        self.nrepeats = nrepeats
        self.parent = parent
        self.dtype = np.int32
        self.continuous_save = continuous_save
        self.continuous_points = continuous_points
        self.continuous_plot = continuous_plot
        self.continuous_measure_point = continuous_measure_point
        self.npoints = None
        self.measurement = ''  #: the current measurement
        self._idx = np.int32(0)
        if self.continuous_save:
            self.continuous_logger = DataLogger(self)
        else:
            self.continuous_logger = None

    def initialize(self, nmeasurements, nrepeats):
        self.nmeasurements = nmeasurements
        self.measurements = []
        for m in self.parent.measurements:
            self.measurements.append(m)
        self.init_storage(nmeasurements, nrepeats)

    def init_storage(self, nmeasurements, nrepeats):
        """initialize memory to record counts on core device"""

        #: 2D array of counts measured for a given scan point, i.e. nmeasurement*nrepeats
        self.counts = self.dtype(0)
        self.counts_zero = self.dtype(0)
        self.data = np.zeros((nmeasurements, nrepeats), dtype=self.dtype)

    @portable
    def store_measurement(self, i_measurement, i_repeat, count):
        self.data[i_measurement][i_repeat] = count
        self.counts += count

    @portable
    def calculate_mean(self, nrepeats, nmeasurements):
        return self.counts / (nrepeats * nmeasurements)

    def terminate(self):
        if self.continuous_save:
            first_pass = self.continuous_points == int(self.continuous_index)
            self.continuous_logging(self, first_pass)

    def continuous_logging(self, parent, first_pass):
        if self.continuous_save:
            for entry in parent._model_registry:
                # model registered for this measurement
                if entry['measurement']:
                    # grab the model for the measurement from the registry
                    # get counts for measurement of the measurement model
                    if parent._terminated:
                        counts = entry['model'].stat_model.counts[0:int(self._idx)]
                    else:
                        counts = entry['model'].stat_model.counts

                    name = entry['model'].stat_model.namespace + '.counts'
                    self.continuous_logger.append_continuous_data(counts, name, first_pass)

    def load_points(self):
        parent = self.parent
        # grab the points
        points = [i for i in range(self.continuous_points)]
        # total number of scan points
        self.npoints = np.int32(self.continuous_points)

        # shape of the stats.counts dataset
        self.shape = np.int32(self.npoints)

        # shape of the plots.x, plots.y, and plots.fitline datasets
        self.plot_shape = np.int32(self.continuous_plot)

        # 1D array of scan points (these are saved to the stats.points dataset)
        self.points = np.array(points, dtype=np.float64)
        self.continuous_index = 0

    def offset_points(self, x_offset):
        parent = self.parent
        if x_offset is not None:
            self.continuous_measure_point += x_offset

    def mutate_plot(self, entry, i_point, point, mean, error=None):
        model = entry['model']
        i_point = int(point % self.continuous_plot)
        # mutate plot x/y datasets
        model.mutate_plot(i_point=i_point, x=point, y=mean)

        # tell the current_scan applet to redraw itself
        model.set('plots.trigger', 1, which='mirror')
        model.set('plots.trigger', 0, which='mirror')

    # -------- Runs on core device --------

    @portable
    def init_repeat_loop(self):
        self.counts = self.counts_zero

    @portable
    def loop(self, ncalcs, nmeasurements, nrepeats, measurements, resume=False):
        parent = self.parent
        poffset = 0
        while True:
            # if not resume or self._idx == 0:
            #     parent.before_pass(parent._i_pass)
            i_pass = 0
            i_point = self._idx
            last_point = False
            last_pass = False
            point = self.continuous_index

            # callback: offset_point()
            #    dynamically offset the scan point
            measure_point = parent.offset_point(i_point, self.continuous_measure_point)

            # -- check_pause
            # check for higher priority experiment or termination requested
            if parent.enable_pausing:
                # cost: 3.6 ms
                parent.check_pause()

            # callback: set_scan_point()
            parent.set_scan_point(i_point, measure_point)

            # initialize the repeat loop
            self.init_repeat_loop()

            # repeat loop
            for i_repeat in range(nrepeats):
                # each measurement
                for i_measurement in range(nmeasurements):
                    # so other methods know what the current measurement is
                    self.parent.measurement = measurements[i_measurement]
                    self.measurement = measurements[i_measurement]

                    # callback: before_measure
                    self.parent.before_measure(measure_point, self.measurement)

                    # callback: lab_before_measure
                    self.parent.lab_before_measure(measure_point, self.measurement)

                    # callback: do_measure()
                    count = self.parent.do_measure(measure_point)

                    # store the measurement
                    self.store_measurement(i_measurement, i_repeat, count)

                    # callback: after_measure()
                    self.parent.after_measure(measure_point, self.measurement)

                    # callback: lab_after_measure()
                    self.parent.lab_after_measure(measure_point, self.measurement)

            # update the dataset used to monitor counts
            # mean = counts / (nrepeats*nmeasurements*self.nresults)
            mean = self.calculate_mean(nrepeats, nmeasurements)

            # RPC: mutate_datasets()
            #   mutate dataset values
            #   cost: 18 ms per point
            if parent.enable_mutate:
                # each measurement
                for i_measurement in range(nmeasurements):
                    # send data to the model
                    parent.mutate_datasets(
                        i_point,
                        i_pass,
                        poffset,
                        self.measurements[i_measurement],
                        point,
                        self.data[i_measurement]
                    )

            # RPC: _calculate_all()
            #   perform calculations
            if ncalcs > 0:
                parent._calculate_all(i_point, i_pass, measure_point)

            # callback: _analyze_data()
            parent._analyze_data(i_point, last_pass, last_point)

            # callback: after_scan_point()
            parent.after_scan_point(i_point, measure_point)

            # callback: _after_scan_point()
            parent._after_scan_point(i_point, measure_point, mean)

            # RPC: set counts dataset
            if parent.enable_count_monitor:
                # cost: 2.7 ms
                parent.set_counts(mean)

            # update indexes
            self._idx += 1
            self.continuous_index += 1

            if self._idx == self.continuous_points:
                self._idx = 0
                if self.continuous_save:
                    first_pass = self.continuous_points == int(self.continuous_index)
                    self.continuous_logging(parent, first_pass)

    def report(self, location='both'):
        """Interface method (optional, has default behavior)

        Logs details about the scan to the log window.
        Runs during initialization after the scan points and warmup points have been loaded but before datasets
        have been initialized.
        """

        if location == 'top' or location == 'both':
            if self.nrepeats == 1:
                self.parent.logger.info('START {} / {} repeat'.format(self.parent._name, self.nrepeats))
            else:
                self.parent.logger.info('START {} / {} repeats'.format(self.parent._name, self.nrepeats))

    @portable
    def rewind(self, num_points):
        """Rewind the cursor from the current pass and point indices by the specified number of points.  The cursor can
          be rewound into a previous pass.  The cursor cannot be rewound past the first point of the first pass.

          :param num_points: The current cursor will be moved to this number of scan points before its current value.
        """
        if num_points > 0:
            self._idx -= num_points
            if self._idx < 0:
                self._idx = 0

