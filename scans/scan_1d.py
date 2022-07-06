from .scan import *


class Scan1D(Scan):
    """Extension of the :class:`~artiq_scan_framework.scans.scan.Scan` class for 1D scans.  All 1D scans should inherit from
    this class."""

    def __init__(self, managers_or_parent, *args, **kwargs):
        super().__init__(managers_or_parent, *args, **kwargs)
        self._dim = 1
        self._i_point = np.int64(0)

    def _load_points(self):
        # grab the points
        if self._points is None:
            points = list(self.get_scan_points())
        else:
            points = list(self._points)

        # warmup points
        if self._warmup_points is None:
            warmup_points = self.get_warmup_points()
        else:
            warmup_points = list(self._warmup_points)
        warmup_points = [p for p in warmup_points]

        # this turn's ARTIQ scan arguments into lists
        points = [p for p in points]

        # total number of scan points
        self.npoints = np.int32(len(points))
        self.nwarmup_points = np.int32(len(warmup_points))

        # initialize shapes (these are the authority on data structure sizes)...

        # shape of the stats.counts dataset
        self._shape = np.int32(self.npoints)

        # shape of the plots.x, plots.y, and plots.fitline datasets
        if self._plot_shape is None:
            self._plot_shape = np.int32(self.npoints)

        # initialize 1D data structures...

        # 1D array of scan points (these are saved to the stats.points dataset)
        self._points = np.array(points, dtype=np.float64)

        # flattened 1D array of scan points (these are looped over on the core)
        self._points_flat = np.array(points, dtype=np.float64)
        if self.nwarmup_points:
            self._warmup_points = np.array(warmup_points, dtype=np.float64)
        else:
            self._warmup_points = np.array([0],dtype=np.float64)


        # flattened 1D array of point indices as tuples
        # (these are used on the core to map the flat idx index to the 2D point index)
        self._i_points = np.array(range(self.npoints), dtype=np.int64)

    def _mutate_plot(self, entry, i_point, point, mean, error=None):
        model = entry['model']

        # mutate plot x/y datasets
        model.mutate_plot(i_point=i_point, x=point, y=mean, error=error)

        # tell the current_scan applet to redraw itself
        model.set('plots.trigger', 1, which='mirror')
        model.set('plots.trigger', 0, which='mirror')

    def _fit(self, entry, save, use_mirror, dimension, i):
        """Perform the fit"""

        model = entry['model']
        x_data, y_data = model.get_fit_data(use_mirror)

        # for validation methods
        self.min_point = min(x_data)
        self.max_point = max(x_data)

        errors = model.stat_model.get('error', mirror=use_mirror)
        fit_function = model.fit_function

        guess = self._get_fit_guess(fit_function)

        return model.fit_data(
            x_data=x_data,
            y_data=y_data,
            errors=errors,
            fit_function=fit_function,
            guess=guess,
            validate=True,
            set=True,  # keep a record of the fit
            save=save,  # save the main fit to the root namespace?
            man_bounds=model.man_bounds,
            man_scale=model.man_scale
            )

    def _offset_points(self, x_offset):
        if x_offset is not None:
            self._points += x_offset
            self._points_flat += x_offset

    def _write_datasets(self, entry):
        entry['model'].write_datasets(dimension=0)
        entry['datasets_written'] = True
