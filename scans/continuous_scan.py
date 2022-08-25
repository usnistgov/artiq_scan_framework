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

            poffset = 0  # not used since there are no passes in continuous scan, just dummy variable
            while True:
                if not resume or parent._idx == 0:
                    parent.before_pass(parent._i_pass)
                parent._repeat_loop(parent.continuous_index, parent.continuous_measure_point, parent._idx, 1, nrepeats, nmeasurements, measurements, poffset, ncalcs)
                parent._idx += 1
                parent.continuous_index += 1
                # _idx is the index for accessing the points array, which gets overwritten after continuous_points scan points
                if parent._idx == parent.continuous_points:
                    # start overwritting scan points, keep track of number of points still in continuous_index however
                    parent._idx = 0
                    if parent.continuous_logger:
                        # save data to external hdf file after getting to end of index before overwriting it
                        # first_pass happens if number of points (continuous_index) is less than or equal to the size of the points array (continuous_points)
                        # need to know first pass to init the dataset in the external hdf file
                        first_pass = parent.continuous_points >= int(parent.continuous_index)
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
        if parent._plot_shape == None:
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
        model.mutate_plot(i_point=i_point, x=point, y=mean, error=error)

        # tell the current_scan applet to redraw itself
        model.set('plots.trigger', 1, which='both')
        model.set('plots.trigger', 0, which='both')

    def _offset_points(self, x_offset):
        parent = self.parent
        if x_offset != None:
            parent.continuous_measure_point += x_offset

    @rpc(flags={"async"})
    def continuous_logging(self, parent, logger, first_pass):
        for entry in parent._model_registry:
            # look at every model, and if it's a measurement append it to external hdf dataset
            if entry['measurement']:
                model = entry['model']
                if hasattr(model, "models"):
                    ###if hasattr models this is a multiresult model and will loop through all models in that multiresult model
                    models = model.fit_models
                else:
                    ###else normal model, just make this an array so the for loop below behaves and only loops for the singular model
                    models = [model]
                for model in models:
                    # get counts for measurement of the measurement model
                    if parent._terminated:
                        # if terminated only append subset of counts corresponding to last taken points
                        counts = model.stat_model.counts[0:int(parent._idx)]
                    else:
                        counts = model.stat_model.counts

                    name = model.stat_model.namespace + '.counts'
                    logger.append_continuous_data(counts, name, first_pass)
