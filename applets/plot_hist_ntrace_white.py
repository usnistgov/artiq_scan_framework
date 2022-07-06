#!/usr/bin/env python3.5

import PyQt5  # make sure pyqtgraph imports Qt5
import pyqtgraph
from artiq.applets.simple import TitleApplet
n_plots = 4


class HistogramPlot(pyqtgraph.PlotWidget):
    labelStyle = {'font-size': '12pt', "font-bolt": "True"}

    def __init__(self, args):
        pyqtgraph.setConfigOption('background', 'w')
        pyqtgraph.setConfigOption('foreground', 'k')
        pyqtgraph.PlotWidget.__init__(self)
        self.args = args

    def data_changed(self, data, mods, title):
        if title is None:
            try:
                if self.args.plot_title is not None and self.args.plot_title in data:
                    title = data.get(self.args.plot_title, (False,None))[1]
                else:
                    if self.args.plot_title is None:
                        title = ""
                    else:
                        title = self.args.plot_title
            except KeyError:
                title = ""
        try:
            if self.args.x is None:
                x = None
            else:
                x = data[self.args.x][1]

            x_units = data.get(self.args.x_units, (False, None))[1] or self.args.x_units
            x_label = data.get(self.args.x_label, (False, None))[1] or self.args.x_label
            y_label = data.get(self.args.y_label, (False, None))[1] or self.args.y_label

            if x_units:
                x_label = x_label + " ({})".format(x_units)

            ys = []
            ys.append(data[self.args.y1][1])
            for i in range(2, n_plots+1):
                argname = 'y{}'.format(i)
                if hasattr(self.args, argname):
                    val = getattr(self.args, argname)
                    if val is not None:
                        ys.append(data[val][1])

        except KeyError:
            print("KeyError in plot_hist_ntrace_white applet")
            return

        if x is None:
            x = list(range(len(ys[0])+1))

        self.clear()
        self.addLegend()
        brushes = [(0, 0, 255, 100), (0, 255, 0, 100), (255, 0, 0, 100), (255, 255, 0, 100)]
        i = 0
        for y in ys:
            if len(y) and len(x) == len(y) + 1:
                name = getattr(self.args, 'leg{}'.format(i+1))
                self.plot(x, y, stepMode=True, fillLevel=0, brush=brushes[i], name=name, antialias=False)
            else:
                #print("Plot Hist: x and y dimensions don't agree")
            i = i + 1

        self.setLabel('bottom', x_label, **self.labelStyle)
        self.setLabel('left', y_label, **self.labelStyle)
        self.setTitle(title)


def main():
    applet = TitleApplet(HistogramPlot)
    applet.add_dataset("y1", "y1 values")
    applet.add_dataset("x", "Bin boundaries", required=False)
    for i in range(2, n_plots+1):
        applet.add_dataset("y%i" % i, "y%i values" % i, required=False)

    applet.add_dataset("plot_title", 'Plot title', required=False)
    applet.add_dataset("x_units", 'X-axis units', required=False)
    applet.add_dataset("x_label", 'X-axis label', required=False)
    applet.add_dataset("y_label", 'Y-axis label', required=False)
    applet.add_dataset("leg1", 'Name of y1 series in legend', required=False)
    applet.add_dataset("leg2", 'Name of y2 series in legend', required=False)
    applet.run()

if __name__ == "__main__":
    main()
