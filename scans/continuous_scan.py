from .scan import *


class ContinuousScan(HasEnvironment):
    def build(self, parent):
        self.parent = parent

    @portable
    def _loop(self, resume=False):
        parent = self.parent
        ncalcs = parent._ncalcs
        nmeasurements = parent.nmeasurements
        nrepeats = parent.nrepeats
        measurements = parent.measurements

        try:
            # callback
            parent._before_loop(resume)
            # callback
            parent.initialize_devices()

            poffset = 0
            while True:
                if not resume or parent._idx == 0:
                    parent.before_pass(parent._i_pass)
                parent._repeat_loop(parent.continuous_index, parent.continuous_measure_point, parent._idx, 1, nrepeats, nmeasurements, measurements, poffset, ncalcs)
                parent._idx += 1
                parent.continuous_index += 1
                if parent._idx == parent.continuous_points:
                    parent._idx = 0
                    if parent.continuous_logger:
                        first_pass = parent.continuous_points == int(parent.continuous_index)
                        self.continuous_logging(parent, parent.continuous_logger, first_pass)
        except Paused:
            parent._paused = True
        finally:
            parent.cleanup()

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

        parent.continuous_index = 0.0

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

                name = entry['model'].stat_model.namespace + '.counts'
                logger.append_continuous_data(counts, name, first_pass)
