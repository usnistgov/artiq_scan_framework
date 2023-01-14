from artiq_stylus.lib.stylus_scan import *
from artiq_stylus.lib.libs import *
from artiq_stylus.lib.models.ramsey import *




class MyContinuousScan(HasEnvironment):
    def build(self, parent):
        self.parent = parent

    @portable
    def _loop(self, resume=False):

        try:

            i = 0
            while True:
                self.parent._repeat_loop(
                    self.parent.continuous_index,
                    self.parent.continuous_measure_point,
                    self.parent._idx, 1,
                    100, 1, self.parent.measurements, 0, 0, True, True)
                #
                # i += 1
                # if i % 100 == 0:
                #     self.parent.check_pause()
                #     print('checked')
                #     print(i)
        except Paused:
            self.parent._paused = True

    def _load_points(self):
        parent = self.parent
        # grab the points
        points = [i for i in range(parent.continuous_points)]

        # total number of scan points
        parent.npoints = np.int32(parent.continuous_points)

        # initialize shapes (these are the authority on data structure sizes)...

        # shape of the stats.counts dataset
        parent._shape = np.int32(parent.npoints)

        # shape of the plots.x, plots.y, and plots.fitline datasets
        if parent._plot_shape is None:
            parent._plot_shape = np.int32(parent.continuous_plot)

        # initialize 1D data structures...

        # 1D array of scan points (these are saved to the stats.points dataset)
        parent._points = np.array(points, dtype=np.float64)

        # flattened 1D array of scan points (these are looped over on the core)
        parent._points_flat = np.array(points, dtype=np.float64)

        parent.continuous_index = 0

        # --- Philip's addition
        parent._i_points = np.array(range(parent.npoints), dtype=np.int64)

    def _mutate_plot(self, entry, i_point, point, mean, error=None):
        parent = self.parent
        model = entry['model']
        i_point = int(point % parent.continuous_plot)
        # mutate plot x/y datasets
        model.mutate_plot(i_point=i_point, x=point, y=mean)

        # tell the current_scan applet to redraw itself
        model.set('plots.trigger', 1, which='mirror')
        model.set('plots.trigger', 0, which='mirror')

    def _offset_points(self, x_offset):
        parent = self.parent
        if x_offset is not None:
            parent.continuous_measure_point += x_offset

    def continuous_logging(self, parent, logger, first_pass):
        for entry in parent._model_registry:
            # model registered for this measurement
            if entry['measurement']:
                # grab the model for the measurement from the registry
                # get counts for measurement of the measurement model
                if parent._terminated:
                    counts = entry['model'].stat_model.counts[0:int(parent._idx)]
                else:
                    counts = entry['model'].stat_model.counts

                # PK added 01/10/2023 check that logger exists.  Fixes AttributeError when logger is not created
                if logger is not None:
                    name = entry['model'].stat_model.namespace + '.counts'
                    logger.append_continuous_data(counts, name, first_pass)


class TestContinuousScan2(Scan1D, EnvExperiment):

    def build(self):
        self.setattr_device("core")
        self.setattr_device('scheduler')
        self.scan_arguments()

    def get_scan_points(self):
        return [i for i in range(10)]

    @kernel
    def measure(self, point):
        return 0

    @portable
    def _repeat_loop(self, point, measure_point, i_point, i_pass, nrepeats, nmeasurements, measurements, poffset, ncalcs,
                     last_point=False, last_pass=False):
        check_pause = self.scheduler.check_pause()
        if check_pause:
            print('raise Paused')
            raise Paused
        #data = self._data[0]
        #print(data)
        #self.rpc(i_point, i_pass, poffset, 0, point)
