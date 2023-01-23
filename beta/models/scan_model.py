from artiq_scan_framework.models.scan_model import *


class BetaScanModel(ScanModel):

    def report(self):
        """Generate a report string that displays the values of the stat datasets."""
        str = ""
        for key in ['bins', 'counts', 'error', 'hist', 'mean', 'nbins']:
            v = self.get("stats.{}".format(key)).items()
            str += "[{0}]\n {1}\n\n".format(key, v)
        for k, v in self.get(['points']).items():
            str += "[{0}]\n {1}\n\n".format(k, v)
        return str

    def build(self, bind=True, **kwargs):

        # don't bind the child model's to their namespaces yet since our namespace hasn't been set.
        self.fit_model = Model(self,
                               bind=False,
                               mirror=self.mirror,
                               mirror_namespace=self.mirror_namespace,
                               broadcast=self.broadcast,
                               persist=self.persist,
                               save=self.save
                               )
        # for monitoring histograms of each scan point
        if self.enable_histograms:
            self.hist_model = HistModel(self,
                                        bind=False,
                                        discrete=True,
                                        aggregate=True,
                                        mirror=self.mirror,
                                        x_label="PMT Counts",
                                        broadcast=self.broadcast,
                                        persist=self.persist,
                                        save=self.save
                                        )

        self.defaults_model = Model(self,
                                    bind=False,
                                    mirror=False)

        # bind the scan model and it's child models to their namespaces
        super().build(bind, **kwargs)

        # create a logger and reset the model state.
        self._name = self.__class__.__name__
        self.logger = logging.getLogger("")
        self.reset_state()
        self._fit_saved = False

    @property
    def nrepeats(self):
        return self._scan.nrepeats

    @property
    def nbins(self):
        return self._scan.nbins

    @property
    def npasses(self):
        return self._scan.npasses

    def simulate(self, x, simulation_args = None):
        if simulation_args is None and hasattr(self, 'simulation_args'):
            #try:
            simulation_args = self.simulation_args
            #except(NotImplementedError):
            #    simulation_args = self.fit_function.simulation_args()
        lam = self.fit_function.value(x, **simulation_args)

        return int(np.random.poisson(lam, 1)[0])
        # # convert expectation value to quantized value
        # f = floor(value)
        # c = ceil(value)
        # if np.random.random() > (value - f):
        #     value = f
        # else:
        #     value = c
        #
        # noise = (2.0 * np.random.random() - 1.0) * noise_level
        # return int(abs(value + noise))

    def bind(self):
        """Bind the scan model to it's namespace and additional sub-spaces for fits, stats, hists, and defaults."""

        # map and bind the scan model namespace first because child models extend off of our namespace
        super().bind()

        # now bind the child models to their namespaces
        self.fit_model._namespace = self.namespace + '.fits'
        self.fit_model._mirror_namespace = self.mirror_namespace + '.fits'
        self.fit_model.bind()
        if self.enable_histograms:
            self.hist_model.namespace = self.namespace + '.hist'
            self.hist_model.mirror_namespace = 'current_hist'
            self.hist_model.plot_title = self.plot_title
            self.hist_model.bind()
        self.defaults_model.namespace = self.namespace + '.defaults'
        self.defaults_model.bind()

    def attach(self, scan):
        """ Attach a scan to the model.  Gather's parameters of the scan -- such as scan.nrepeats, scan.npasses,
        etc. --  and sets these as attributes of the model.  """
        self._scan = scan
        self.bins = np.linspace(-0.5, self.nbins - 0.5, self.nbins + 1)
        if self.enable_histograms:
            if self.bin_end == 'auto' or self.bin_end == None:
                bin_end = self.nbins - 1
            else:
                bin_end = self.bin_end
            self.hist_model.init_bins(bin_start=self.bin_start, bin_end=bin_end, nbins=self.nbins)

    def init_datasets(self, shapes, points, dtype, dimension=0):
        """Initializes all datasets pertaining to scans.  This method is called by the scan during the initialization
        stage."""
        self.set('class_name', self._scan.__class__.__name__, which='mirror')
        self.shape = shapes['itr']
        self.plot_shape = shapes['plot']
        # allow below to work on either 1d or 2d scans
        if self._scan._dim == 1:
            shape = np.array([shapes['itr']])
        else:
            shape = shapes['itr']
        shape = list(shape)

        # set experiment rid
        if not (hasattr(self._scan, 'scheduler')):
            raise NotImplementedError('The scan has no scheduler attribute.  Did you forget to call super().build()?')
        self.set('rid', self._scan.scheduler.rid)

        # don't draw plots while initializing
        self.set('plots.trigger', 0)

        # initialize scan points
        self.set('stats.points', points)
        self.points = points

        # initialize plots
        self._init_plots(dimension=dimension)
        # initialize stats
        if 'stats.counts' in shapes:
            self.init('stats.counts', varname='counts', shape=shapes['stats.counts'], fill_value=0, dtype=dtype)
        self.init(key='stats.mean', shape=shape, varname='means')
        if 'pass_means' in shapes:
            self.init(key='stats.pass_means', shape=shapes['pass_means'], varname='pass_means')
        self.init('stats.error', shape, varname='errors')
        if self.enable_histograms:
            self.write('stats.nbins', varname='nbins')
            self.write('stats.bins', varname='bins')
            if 'stats.hist' in shapes:
                self.init('stats.hist', varname='hist', shape=shapes['stats.hist'], fill_value=0, dtype=dtype)
            self.hist_model.init_datasets(broadcast=self.broadcast, persist=self.persist, save=self.save)

        # initialize fits
        self.fit_model.init('fitline', shapes['plot'])
        self.fit_model.init('fitline_fine', shapes['plot'])
        self.fit_model.init('fitline_fine_nn', shapes['plot'])
        self.fit_model.init('x_fine', shapes['plot'])
        self.fit_model.set('fit_performed', None)
        self.fit_model.set('fit_valid', None)
        self.fit_model.set('fit_saved', None)
        self.fit_model.set('fit_errormsg', None)

    def init_plots(self, shape, shape_fine, plot_title="", x_label="", x_scale=1, x_units="", y_label="", y_scale=1, y_units=""):
        # data
        self.init('plots.x', shape, varname='x', init_local=True)
        self.init('plots.y', shape, varname='y', init_local=True)
        self.init('plots.y2', shape, varname='y2', init_local=True)
        self.init('plots.fitline', shape, varname='fitline', init_local=True)
        self.init('plots.fitline_fine', shape_fine, varname='fitline_fine', init_local=True)
        self.init('plots.fitline_fine_nn', shape_fine, varname='fitline_fine_nn', init_local=True)
        self.init('plots.x_fine', shape_fine, varname='x_fine', init_local=True)
        self.init('plots.error', shape, init_local=False)

        # labels, etc.
        self.set('plots.plot_title', plot_title)
        self.set('plots.y_label', y_label)
        self.set('plots.x_label', x_label)
        self.set('plots.x_scale', x_scale)
        self.set('plots.y_scale', y_scale)
        self.set('plots.x_units', x_units)
        self.set('plots.y_units', y_units)

    def init_sub_plots(self, shape, shape_fine, plot_title="", x_label="", x_scale=1, x_units="", y_label="", y_scale=1, y_units=""):
        # data
        self.init('plots.dim1.x', shape, varname='dim1_x', init_local=True)
        self.init('plots.dim1.y', shape, varname='dim1_y', init_local=True)
        self.init('plots.dim1.fitline', shape, varname='dim1_fitline', init_local=True)
        self.init('plots.dim1.fitline_fine', shape_fine, varname='dim1_fitline_fine', init_local=True)
        self.init('plots.dim1.fitline_fine_nn', shape_fine, varname='dim1_fitline_fine_nn', init_local=True)
        self.init('plots.dim1.x_fine', shape_fine, varname='dim1_x_fine', init_local=True)

        # labels, etc.
        self.set('plots.dim1.plot_title', plot_title)
        self.set('plots.dim1.y_label', y_label)
        self.set('plots.dim1.x_label', x_label)
        self.set('plots.dim1.x_scale', x_scale)
        self.set('plots.dim1.x_scale', y_scale)
        self.set('plots.dim1.x_units', x_units)
        self.set('plots.dim1.y_units', y_units)

    def set_plots(self, x, y, which='both', fit=None):
        self.set('plots.x', x, which=which)
        self.set('plots.y', y, which=which)
        if fit is not None:
            self.set_fitline(fit=fit, which=which)

    def set_fitline(self, fit, which='both'):
        self.set('plots.fitline', fit.fitline, which=which)
        self.set('plots.fitline_fine', fit.fitline_fine, which=which)
        self.set('plots.fitline_fine_nn', fit.fitline_fine_nn, which=which)
        self.set('plots.x_fine', fit.x_fine, which=which)

    def set_sub_plots(self, x, y, which='both', fit=None):
        self.set('plots.dim1.x', x, which=which)
        self.set('plots.dim1.y', y, which=which)
        if fit is not None:
            self.set('plots.dim1.fitline', fit.fitline, which=which)
            self.set('plots.dim1.fitline_fine', fit.fitline_fine, which=which)
            self.set('plots.dim1.fitline_fine_nn', fit.fitline_fine_nn, which=which)
            self.set('plots.dim1.x_fine', fit.x_fine, which=which)

    def write_datasets(self, dimension):
        """Writes all internal values to their datasets.  This method is called by the scan when it is resuming from a
         pause to restore previous scan values to their datasets."""

        # don't draw plots while writing
        self.set('plots.trigger', 0)

        if dimension == 0:

            # write scan points
            self.write('stats.points', varname='points')
            # self.write('x', 'x')

            # write plots
            self.write_plots()

            # write stats
            self.write('stats.counts', varname='counts')
            self.write('stats.mean', varname='means')
            self.write('stats.pass_means', varname='pass_means')
            self.write('stats.error', varname='errors')

            if self.enable_histograms:
                self.write('stats.nbins', varname='nbins')
                self.write('stats.bins', varname='bins')
                self.write('stats.hist', varname='hist')
                self.hist_model.init_datasets()

        elif dimension is 1:
            # write scan points
            # self.write('x', 'x')

            # write plots
            self.write_sub_plots()

        # draw plots when done writting
        self.set('plots.trigger', 1)

    def write_plots(self):
        self.write('plots.x', varname='x')
        self.write('plots.y', varname='y')
        self.write('plots.fitline', varname='fitline')
        self.write('plots.fitline_fine', varname='fitline_fine')
        self.write('plots.fitline_fine_nn', varname='fitline_fine_nn')
        self.write('plots.x_fine', varname='x_fine')
        self.set('plots.plot_title', self.plot_title)
        self.set('plots.y_label', self.y_label)
        self.set('plots.x_label', self.x_label)
        self.set('plots.x_scale', self.x_scale)
        self.set('plots.y_scale', self.y_scale)
        self.set('plots.x_units', self.x_units)
        self.set('plots.y_units', self.y_units)

    def write_sub_plots(self):
        self.write('plots.dim1.x', varname='dim1_x')
        self.write('plots.dim1.y', varname='dim1_y')
        self.write('plots.dim1.fitline', varname='dim1_fitline')
        self.write('plots.dim1.fitline_fine', varname='dim1_fitline_fine')
        self.write('plots.dim1.fitline_fine_nn', varname='dim1_fitline_fine_nn')
        self.write('plots.dim1.x_fine', varname='dim1_x_fine')
        self.set('plots.dim1.plot_title', self.plot_title)
        self.set('plots.dim1.y_label', self.y_label)
        self.set('plots.dim1.x_label', self.x_label)
        self.set('plots.dim1.x_scale', self.x_scale)
        self.set('plots.dim1.y_scale', self.y_scale)
        self.set('plots.dim1.x_units', self.x_units)
        self.set('plots.dim1.y_units', self.y_units)

    def mutate_datasets(self, i_point, i_pass, poffset, point, counts):
        """Generates the mean and standard error of the mean for the measured value at the specified scan point
        and mutates the corresponding datasets.  The `points` and `counts` datasets are also mutated with the
        specified scan point value and raw values measured at the specified scan point.  If histograms are enabled,
        each measured value in `counts` will also be binned and the histogram datasets will be mutated with the
        binned values to updated the histogram plots.

        :param i_point: scan point index
        :param poffset: index of start of measurements for this pass. If all data submitted together poffset=0
        :param point: value of scan point
        :param counts: array containing all values returned by the scan's measure() method during the specified
                       scan point
        """
        dim = self._scan._dim
        # mutate the dataset containing the scan point values
        self.mutate_points(i_point, point)  # TODO this shouldn't need to be called every time, does this slow down the rpc?
        counts = list(counts)
        # mutate the dataset containing the array of counts measured at each repetition of the scan point
        if dim == 1:
            # mutate the counts dataset with counts at point i_point,poffset:poffset+len(counts)
            i = ((i_point, i_point + 1), (poffset, poffset + len(counts)))
            self.mutate('stats.counts', i, counts, update_local=False)

            # mutate the local counts array (so it can be written when a scan resumes)
            self.counts[i_point, poffset:poffset + len(counts)] = counts

            # resize counts to full filled local array for statistics modeling
            counts = self.counts[i_point, 0:poffset + len(counts)]
        else:
            # mutate the 2D counts dataset with counts at point i_point[0],i_point[1],poffset:poffset+len(counts)
            i = ((i_point[0], i_point[0] + 1), (i_point[1], i_point[1] + 1), (poffset, poffset + len(counts)))
            self.mutate('stats.counts', i, counts, update_local=False)

            # mutate the local counts array (so it can be written when a scan resumes)
            self.counts[i_point[0], i_point[1], poffset:poffset + len(counts)] = counts

            # resize counts to full filled local array for statistics modeling
            counts = self.counts[i_point[0], i_point[1], 0:poffset + len(counts)]
        # calculate the mean
        mean, pass_mean = self._calc_mean(counts, i_pass)

        # mutate the dataset containing the mean values at each scan point
        self.mutate_means(i_point, i_pass, mean, pass_mean)

        # calculate the error
        error = self.calc_error(counts)

        # mutate the dataset containing the error in the mean at each scan point
        self.mutate_errors(i_point, error)

        # histograms
        if self.enable_histograms:

            # bin counts and mutate the histogram at the current scan point
            self.hist_model.reset_bins()
            self.hist_model.mutate(counts)

            # mutate the time series histograms
            if dim == 1:
                # mutate the hist dataset
                if hasattr(self, 'hist'):
                    self.mutate('stats.hist', i_point, self.hist_model.bins, update_local=False)

                    # mutate the local hist array
                    self.hist[i_point] = self.hist_model.bins
            else:
                # mutate the hist dataset
                i = ((i_point[0], i_point[0] + 1), (i_point[1], i_point[1] + 1))
                self.mutate('stats.hist', i, self.hist_model.bins, update_local=False)

                # mutate the local hist array
                self.hist[i_point[0], i_point[1]] = self.hist_model.bins

        return mean, error

    def mutate_points(self, i_point, point):
        """Mutate the 'points' dataset with the value of a scan point

        :param i_point: index of the scan point
        :param point: value of the scan point
        """
        dim = self._scan._dim
        if dim == 1:
            i = i_point
            self.mutate('stats.points', i, point)
            self.points[i] = point
        else:
            i = ((i_point[0], i_point[0] + 1), (i_point[1], i_point[1] + 1))
            self.mutate('stats.points', i, point, update_local=False)
            self.points[i_point[0], i_point[1]] = point

    def mutate_means(self, i_point, i_pass, mean, pass_mean=None):
        """"Mutate the 'means' dataset with a mean value calculated at the specified scan point

        :param i_point: index of the scan point
        :param mean: mean of the measured value at the given scan point
        """
        dim = self._scan._dim
        if dim == 1:
            # mutate the mean dataset
            self.mutate('stats.mean', i_point, mean, update_local=False)

            # mutate the stats.mean dataset
            if self.generate_pass_means and pass_mean is not None:
                self.mutate('stats.pass_means', ((i_pass, i_pass + 1), (i_point, i_point + 1)), pass_mean, update_local=False)

            # mutate local means array
            self.means[i_point] = mean
        else:
            # mutate the mean dataset
            i = ((i_point[0], i_point[0] + 1), (i_point[1], i_point[1] + 1))
            self.mutate('stats.mean', i, mean, update_local=False)

            # mutate local means array
            self.means[i_point[0], i_point[1]] = mean

    def mutate_errors(self, i_point, error):
        """"Mutate the 'error' dataset with the error in the mean value calculated at the specified scan point

        :param i_point: index of the scan point
        :param error: error in the mean measured value at the given scan point
        """
        dim = self._scan._dim
        if dim == 1:
            # mutate the error dataset
            i = i_point
            self.mutate('stats.error', i, error, update_local=False)

            # mutate the local errors array
            self.errors[i_point] = error
        else:
            # mutate the error dataset
            i = ((i_point[0], i_point[0] + 1), (i_point[1], i_point[1] + 1))
            self.mutate('stats.error', i, error, update_local=False)

            # mutate the local errors array
            self.errors[i_point[0], i_point[1]] = error

    def get_means(self, default=NoDefault, mirror=False):
        """Fetches from the datasets and returns the mean values measured at each scan point.  i.e. the
        'means' dataset """
        return self.get('stats.mean', default, mirror)

    def get_means_key(self, mirror=False):
        """Returns the dataset key of the 'means' dataset"""
        return self.key('stats.mean', mirror)

    # [loaders]
    def load_counts(self):
        """Loads the internal counts variable from its dataset"""
        self.load('stats.counts')

    def load_xs(self):
        """Loads the internal xs variable from its dataset"""
        self.load('stats.x', 'xs')

    def load_errors(self):
        """Loads the internal errors variable from its dataset"""
        self.load('stats.error', 'errors')

    def load_means(self):
        """Loads the internal means variable from its dataset"""
        self.load('stats.mean', 'means')

    def _calc_mean(self, counts, i_pass):
        """Calculate mean value of counts.

        :param counts: Array of counts"""
        return np.nanmean(counts), np.nanmean(counts[i_pass * self.nrepeats:(i_pass + 1) * self.nrepeats])


    def get_fit_data(self, use_mirror):
        """Helper method.  Returns the experimental data to use for fitting."""
        x_data = self.get('stats.points', mirror=use_mirror)
        y_data = self.get('stats.mean', mirror=use_mirror)
        return x_data, y_data

