#!/usr/bin/env python3.5
from . import plot
import pyqtgraph
import PyQt5
import numpy as np
import itertools
n_plots = 3

class SimpleApplet(plot.SimpleApplet):

    def add_datasets(self):
        # plot title
        self.add_dataset("title", 'plot title', required=False)
        self.add_dataset("rid", "RID for experiment", required=False)
        self.add_dataset("trigger", "", required=False)

        for i in range(n_plots):
            # x/y data
            self.add_dataset("y%i" % (i+1), "y%i values" % (i+1), required=False)
            self.add_dataset("x%i" % (i+1), "x%i values" % (i+1), required=False)
            self.add_dataset("pass_y%i" % (i+1), "y%i values at each pass", required=False)

            # error
            self.add_dataset("error%i" % (i+1), "errror bars%i for each y%i value" % ((i+1), (i+1)), required=False)

            # fit
            self.add_dataset("fit%i" % (i+1), "fit%i values at each x value"%(i+1), required=False)
            self.add_dataset("fit_fine%i" % (i+1), "fine fit%i values at each fine x%i value"% ((i+1), (i+1)), required=False)
            self.add_dataset("x_fine%i" % (i+1), "fine x%i values"%(i+1), required=False)

        # axes
        self.add_dataset("x_label", 'x-axis label', required=False)
        self.add_dataset("x_units", 'x-axis units', required=False)
        self.add_dataset("y_label", 'y-axis label', required=False)
        self.add_dataset("y_units", 'y-axis label', required=False)


class XYNTracePlot(plot.Plot):
    """Applet for plotting X-Y data.  A single trace is plotted by providing two 1D arrays for the x and y values.
    Multiple traces can be plotted by providing two 2D arrays for the x and y values.  The plot style can be customized
     by modifiying the `style` attribute.  When plotting multiple traces, each trace uses a separate symbol
     for its data points defined by style['plot']['symbol'].

    **Default Styles**
        - **style['background']['color']** white
        - **style['foreground']['color']** black
        - **style['fit']['pen']** fitline color is red with a width of 4
        - **style['plot']['symbol']** data point symbols for each trace.  Order is o, t, d, s, d which repeats for >5 traces.
        - **style['plot']['size']** data point symbol sizes for each trace.  Order is 10, 12, 15, 10, 10 which repeats for >5 traces.
        - **style['plot']['color']** data point symbol colors for each trace.  Order is r, b, g, m, c, y which repeats for >5 traces.
        - **style['plot']['axes']['size']** axes size defaults to 15
        - **style['plot']['axes']['tick_offset']** tick offset defaults to 30
        - **style['plot']['axes']['label']['font-size']** axes label font sizes default to 15pt
        - **style['plot']['axes']['label']['bold']** axes label fonts are bold by default
        - **style['title']['size']** plot title size defaults to 20px
    """
    style = {
        'background': {
            'color': 'w'
        },
        'foreground': {
            'color': 'k'
        },
        'fit': {
            'pen': pyqtgraph.mkPen(color=PyQt5.QtGui.QColor.fromHsvF(0.00, 0.7, 0.9, 0.85), width=2.0)
        },
        'plot': {
            'symbol': ['o',  't', 'd', 's', 'x', 'p', 'h', 'star'],
            'size': [8, 10, 12, 10, 10],
            'color': [
                PyQt5.QtGui.QColor.fromHsvF(0 / 360, 0.828, 0.706, 0.9),
                PyQt5.QtGui.QColor.fromHsvF(205 / 360, 0.828, 0.706, 0.9),
                PyQt5.QtGui.QColor.fromHsvF(100 / 360, 0.828, 0.706, 0.9),
                'm', 'c', 'y'],
            'pen': None,
            'pass_pen': None,
            'pass_color': [
                [
                    PyQt5.QtGui.QColor.fromHsvF(345 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(350 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(355 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(0 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(5 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(10 / 360, 0.528, 0.706, 0.9),
                ],
                [
                    PyQt5.QtGui.QColor.fromHsvF(190 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(195 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(200 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(205 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(210 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(215 / 360, 0.528, 0.706, 0.9)
                ],
                [
                    PyQt5.QtGui.QColor.fromHsvF(85 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(90 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(95 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(100 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(105 / 360, 0.528, 0.706, 0.9),
                    PyQt5.QtGui.QColor.fromHsvF(110 / 360, 0.528, 0.706, 0.9),
                ]
                ],
            'pass_size': [6, 8, 8, 10, 10, 8, 8, 8, 8, 8],
            'pass_symbol': ['t', 'd', 'star', '+', 'x', 't1', 't2','t3'],
            'symbol2': ['t', 'd', 's', 'd', 'o'],
            'size2': [7, 15, 10, 10, 10],
            'color2': ['b', 'g', 'm', 'c', 'y', 'r'],
            'pen2': None
        },
        'axes': {
            'size': 14,
            'tick_offset': 30,
            'label': {
                'font-size': '11pt',
                "font-bold": "False"
            }
        },
        'title': {
            'size': '17px'
        }
    }  #: Specifies the style of the plot.
    started = False
    starting = True

    def load(self, data):
        # don't plot if not triggered
        self._load(data, 'trigger', default=1, ds_only=False)

        if not self.trigger:
            return False

        # defaults
        self.x_label = None
        self.y_label = None

        self.error = [None for _ in range(n_plots)]
        self.fit = [None for _ in range(n_plots)]
        self.fit_fine = [None for _ in range(n_plots)]
        self.x_fine = [None for _ in range(n_plots)]

        """Load the data from datasets"""
        # load dataset values
        self._load(data, ['title', 'x_label', 'y_label', 'x_units', 'y_units'], ds_only=False)
        self._load(data, 'rid', default=None)
        for i in range(n_plots):
            self._load(data, ['x%i'%(i+1),
                              'y%i'%(i+1),
                              'pass_y%i'%(i+1),
                              'fit%i'%(i+1),
                              'fit_fine%i'%(i+1),
                              'x_fine%i'%(i+1),
                              'error%i'%(i+1)], default=None, ds_only=True)
            if getattr(self, 'x%i'%(i+1)) is None and not getattr(self, 'y%i'%(i+1)) is None:
                setattr(self, 'x%i'%(i+1), np.array([_ for _ in range(len(getattr(self, 'y%i'%(i+1)) ))], np.int32))
        # don't plot if not triggered
        if self.started and not self.trigger:
            return False
        self.started = True

        # default value for x is index values
        #if self.x is None:
        #    self.x = [_ for _ in itertools.product(*[range(self.shape[0]), range(self.shape[1])])]

    def clean(self):
        """Clean the data so it can be plotted"""
        # format data so plots also work with 1D arrays
        for i in range(n_plots):
            if len(getattr(self, 'y%i' % (i+1)).shape) == 1:
                setattr(self, 'y%i'%(i+1), np.array([getattr(self, 'y%i'%(i+1))]))
                setattr(self, 'x%i' %(i+1), np.array([getattr(self, 'x%i' % (i+1))]))
                if getattr(self, 'fit%i'%(i+1)) is not None:
                    setattr(self, 'fit%i'%(i+1), np.array([getattr(self, 'fit%i'%(i+1))]))
                if getattr(self, 'error%i' % (i+1)) is not None:
                    setattr(self, 'error%i' % (i+1), np.array([getattr(self,  'error%i' % (i+1))]))

    def validate(self):
        """Validate that the data can be plotted"""

        try:
            for i in range(n_plots):
                if not getattr(self, 'y%i'%(i+1)).shape == getattr(self, 'x%i'%(i+1)).shape:
                    #print("plot_xy applet: x and y shapes don't agree")
                    return False

                if getattr(self, 'fit%i'%(i+1)) is not None and not getattr(self, 'fit%i'%(i+1)).shape == getattr(self, 'x%i'%(i+1)):
                    #print("plot_xy applet: x and fit shapes don't agree")
                    return False
        except AttributeError:
            print('AttributeError')
            return False

    def draw(self):
        """Plot the data"""

        # draw title
        style = self.style['title']
        if self.rid is None:
            title = self.title
        else:
            title = "RID {}: {}".format(self.rid, self.title)

        self.setTitle(title, size=style['size'])

        for i in range(n_plots):
            # dimensions of the data
            shape = getattr(self, 'y%i'%(i+1)).shape

            # draw data
            for n in range(shape[0]):
                self.draw_series(i, n)
        # draw axes
        axis_font = PyQt5.QtGui.QFont()
        axis_font.setPixelSize(self.get_style('axes.size'))

        # draw x axis
        x_axis = self.getAxis('bottom')
        x_axis.tickFont = axis_font
        # somehow tickTextOffset necessary to change tick font
        x_axis.setStyle(tickTextOffset=self.get_style('axes.tick_offset'))
        x_axis.enableAutoSIPrefix(False)
        if self.x_label is not None and self.x_label:
            self.setLabel('bottom', self.x_label, units=self.x_units, **self.get_style("axes.label"))

        # draw y axis
        y_axis = self.getAxis('left')
        y_axis.tickFont = axis_font
        y_axis.setStyle(tickTextOffset=self.get_style('axes.tick_offset'))
        if self.y_label is not None and self.y_label:
            self.setLabel('left', self.y_label, units=self.y_units, **self.get_style("axes.label"))
        self.showGrid(x=True, y=True, alpha=0.5)

    def draw_series(self, i, n, name=None):
        x = getattr(self, 'x%i'%(i+1))
        y = getattr(self, 'y%i' %(i+1))
        fit = getattr(self, 'fit%i' %(i+1))
        error = getattr(self, 'fit%i' %(i+1))
        fit_fine = getattr(self, 'fit_fine%i' %(i+1))
        x_fine = getattr(self, 'fit_fine%i' %(i+1))
        pass_y = getattr(self, 'pass_y%i'%(i+1))
        pass_brushes = self.get_style('plot.pass_color', i)

        if n < len(x) and n < len(y):
            x = x[n]
            y = y[n]

            # don't draw if all values are nan
            if not np.isnan(y).all():
                # plot pass ys
                pass_pen = self.get_style('plot.pass_pen')

                if pass_y is not None:
                    for pi, py in enumerate(pass_y):
                        pass_symbol = self.get_style('plot.pass_symbol', pi)
                        pass_brush = pass_brushes[pi%6]
                        pass_size = self.get_style('plot.pass_size', pi)
                        self.plot(x, py, pen=pass_pen, symbol=pass_symbol, symbolSize=pass_size, symbolBrush=pass_brush, symbolPen=None, name=name)

                # plot
                brush = pyqtgraph.mkBrush(color=self.get_style('plot.color', i))
                symbol = self.get_style('plot.symbol', n)
                size = self.get_style('plot.size', n)
                pen = self.get_style('plot.pen')
                self.plot(x, y, pen=pen, symbol=symbol, symbolSize=size, symbolBrush=brush, symbolPen=None, name=name)

            # draw fit
            if fit_fine is not None and x_fine is not None:
                if len(fit_fine) == len(x_fine):
                    # style
                    pen = self.get_style('fit.pen')
                    self.plot(self.x_fine, self.fit_fine, pen=pen)
            elif fit is not None:
                fit = self.fit[i]
                if fit is not None:
                    # style
                    pen = self.get_style('fit.pen')
                    self.plot(x, fit, pen=pen)

            # draw error
            if error is not None:
                error = error[i]
                if not np.isnan(error).all():
                    # See https://github.com/pyqtgraph/pyqtgraph/issues/211
                    if hasattr(error, "__len__") and not isinstance(error, np.ndarray):
                        error = np.array(error)
                    errbars = pyqtgraph.ErrorBarItem(
                        x=np.array(x), y=np.array(y), height=error)
                    self.addItem(errbars)



def main():
    applet = SimpleApplet(XYNTracePlot)
    applet.run()


if __name__ == "__main__":
    main()

