from .scan import *

class ContinuousScan2D(HasEnvironment):
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
                scanpoint=parent._points_flat[int(parent._idx)][1]
                point=np.array([parent.continuous_index,scanpoint]) #point needs to be [total number of dim 0 passes, dim 1 scan value]
                measure_point=[parent.continuous_measure_point,scanpoint] #measure point needs to be [continuous measure point, dim 1 scan value]
                parent._repeat_loop(point, measure_point, parent._i_points[int(parent._idx)], 1, nrepeats, nmeasurements, measurements, poffset, ncalcs)
                parent._idx += 1
                # _idx is the index for accessing the points array, which gets overwritten after continuous_points scan points
                if parent._idx == parent.npoints:
                    # start overwritting scan points, keep track of number of points still in continuous_index however
                    parent._idx = 0
                    if parent.continuous_logger:
                        # save data to external hdf file after getting to end of index before overwriting it
                        # first_pass happens if number of points (continuous_index) is less than or equal to the size of the points array (continuous_points)
                        # need to know first pass to init the dataset in the external hdf file
                        first_pass = parent.continuous_points >= int(parent.continuous_index)
                        self.continuous_logging(parent, parent.continuous_logger, first_pass)
                    parent.continuous_index+=1
                else:
                    if parent._points_flat[int(parent._idx)][0]>parent._points_flat[int(parent._idx)-1][0]:
                        parent.continuous_index += 1
        except Paused:
            parent._paused = True
        finally:
            parent.cleanup()

    def _load_points(self):
        parent = self.parent
        
        ##########################
        # grab the points...
        if parent._points == None:
            points = list(parent.get_scan_points())
        else:
            points = list(parent._points)

        # warmup points
        if parent._warmup_points == None:
            warmup_points = parent.get_warmup_points()
        else:
            warmup_points = list(parent._warmup_points)

        # force warmup points to be two dimensional.  Otherwise this breaks compilation of the do_measure() method which initially
        # compiles with a signature that accepts a float argument when self.warmup() is called.  Then, an array is passed to do_measure()
        # in _repeat_loop().  This results in a compilation error since do_measure() was already compiled expecting a single float argument
        # but not an array of floats.
        _temp = []
        if not warmup_points:
            warmup_points = [[]]
        else:
            for p in warmup_points:
                try:
                    # warmup points is a 2D array, and is therefore compatible with do_measure
                    _temp.append([p[0], p[1]])
                # handle cases where warmup points is a 1D array and is therefore not compatible with do_measure
                except TypeError:
                    _temp.append([p])
            warmup_points = _temp

        parent.nwarmup_points = np.int32(len(warmup_points))
        # edge case to help artiq compiler. Doesn't like looping through an empty array so always have a least warmup_points=[0], if nwarmup_points=0
        if parent.nwarmup_points:
            parent._warmup_points = np.array(warmup_points, dtype=np.float64)
        else:
            #I believe this should actually be [[0]]
            parent._warmup_points = np.array([0], dtype=np.float64)

        # this turn's ARTIQ scan arguments into lists
        if hasattr(points[0],"__len__"):
            #points was passed as two lists or two arrays with points[0] scan 1, points[1] scan 2
            points = [i for i in range(parent.continuous_points)], [p for p in points[1]]
        else:
            #points was passed as a 1D array for the dim1 scan.
            points = [i for i in range(parent.continuous_points)], [p for p in points]
        

        # total number of scan points over both dimensions
        parent.npoints = np.int32(len(points[0]) * len(points[1]))

        # initialize shapes (these are the authority on data structure sizes)...
        parent._shape = np.array([len(points[0]), len(points[1])], dtype=np.int32)

        # shape of the current scan plot
        if parent._plot_shape == None:
            parent._plot_shape = np.array([np.int32(parent.continuous_plot), parent._shape[1]], dtype=np.int32)

        # initialize 2D data structures...

        # 2D array of scan points (these are saved to the stats.points dataset)
        parent._points = np.array([
            [[x1, x2] for x2 in points[1]] for x1 in points[0]
        ], dtype=np.float64)

        # flattened 1D array of scan points (these are looped over on the core)
        parent._points_flat = np.array([
            [x1, x2] for x1 in points[0] for x2 in points[1]
        ], dtype=np.float64)

        # flattened 1D array of point indices as tuples
        # (these are used on the core to map the flat idx index to the 2D point index)
        parent._i_points = np.array([
            (i1, i2) for i1 in range(parent._shape[0]) for i2 in range(parent._shape[1])
        ], dtype=np.int64)
        
        parent.continuous_index = 0.0

    def _mutate_plot(self, entry, i_point, point, mean, error=None):
        parent = self.parent
        model = entry['model']
        i_point= (int(point[0] % parent.continuous_plot),i_point[1])
        if entry['dimension'] == 1:
            dim1_model = entry['model']
            dim1_scan_end = i_point[1] == parent._shape[1] - 1
            dim1_scan_begin = i_point[1] == 0 and i_point[0] > 0
            dim1_model.set('plots.subplot.i_plot', i_point[0], which='mirror', broadcast=True, persist=True)

            # --- Beginning of dimension 1 scan ---
            # if dim1_scan_begin:
                # if not self.hold_plot:
                    # clear out plot data from previous dimension 1 plots
                #    dim1_model.init_plots(dimension=1)

            # --- Mutate Dimension 1 Plot ---

            # first store the point & mean to the dim1 plot x/y datasets
            # the value of the fitted parameter is plotted as the y value
            # at the current dimension-0 x value (i.e. x0)
            dim1_model.mutate_plot(i_point=i_point, x=point[1], y=mean, error=error, dim=1)

            # --- End of dimension 1 scan ---
            if dim1_scan_end:

                # --- Fit dimension 1 data ---
                # perform a fit over the dimension 1 data
                fit_performed = False
                try:
                    fit_performed, fit_valid, saved, errormsg = parent._fit(entry,dim1_model,
                                                                          save=None,
                                                                          use_mirror=None,
                                                                          dimension=1,
                                                                          i=i_point[0])

                # handle cases when fit fails to converge so the scan doesn't just halt entirely with an
                # unhandeled error
                except RuntimeError:
                    fit_performed = False
                    fit_valid = False
                    saved = False
                    errormsg = 'Runtime Error'

                # fit went ok...
                if fit_performed and hasattr(dim1_model, 'fit'):

                    # --- Plot Dimension 1 Fitline ---
                    # set the fitline to the dimension 1 plot dataset
                    dim1_model.mutate('plots.dim1.fitline', ((i_point[0], i_point[0] + 1), (0, len(dim1_model.fit.fitline))), dim1_model.fit.fitline)

                    # --- Mutate Dimension 0 Plot ---

                    # get the name of the fitted parameter that will be plotted
                    param, error = parent.calculate_dim0(dim1_model)

                    # find the dimension 0 model
                    for entry2 in parent._model_registry:
                        if entry2['dimension'] == 0:
                            dim0_model = entry2['model']

                            # mutate the dimension 0 plot
                            dim0_model.mutate_plot(i_point=i_point, x=point[0], y=param, error=error, dim=0)

            # --- Redraw Plots ---
            # tell the current_scan applet to redraw itself
            dim1_model.set('plots.trigger', 1, which='mirror')
            dim1_model.set('plots.trigger', 0, which='mirror')
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
                        counts = model.stat_model.counts[0:int(parent.continuous_index % parent.continuous_points)]
                    else:
                        counts = model.stat_model.counts

                    name = model.stat_model.namespace + '.counts'
                    logger.append_continuous_data(counts, name, first_pass)
    
