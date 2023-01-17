from artiq_scan_framework.beta.loop import *
from artiq_scan_framework.beta.snippets import *
from artiq_scan_framework.beta.data import *
import numpy as np
from .iter import *


class Loop2D(Loop):
    kernel_invariants = {'nrepeats', 'npoints', 'nmeasurements'}

    def build(self, scan, npasses, nrepeats):
        self.scan = scan
        scan._dim = 2
        scan._i_point = np.array([0, 0], dtype=np.int32)
        self.dtype = np.int32
        self.nrepeats = nrepeats
        self.itr = Iter2D(self, npasses=npasses, nrepeats=nrepeats)

    def init(self, switch, *args, **kwargs): #nmeasurements, ncalcs, measurements):
        def report(self, location='both'):
            self.scan.print('Loop2D.report(location={})'.format(location))
            if location == 'top' or location == 'both':
                if self.nrepeats == 1:
                    self.scan.logger.info('START {} / {} repeat'.format(self.scan._name, self.nrepeats))
                else:
                    self.scan.logger.info('START {} / {} repeats'.format(self.scan._name, self.nrepeats))
        def load_points(self):
            # points
            points = get_points(self.scan)
            self.itr.set_points(points)
            self.scan.print(
                'itr.shape={0.shape}, itr.plot_shape={0.plot_shape}, itr.nitr={0.niter}, itr.npoints={0.npoints}'.format(
                    self.itr))

            # warmup points
            warmup_points = get_warmup_points(self.scan)

            # force warmup points to be two dimensional.  Otherwise this breaks compilation of the do_measure() method, which initially
            # compiles with a signature that accepts a float argument when self.warmup() is called.  Then, an array is passed to do_measure()
            # in _repeat_loop().  This results in a compilation error since do_measure() was already compiled expecting a single float argument
            # but not an array of floats.
            if not warmup_points:
                # bit of a hack so that the warmup method can compile, otherwise Artiq balks at the dimension of the point argument
                warmup_points = np.array([[]], dtype=np.float64)
                nwarmup_points = 0
            else:
                _temp = []
                for p in warmup_points:
                    try:
                        # warmup points is a 2D array, and is therefore compatible with do_measure
                        _temp.append([p[0], p[1]])
                    # handle cases where warmup points is a 1D array and is therefore not compatible with do_measure
                    except TypeError:
                        _temp.append([p])
                nwarmup_points = np.int32(len(_temp))
                warmup_points = np.array(_temp, dtype=np.float64)
            self.warmup_points = warmup_points
            self.nwarmup_points = nwarmup_points
        def offset_points(self, x_offset):
            self.scan.print('Loop2D.offset_points(x_offset={})'.format(x_offset))
            self.itr.offset_points(x_offset)
        def init_datasets(self, model, dimension):
            # initialize the model's datasets
            self.scan.print('{0}::init_datasets(shape={1.shape}, plot_shape={1.plot_shape}, dimension={2})'.format(
                model.__class__.__name__, self.itr, dimension))
            model.init_datasets(
                shape=self.itr.shape,
                plot_shape=self.itr.plot_shape,
                points=self.itr.points(),
                dimension=dimension
            )
        def write_datasets(self, model, dimension):
            model.write_datasets(dimension=dimension)
        def init(self, nmeasurements, ncalcs, measurements):
            self.measurements = measurements
            self.ncalcs = ncalcs
            self.nmeasurements = nmeasurements
            self.measurements = []
            for i_meas, meas in enumerate(self.scan.measurements):
                self.measurements.append(meas)
                for entry in get_registered_models(self.scan, measurement=meas):
                    entry['i_meas'] = i_meas
            self.data = Data(shape=(nmeasurements, self.nrepeats),
                             dtype=self.dtype)

        if switch == 'report':
            return report(self, *args, **kwargs)
        elif switch == 'load_points':
            return load_points(self, *args, **kwargs)
        elif switch == 'offset_points':
            return offset_points(self, *args, **kwargs)
        elif switch == 'init_datasets':
            return init_datasets(self, *args, **kwargs)
        elif switch == 'write_datasets':
            return write_datasets(self, *args, **kwargs)
        elif switch == 'init':
            return init(self, *args, **kwargs)

    @portable
    def loop(self, resume=False):
        self.scan.run_warmup(
            self.nwarmup_points,
            self.warmup_points,
            self.nmeasurements,
            self.measurements
        )

        meas_point = [0.0, 0.0]
        while not self.itr.done(meas_point):
            self.scan.print('itr: i0={0.i0}, i1={0.i1}, i={0.i}, i_pass={0.i_pass}'.format(self.itr))
            i_point = self.itr.i_point
            i_pass = self.itr.i_pass
            self.scan._i_pass = i_pass
            self.scan._i_point = i_point

            if self.scan.enable_pausing:
                check_pause(self.scan)
            if not resume or self.itr.i == 0:
                self.scan.before_pass(i_pass)
            meas_point = self.scan.offset_point(i_point, meas_point)  # user callback
            self.scan.set_scan_point(i_point, meas_point)  # user callback
            self.data.zero_val()
            for i_repeat in range(self.itr.nrepeats):
                for i_meas in range(self.nmeasurements):
                    meas = self.measurements[i_meas]
                    self.measurement = meas
                    self.scan.before_measure(meas_point, meas)  # user callback
                    self.scan.lab_before_measure(meas_point, meas)  # user callback
                    count = self.scan.do_measure(meas_point)  # call measure
                    self.data.store([i_meas, i_repeat], count)  # store value
                    self.scan.after_measure(meas_point, meas)  # user callback
                    self.scan.lab_after_measure(meas_point, meas)  # user callback
            mean = self.data.mean(self.nmeasurements * self.nrepeats)  # mean value over repeats & meas
            if self.scan.enable_mutate:
                self.mutate_datasets(i_point=i_point,
                                     i_pass=i_pass,
                                     poffset=self.itr.poffset(),
                                     meas_point=meas_point,
                                     data=self.data.data)
            if self.ncalcs > 0:
                self.scan._calculate_all(i_point, i_pass, meas_point)
            for comp in self.scan.components:
                comp.analyze(
                    i_point=i_point,
                    last_itr=self.itr.last_itr(),
                    data=self.data.data
                )  # component hook
            self.scan.after_scan_point(i_point, meas_point)  # user callback
            self.scan._after_scan_point(i_point, meas_point, mean)  # user callback
            if self.scan.enable_count_monitor:
                set_counts(self, mean)
            self.itr.step()
        self.itr.reset()

    @rpc(flags={"async"})
    def mutate_datasets(self, i_point, i_pass, poffset, meas_point, data):
        self.scan.print('call: Loop2D::mutate_datasets()', 2)
        for entry in get_registered_models(self.scan, measurement=True, dimension=1):   # all subscan models
            model = entry['model']
            self.scan.print('{}::mutate_datasets(i_point={}, i_pass={}, poffset={}, point={}'.format(
                model.__class__.__name__, i_point, i_pass, poffset, meas_point))
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
                    self.mutate_plot_dim0(i_point=i_point, x=i_point[0],
                                          y=y, error=error)                             # plot scan
            trigger_plot(model)
        self.scan.print('return: Loop2D::mutate_datasets()', -2)

    def mutate_plot_dim1(self, entry, i_point, x, y, error=None):
        """Plots results from dimension 1 sub-scans"""
        model = entry['model']
        model.set('plots.subplot.i_plot', i_point[0], which='mirror', broadcast=True, persist=True)

        # first store the point & mean to the dim1 plot x/y datasets
        # the value of the fitted parameter is plotted as the y value
        # at the current dimension-0 x value (i.e. x0)
        self.scan.print('{}::mutate_plot(i_point={}, x={}, y={}, error={}, dim={})'.format(
            model.__class__.__name__, i_point, x, y, error, 1
        ))
        model.mutate_plot(i_point=i_point, x=x, y=y, error=None, dim=1)

    def fit_dim1(self, model, i_point, validate, set, save):
        """Performs fits on dimension 1 sub-scans"""
        try:
            self.scan.print(
                '{}::fit_data(fit_function={}, guess={}, i={}, validate={}, set={}, save={}, man_bounds={}, man_scale={})'.format(
                    model.__class__.__name__, model.fit_function.__name__, None, i_point[0], validate, set, save, model.man_bounds,
                    model.man_scale
                ))
            performed, valid, saved, errormsg = model.fit_data(
                x_data=model.stat_model.points[i_point[0], :, 1] ,   # these are unsorted,
                y_data=model.stat_model.means[i_point[0], :],
                errors=model.stat_model.errors[i_point[0], :],       # use the errors in the dimension 1 mean values (std dev of mean) as the weights in the fit
                fit_function=model.fit_function,
                guess=None,
                i=i_point[0],
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
            self.scan.print('{}::mutate_plot(i_point={}, x={}, y={}, error={}, dim={})'.format(
                entry['model'].__class__.__name__, i_point[0], x, y, error, 0
            ))
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
        self.scan.print('{}::fit_data(fit_function={}, guess={}, i={}, validate={}, set={}, save={}, man_bounds={}, man_scale={})'.format(
            model.__class__.__name__, model.fit_function.__name__, self.scan._get_fit_guess(model.fit_function), None, args['validate'], args['set'], args['save'], model.man_bounds, model.man_scale
        ))
        return model.fit_data(                                          # perform the fit
            x_data=x_data,
            y_data=y_data,
            errors=errors,
            fit_function=model.fit_function,
            guess=self.scan._get_fit_guess(model.fit_function),
            i=None,
            validate=args['validate'],
            set=args['set'],  # save all info about the fit (fitted params, etc) to the 'fits' namespace?
            save=args['save'],  # save the main fit to the root namespace?
            man_bounds=model.man_bounds,
            man_scale=model.man_scale
        )