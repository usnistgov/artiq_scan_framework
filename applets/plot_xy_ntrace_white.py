#!/usr/bin/env python3.5
# -*- coding: utf8 -*-
#
#
# Applet for plotting multiple measurements in the NIST scan framework
import numpy as np
import PyQt5  # make sure pyqtgraph imports Qt5
import pyqtgraph
from artiq.applets.simple import SimpleApplet


class LoadError(Exception):
    pass


class XYPlot(pyqtgraph.PlotWidget):
    def __init__(self, args):
        #  colors have to be set before PlotWidget initialised
        #
        pyqtgraph.setConfigOption('background', 'w')
        pyqtgraph.setConfigOption('foreground', 'k')

        self.args = args
        self.args_dict = vars(args)
        pyqtgraph.PlotWidget.__init__(self)
        self.n_plots = 3

    def load_plot_data(self, data, n):
        # load y
        try:
            key = self.args_dict["y%i" % n]
            y = data[key][1]
        except KeyError:
            raise LoadError

        # load x
        x = data.get(self.args_dict["x%i" % n], (False, None))[1]
        if x is None:
            x = list(range(len(y)))

        # load error
        error = data.get(self.args_dict["error%i"%n], (False, None))[1]
        if error is not None:
            if len(np.shape(error)) > 1:
                error = np.reshape(error[1], np.shape(x))

        # load fit
        fit = data.get(self.args_dict["fit%i"%n], (False, None))[1]
        if len(np.shape(fit)) > 1:
            fit = np.reshape(fit[1], np.shape(x))

        if len(np.shape(y)) > 1:
            y = np.reshape(y[1], np.shape(x))
        if not len(y) or len(y) != len(x):
            raise LoadError
        if error is not None and hasattr(error, "__len__"):
            if not len(error):
                error = None
            elif len(error) != len(y):
                raise LoadError
        if fit is not None:
            if not len(fit):
                fit = None
            elif len(fit) != len(y):
                raise LoadError
        return x, y, error, fit

    def data_changed(self, data, mods):
        # load title
        try:
            title = self.args.title
        except KeyError:
            title = None

        # load plot data
        try:
            plot_data = [[] for _ in range(6)]
            for i in range(self.n_plots):
                plot_data[i] = self.load_plot_data(data, i+1)
        except LoadError:
            return

        self.clear()

        # add plots
        colors = ['r', 'b', 'g', 'm', 'c','y']
        symbols = ['o',  't', 'd', 's', 'd' ]
        sizes = [10, 12, 15, 10, 10]
        errcolors = ['k', 'r', 'k', 'r', 'r', 'r', ]
        for i in range(self.n_plots):
            (x, y, error, fit) = plot_data[i]
            c = colors[i % len(colors)]
            s = symbols[i % len(symbols)]
            sz = sizes[i % len(sizes)]
            self.plot(x, y, pen=None, symbol=s, symbolBrush=c, symbolSize=sz)


            # add errors & fits
            if error is not None:
                ec = errcolors[i % len(errcolors)]
                # See https://github.com/pyqtgraph/pyqtgraph/issues/211
                if hasattr(error, "__len__") and not isinstance(error, np.ndarray):
                    error = np.array(error)
                errbars = pyqtgraph.ErrorBarItem(
                    x=np.array(x), y=np.array(y), height=error,
                    pen=pyqtgraph.mkPen(color=ec, width=1), beam=np.array((max(x) - min(x)) / len(x) / 10))
                self.addItem(errbars)

            if fit is not None:
                xi = np.argsort(x)
                self.plot(x[xi], fit[xi], pen=pyqtgraph.mkPen(color='r', width=2),
                          shadowPen=pyqtgraph.mkPen(color='w', width=3))

        # axes & title
        x_axis = self.getAxis('bottom')
        y_axis = self.getAxis('left')
        axis_font = PyQt5.QtGui.QFont()
        axis_font.setPixelSize(20)
        x_axis.tickFont = axis_font
        # somehow tickTextOffset necessary to change tick font
        x_axis.setStyle(tickTextOffset=30)
        y_axis.tickFont = axis_font
        y_axis.setStyle(tickTextOffset=30)
        x_axis.enableAutoSIPrefix(False)
        label_style = {'font-size': '20pt', "font-bold": "False"}
        self.setLabel('bottom', self.args.x_label, units=self.args.x_units,
                      **label_style)
        self.setLabel('left', self.args.y_label, units=self.args.y_units,
                      **label_style)
        self.setTitle(title, size='20px')




def main():
    applet = SimpleApplet(XYPlot)
    n_plots = 3
    for i in range(1, n_plots+1):
        applet.add_dataset("y%i" % i, "y%i values" % i)
        applet.add_dataset("x%i" % i, "x%i values" % i, required=False)
        applet.add_dataset("error%i" % i, "Error bars for each Y%i value" % i, required=False)
        applet.add_dataset("fit%i" % i, "Fit values for each Y%i value" % i, required=False)

    applet.add_dataset("x_label", 'x-axis label', required=False)
    applet.add_dataset("x_units", 'x-axis units', required=False)
    applet.add_dataset("y_label", 'y-axis label', required=False)
    applet.add_dataset("y_units", 'y-axis label', required=False)
    applet.add_dataset("title", "plot title", required=False)
    applet.run()

if __name__ == "__main__":
    main()
