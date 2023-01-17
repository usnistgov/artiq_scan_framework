from artiq_scan_framework.beta.loop import *
from artiq_scan_framework.beta.snippets import *
from artiq_scan_framework.beta.data import *
import numpy as np
from .iter import *


class Loop1D(Loop):
    kernel_invariants = {'nrepeats', 'npoints', 'nmeasurements'}

    def build(self, scan, npasses, nrepeats):
        self.scan = scan
        scan._dim = 1
        scan._i_point = np.int32(0)
        self.dtype = np.int32
        self.nrepeats = nrepeats
        self.itr = Iter1D(self, npasses=npasses, nrepeats=nrepeats)

    def init(self, switch, *args, **kwargs): #nmeasurements, ncalcs, measurements):
        def report(self, location='both'):
            self.scan.print('call: Loop1D.report(location={})'.format(location))
            if location == 'top' or location == 'both':
                if self.nrepeats == 1:
                    self.scan.logger.info('START {} / {} repeat'.format(self.scan._name, self.nrepeats))
                else:
                    self.scan.logger.info('START {} / {} repeats'.format(self.scan._name, self.nrepeats))
        def load_points(self):
            # scan points
            points = get_points(self.scan)
            self.itr.set_points(points)
            self.npoints = len(points)

            # warmup points
            warmup_points = get_warmup_points(self.scan)
            warmup_points = [p for p in warmup_points]
            nwarmup_points = np.int32(len(warmup_points))
            if not nwarmup_points:
                warmup_points = [0]
            warmup_points = np.array(warmup_points, dtype=np.float64)
            self.warmup_points = warmup_points
            self.nwarmup_points = nwarmup_points
        def offset_points(self, x_offset):
            self.scan.print('Loop1D.offset_points(x_offset=)'.format(x_offset))
            self.itr.offset_points(x_offset)
        def init_datasets(self, model, dimension):
            self.scan.print('Loop1D.init_datasets(model={}, dimension={})'.format(model.__class__.__name__, dimension))
            # initialize the model's datasets
            self.scan.print('{}::init_datasets(shape={}, plot_shape={}, points={}, dimension={})'.format(
                model.__class__.__name__,
                self.itr.shape,
                self.itr.plot_shape,
                self.itr.points,
                dimension
            ))
            model.init_datasets(
                shape=self.itr.shape,
                plot_shape=self.itr.plot_shape,
                points=self.itr.points,
                dimension=dimension
            )
        def write_datasets(self, model):
            self.scan.print('Loop1D.write_datasets(model={})'.format(model.__class__.__name__))
            model.write_datasets(dimension=0)
        def init(self, nmeasurements, ncalcs, measurements):
            self.measurements = measurements
            self.ncalcs = ncalcs
            self.nmeasurements = nmeasurements
            self.measurements = []
            for m in self.scan.measurements:
                self.measurements.append(m)
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

        ret = [0.0]
        while not self.itr.done(ret):
            i_point = self.itr.i_point
            i_pass = self.itr.i_pass
            self.scan._i_pass = i_pass
            self.scan._i_point = i_point
            meas_point = ret[0]
            if self.scan.enable_pausing:
                check_pause(self.scan)
            if not resume or self.itr.i == 0:
                self.scan.before_pass(i_pass)
            meas_point = self.scan.offset_point(i_point, meas_point)     # user callback
            self.scan.set_scan_point(i_point, meas_point)                # user callback
            self.data.zero_val()
            for i_repeat in range(self.itr.nrepeats):
                for i_meas in range(self.nmeasurements):
                    meas = self.measurements[i_meas]
                    self.measurement = meas
                    self.scan.before_measure(meas_point, meas)                    # user callback
                    self.scan.lab_before_measure(meas_point, meas)                # user callback
                    count = self.scan.do_measure(meas_point)                      # call measure
                    self.data.store([i_meas, i_repeat], count)                    # store value
                    self.scan.after_measure(meas_point, meas)                     # user callback
                    self.scan.lab_after_measure(meas_point, meas)                 # user callback
            mean = self.data.mean(self.nmeasurements * self.nrepeats)             # mean value over repeats & meas
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
                )                                                                  # component hook
            self.scan.after_scan_point(i_point, meas_point)                        # user callback
            self.scan._after_scan_point(i_point, meas_point, mean)                 # user callback
            if self.scan.enable_count_monitor:
                set_counts(self, mean)
            self.itr.step()
        self.itr.reset()

    @rpc(flags={"async"})
    def mutate_datasets(self, i_point, i_pass, poffset, meas_point, data):
        self.scan.print('call: Loop1D::mutate_datasets()', 2)
        for i_meas, meas in enumerate(self.measurements):
            for entry in get_registered_models(self.scan, meas):
                model = entry['model']
                # mutate stats
                self.scan.print('{}::mutate_datasets(i_point={}, i_pass={}, poffset={}, point={}'.format(
                    model.__class__.__name__, i_point, i_pass, poffset, meas_point))
                mean, error = model.mutate_datasets(
                    i_point=i_point,
                    i_pass=i_pass,
                    poffset=poffset,
                    point=meas_point,
                    counts=data[i_meas],
                )
                # mutate plot x/y datasets
                self.mutate_plot(model, i_point=i_point, x=meas_point, y=mean, error=error, trigger=False)

        # tell the current_scan applet to redraw itself
        trigger_plot(model)
        self.scan.print('return: Loop1D::mutate_datasets()', -2)

    def mutate_plot(self, model, i_point, x, y, error, trigger=True):
        self.scan.print(
            '{}::mutate_plot(i_point={}, x={}, y={}, error={}'.format(
                model.__class__.__name__, i_point, x, y, error))
        model.mutate_plot(i_point=i_point, x=x, y=y, error=error)
        # tell the current_scan applet to redraw itself
        if trigger:
            trigger_plot(model)

    def fit(self, entry, save, use_mirror, dimension, i):
        """Perform the fit"""
        self.scan.print('call: Loop1D.fit()', 2)
        model = entry['model']
        x_data, y_data = model.get_fit_data(use_mirror)

        # for validation methods
        self.min_point = min(x_data)
        self.max_point = max(x_data)

        errors = model.stat_model.get('error', mirror=use_mirror)
        fit_function = model.fit_function

        guess = self.scan._get_fit_guess(fit_function)
        self.scan.print('return: Loop1D.fit()', -2)
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
