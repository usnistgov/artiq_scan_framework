from artiq_scan_framework.language import *
from artiq.experiment import *
from .data import *
import numpy as np
from .iter import *
from collections import OrderedDict
from ..loop import Loop


class Loop2D(Loop):
    kernel_invariants = {'nmeasurements'}

    def build(self, scan):
        self.scan = scan
        scan._dim = 2
        scan._i_point = np.array([0, 0], dtype=np.int32)
        self.dtype = np.int32
        self.itr = Iter2D(self, looper=self)

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
            'processor_args': {'default': 100, 'ndecimals': 0, 'step': 1},
            'group': 'Scan Settings',
            'tooltip': None
        }
        return argdef

    def init(self, switch, *args, **kwargs):
        # order of execution:
        # 1. load_points, 2. report, 3. offset_points, 4. init_datasets or write_datasets, 5. init_loop
        def load_points(self):
            #self.scan.print('Loop2D.init.load_points()', 2)
            self.scan._i_pass = np.int32(0)
            self.scan._i_point = np.array([0, 0], dtype=np.int32)

            # points
            points = get_scan_points(self.scan)

            self.itr.load_points(points)

            # self.scan.print(
            #     'itr.shape={0.shape}, itr.plot_shape={0.plot_shape}, itr.nitr={0.niter}, itr.npoints={0.npoints}'.format(
            #         self.itr))

            # warmup points
            warmup_points = self.scan.get_warmup_points()


            # force warmup points to be two-dimensional.  Otherwise, this breaks compilation of the do_measure() method, which initially
            # compiles with a signature that accepts a float argument when self.warmup() is called.  Then, an array is passed to do_measure()
            # in _repeat_loop().  This results in a compilation error since do_measure() was already compiled expecting a single float argument
            # but not an array of floats.
            if not warmup_points:
                # bit of a hack so that the warmup method can compile, otherwise Artiq balks at the dimension of the point argument
                warmup_points = np.full((0, 0), 0.0, dtype=np.float64)
            else:
                _temp = []
                for p in warmup_points:
                    try:
                        # warmup points is a 2D array, and is therefore compatible with do_measure
                        _temp.append([float(p[0]), float(p[1])])
                    # handle cases where warmup points is a 1D array and is therefore not compatible with do_measure
                    except TypeError:
                        _temp.append([float(p), float(p)])
                warmup_points = _temp
            self.warmup_points = warmup_points
            print("self.warmup_points={}".format(self.warmup_points))
            #self.scan.print('Loop2D.init.load_points()', 2)
        def report(self, location='both'):
            #self.scan.print('Loop2D.report(location={})'.format(location))
            if location == 'top' or location == 'both':
                if self.scan.nrepeats == 1:
                    self.scan.logger.info('START {} / {} repeat'.format(self.scan._name, self.scan.nrepeats))
                else:
                    self.scan.logger.info('START {} / {} repeats'.format(self.scan._name, self.scan.nrepeats))
        def offset_points(self, x_offset):
            #self.scan.print('Loop2D.offset_points(x_offset={})'.format(x_offset))
            self.itr.offset_points(x_offset)
        def init_datasets(self, entry):
            #self.scan.print('Loop2D.init.init_datasets(model={}, dimension={})'.format(entry['model'].__class__.__name__, entry['dimension']))

            import pprint
            pp = pprint.PrettyPrinter(indent=4)

            # initialize the model's datasets
            # self.scan.print('{}::init_datasets('.format(entry['model'].__class__.__name__))
            # self.scan.print('   shapes={}'.format(
            #     pp.pformat({
            #         'itr': self.itr.shape,
            #         'plot': self.itr.plot_shape,
            #         'pass_means': (self.scan.npasses, self.itr.shape),
            #         'stats.counts': (self.itr.shape[0], self.itr.shape[1], self.scan.npasses * self.scan.nrepeats),
            #         'stats.hist': (self.itr.shape[0], self.itr.shape[1], self.scan.nbins)
            #     })
            # ))
            # self.scan.print('   points={}'.format(
            #     self.itr.points()
            # ))
            # self.scan.print('   dtype={}'.format(
            #     self.dtype
            # ))
            # self.scan.print('   dimension={})'.format(
            #     entry['dimension']
            # ))

            # initialize the model's datasets
            entry['model'].init_datasets(
                shapes={
                    'itr': self.itr.shape,
                    'plot': self.itr.plot_shape,
                    'pass_means': (self.scan.npasses, self.itr.npoints),
                    'stats.counts': (self.itr.shape[0], self.itr.shape[1], self.scan.npasses * self.scan.nrepeats),
                    'stats.hist': (self.itr.shape[0], self.itr.shape[1], self.scan.nbins)
                },
                points=self.itr.points(),
                dtype=self.dtype,
                dimension=entry['dimension']
            )
        def write_datasets(self, entry):
            model = entry['model']
            dimension = entry['dimension']
            model.write_datasets(dimension=dimension)
        def init_loop(self, ncalcs, measurements):
            self.set_kernel_invariants()
            self.ncalcs = ncalcs
            self.measurements = []
            for i_meas, meas in enumerate(measurements):
                self.measurements.append(meas)
                for entry in get_registered_models(self.scan, measurement=meas):
                    entry['i_meas'] = i_meas
            self.nmeasurements = len(self.measurements)
            self.data = Data(shape=(self.nmeasurements, self.scan.nrepeats),
                             dtype=self.dtype)
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
        self.scan.run_warmup(
            self.warmup_points,
            self.nmeasurements,
            self.measurements
        )

        meas_point = [0.0, 0.0]
        while not self.itr.done(meas_point):
            #self.scan.print('itr: i0={0.i0}, i1={0.i1}, i={0.i}, i_pass={0.i_pass}'.format(self.itr))
            i_point = self.itr.i_point
            i_pass = self.itr.i_pass
            #self.scan._i_pass = i_pass
            #self.scan._i_point = i_point
            #print(self.itr.i)
            if self.scan.enable_pausing:
                check_pause(self.scan)
            if not resume or self.itr.i == 0:
                self.scan.before_pass(i_pass)
            meas_point = self.scan.offset_point(i_point, meas_point)  # user callback
            self.scan.set_scan_point(i_point, meas_point)  # user callback
            self.data.zero_val()
            for i_repeat in range(self.scan.nrepeats):
                for i_meas in range(self.nmeasurements):
                    meas = self.measurements[i_meas]
                    self.scan.before_measure(meas_point, meas)  # user callback
                    self.scan.lab_before_measure(meas_point, meas)  # user callback
                    count = self.scan.do_measure(meas_point)  # call measure
                    self.data.store([i_meas, i_repeat], count)  # store value
                    self.scan.after_measure(meas_point, meas)  # user callback
                    self.scan.lab_after_measure(meas_point, meas)  # user callback
            mean = self.data.mean(self.nmeasurements * self.scan.nrepeats)  # mean value over repeats & meas
            if self.scan.enable_mutate:
                self.mutate_datasets(i_point,  # i_point
                                     i_pass,  # i_pass
                                     self.itr.i_pass * self.scan.nrepeats, #poffset,
                                     meas_point,  # meas_point
                                     self.data.data)  # data
            if self.ncalcs > 0:
                self.scan._calculate_all(i_point, i_pass, meas_point)
            self.scan._analyze_data(i_point, itr=self.itr, data=self.data)  # extension callback (e.g. ReloadingScan)
            self.scan.after_scan_point(i_point, meas_point)  # user callback
            self.scan._after_scan_point(i_point, meas_point, mean)  # user callback
            if self.scan.enable_count_monitor:
                self.set_counts(mean)
            self.itr.step()
        #self.itr.reset()

    @rpc(flags={"async"})
    def set_counts(self, mean, digits=-1):
        if digits >= 0:
            mean = round(mean, digits)
        self.set_dataset('counts', mean, broadcast=True, persist=True)

    @rpc(flags={"async"})
    def mutate_datasets(self, i_point, i_pass, poffset, meas_point, data):
        #self.scan.print('Loop2D::mutate_datasets()', 2)
        model = None
        for entry in get_registered_models(self.scan, measurement=True, dimension=1):   # all subscan models
            model = entry['model']
            #self.scan.print('{}::mutate_datasets(i_point={}, i_pass={}, poffset={}, point={}'.format(
            #    model.__class__.__name__, i_point, i_pass, poffset, meas_point))
            mean, error = model.mutate_datasets(i_point=i_point, i_pass=i_pass,         # mutate stats
                                                poffset=poffset, point=meas_point,
                                                counts=data[entry['i_meas']])
            self.mutate_plot_dim1(entry, i_point=i_point, x=meas_point[1],
                                  y=mean, error=error)                                  # plot subscan
            if self.itr.at_end(i_point, dim=1):                                         # just finshed a subscan
                defaults = {                                                            # default fit arguments
                    'validate': True,
                    'set': True,
                    'save': False
                }
                args = {**defaults, **entry}                                            # settings in 'entry' always override default values
                if self.fit_dim1(model, i_point, validate=args['validate'],
                                 set=args['set'], save=args['save']):                   # fit the subscan

                    y, error = self.scan.calculate_dim0(model)                          # scan value
                    self.mutate_plot_dim0(i_point=i_point, x=meas_point[0],
                                          y=y, error=error)                             # plot scan
        if model:
            trigger_plot(model)
        #self.scan.print('Loop2D::mutate_datasets()', -2)

    def mutate_plot_dim1(self, entry, i_point, x, y, error=None):
        """Plots results from dimension 1 sub-scans"""
        model = entry['model']
        model.set('plots.subplot.i_plot', i_point[0], which='mirror', broadcast=True, persist=True)

        # first store the point & mean to the dim1 plot x/y datasets
        # the value of the fitted parameter is plotted as the y value
        # at the current dimension-0 x value (i.e. x0)
        #self.scan.print('{}::mutate_plot(i_point={}, x={}, y={}, error={}, dim={})'.format(
        #    model.__class__.__name__, i_point, x, y, error, 1
        #))
        model.mutate_plot(i_point=i_point, x=x, y=y, error=None, dim=1)

    def fit_dim1(self, model, i_point, validate, set, save):
        """Performs fits on dimension 1 sub-scans"""
        try:
            #self.scan.print(
            #    '{}::fit_data(fit_function={}, guess={}, i={}, validate={}, set={}, save={}, man_bounds={}, man_scale={})'.format(
            #        model.__class__.__name__, model.fit_function.__name__, None, i_point[0], validate, set, save, model.man_bounds,
            #        model.man_scale
            #    ))
            performed, valid, saved, errormsg = model.fit_data(
                x_data=model.points[i_point[0], :, 1] ,   # these are unsorted,
                y_data=model.means[i_point[0], :],
                errors=model.errors[i_point[0], :],       # use the errors in the dimension 1 mean values (std dev of mean) as the weights in the fit
                fit_function=model.fit_function,
                i="dim1.{}".format(i_point[0]),
                validate=validate,
                set=set,                           # save all info about the fit (fitted params, etc) to the 'fits' namespace?
                save=save,                         # save the main fit to the root namespace?
                man_bounds=model.man_bounds,
                man_scale=model.man_scale
            )

        # handle cases when fit fails to converge so the scan doesn't just halt entirely with an
        # unhandeled error
        except RuntimeError:
            performed = False
            valid = False
            saved = False
            errormsg = 'Runtime Error'
        success = performed and hasattr(model, 'fit')
        if success:
            # -- plot fitline
            # set the fitline to the dimension 1 plot dataset
            model.mutate('plots.dim1.fitline',
                         ((i_point[0], i_point[0] + 1), (0, len(model.fit.fitline))),
                         model.fit.fitline)
            model.mutate('plots.dim1.fitline_fine',
                         ((i_point[0], i_point[0] + 1), (0, len(model.fit.fitline_fine))),
                         model.fit.fitline_fine)
            model.mutate('plots.dim1.x_fine',
                         ((i_point[0], i_point[0] + 1), (0, len(model.fit.fitline_fine))),
                         model.fit.x_fine)
        return success

    def mutate_plot_dim0(self, i_point, x, y, error):
        """Plot the value calculated from the dim1 scan"""
        # -- dim0
        for entry in get_registered_models(self.scan, dimension=0):
            #self.scan.print('{}::mutate_plot(i_point={}, x={}, y={}, error={}, dim={})'.format(
            #    entry['model'].__class__.__name__, i_point[0], x, y, error, 0
            #))
            entry['model'].mutate_plot(i_point=i_point, x=x, y=y, error=error, dim=0)

    def fit(self, entry, save, use_mirror, dimension, i):
        """Performs fit on dimension 0 top level scan"""
        model = entry['model']
        x_data, y_data, errors = model.get_plot_data(mirror=True)       # get the x/y data for the fit on dimension 0
        defaults = {                                                    # default fit arguments
            'validate': True,
            'set': True,
            'save': save
        }
        args = {**defaults, **entry}                                    # settings in 'entry' always override default values
        return model.fit_data(                                          # perform the fit
            x_data=x_data,
            y_data=y_data,
            errors=errors,
            fit_function=model.fit_function,
            guess=self.scan.fit_arguments.guesses(model.fit_function),
            hold=self.scan.fit_arguments.holds(model.fit_function),
            i=None,
            validate=args['validate'],
            set=args['set'],  # save all info about the fit (fitted params, etc) to the 'fits' namespace?
            save=args['save'],  # save the main fit to the root namespace?
            man_bounds=model.man_bounds,
            man_scale=model.man_scale
        )