from .scan import *


class Scan2D(Scan):
    """Extension of the :class:`~artiq_scan_framework.scans.scan.Scan` class for 2D scans.  All 2D scans should inherit from
        this class."""
    hold_plot = False

    def __init__(self, managers_or_parent, *args, **kwargs):
        super().__init__(managers_or_parent, *args, **kwargs)
        self._dim = 2
        self._i_point = np.array([0, 0], dtype=np.int64)

    # private: for scan.py
    def _load_points(self):

        # grab the points...
        if self._points is None:
            points = list(self.get_scan_points())
        else:
            points = list(self._points)

        # warmup points
        if self._warmup_points is None:
            warmup_points = self.get_warmup_points()
        else:
            warmup_points = list(self._warmup_points)

        # force warmup points to be two dimensional.  Otherwise this breaks compilation of the do_measure() method which initially
        # compiles with a signature that accepts a float argument when self.warmup() is called.  Then, an array is passed to do_measure()
        # in _repeat_loop().  This results in a compilation error since do_measure() was already compiled expecting a single float argument
        # but not an array of floats.

        if not warmup_points:
            # bit of a hack so that the warmup method can compile, otherwise Artiq balks at the dimension of the point argument
            self._warmup_points = np.array([[]], dtype=np.float64)
            self.nwarmup_points = 0
        else:
            _temp = []
            for p in warmup_points:
                try:
                    # warmup points is a 2D array, and is therefore compatible with do_measure
                    _temp.append([p[0], p[1]])
                # handle cases where warmup points is a 1D array and is therefore not compatible with do_measure
                except TypeError:
                    _temp.append([p])
            self.nwarmup_points = np.int32(len(_temp))
            self._warmup_points = np.array(_temp, dtype=np.float64)

        # this turn's ARTIQ scan arguments into lists
        points = [p for p in points[0]], [p for p in points[1]]

        # total number of scan points over both dimensions
        self.npoints = np.int32(len(points[0]) * len(points[1]))

        # initialize shapes (these are the authority on data structure sizes)...
        self._shape = np.array([len(points[0]), len(points[1])], dtype=np.int32)

        # shape of the current scan plot
        if self._plot_shape is None:
            self._plot_shape = np.array([self._shape[0], self._shape[1]], dtype=np.int32)

        # initialize 2D data structures...

        # 2D array of scan points (these are saved to the stats.points dataset)
        self._points = np.array([
            [[x1, x2] for x2 in points[1]] for x1 in points[0]
        ], dtype=np.float64)

        # flattened 1D array of scan points (these are looped over on the core)
        self._points_flat = np.array([
            [x1, x2] for x1 in points[0] for x2 in points[1]
        ], dtype=np.float64)

        # flattened 1D array of point indices as tuples
        # (these are used on the core to map the flat idx index to the 2D point index)
        self._i_points = np.array([
            (i1, i2) for i1 in range(self._shape[0]) for i2 in range(self._shape[1])
        ], dtype=np.int64)



    def _mutate_plot(self, entry, i_point, point, mean, error=None):
        """Mutates datasets for dimension 0 plots and dimension 1 plots"""
        if entry['dimension'] == 1:
            dim1_model = entry['model']
            dim1_scan_end = i_point[1] == self._shape[1] - 1
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
            dim1_model.mutate_plot(i_point=i_point, x=point[1], y=mean, error=None, dim=1)

            # --- End of dimension 1 scan ---
            if dim1_scan_end:

                # --- Fit dimension 1 data ---
                # perform a fit over the dimension 1 data
                fit_performed = False
                try:
                    fit_performed, fit_valid, saved, errormsg = self._fit(entry,
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
                    param, error = self.calculate_dim0(dim1_model)

                    # find the dimension 0 model
                    for entry2 in self._model_registry:
                        if entry2['dimension'] == 0:
                            dim0_model = entry2['model']

                            # mutate the dimension 0 plot
                            dim0_model.mutate_plot(i_point=i_point, x=point[0], y=param, error=error, dim=0)

            # --- Redraw Plots ---
            # tell the current_scan applet to redraw itself
            dim1_model.set('plots.trigger', 1, which='mirror')
            dim1_model.set('plots.trigger', 0, which='mirror')

    def _fit(self, entry, save, use_mirror, dimension, i):
        """Performs fits on dimension 0 and dimension 1"""
        model = entry['model']
        # dimension 1 fits
        if dimension == 1:
            # perform a fit on the completed dim1 plot and mutate the dim0 x/y datasets

            # get the x/y data for the fit on dimension 1
            x_data = model.stat_model.points[i, :, 1]  # these are unsorted
            y_data = model.stat_model.means[i, :]

            # use the errors in the dimension 1 mean values (std dev of mean) as the weights in the fit
            errors = model.stat_model.errors[i, :]

            # default fit arguments
            defaults = {
                'validate': True,
                'set': True,
                'save': False
            }
            guess = None

        # dimension 0 fits
        elif dimension == 0:
            # get the x/y data for the fit on dimension 0
            x_data, y_data, errors = model.get_plot_data(mirror=True)

            # default fit arguments
            defaults = {
                'validate': True,
                'set': True,
                'save': save
            }
            i = None
            guess = self._get_fit_guess(model.fit_function)

        # settings in 'entry' always override default values
        args = {**defaults, **entry}

        # perform the fit
        fit_function = model.fit_function
        validate = args['validate']
        set = args['set']  # save all info about the fit (fitted params, etc) to the 'fits' namespace?
        save = args['save']  # save the main fit to the root namespace?
        return model.fit_data(
            x_data=x_data,
            y_data=y_data,
            errors=errors,
            fit_function=fit_function,
            guess=guess,
            i=i,
            validate=validate,
            set=set,
            save=save,
            man_bounds=model.man_bounds,
            man_scale=model.man_scale
        )

    def _offset_points(self, offset):
        self._points[:, :, 1] += offset
        self._points_flat[:, 1] += offset

    def _write_datasets(self, entry):
        entry['model'].write_datasets(dimension=entry['dimension'])
        entry['datasets_written'] = True

