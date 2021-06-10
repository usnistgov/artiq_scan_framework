#!/usr/bin/env python3.5

import PyQt5  # make sure pyqtgraph imports Qt5
import pyqtgraph

from artiq.applets.simple import TitleApplet


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
                title = data.get(self.args.plot_title, (False,None))[1]
            except KeyError:
                title = ""
        try:
            y = data[self.args.y][1]
            fit = data.get(self.args.fit, (False, None))[1] or [1 for _ in range(10)]
            if self.args.x is None:
                x = None
            else:
                x = data[self.args.x][1]

            x_units = data.get(self.args.x_units, (False, None))[1] or 1
            x_label = data.get(self.args.x_label, (False, None))[1] or ""
            y_label = data.get(self.args.y_label, (False, None))[1] or ""
        except KeyError:
            return
        if x is None:
            x = list(range(len(y)+1))

        # axis scaling
        if x_units is not None:
            x = x / x_units

        if len(y) and len(x) == len(y) + 1:
            self.clear()
            self.plot(x, y, stepMode=True, fillLevel=0,
                      brush=(0, 0, 255, 150))
            self.setLabel('bottom', x_label, **self.labelStyle)
            self.setLabel('left', y_label, **self.labelStyle)
            self.setTitle(title)

        # draw fit
        if fit is not None:
            # style
            pen = self.get_style('fit.pen')
            self.plot(x, fit, pen=None)

        else:
            print("Plot Hist: x and y dimensions don't agree")


def main():
    applet = TitleApplet(HistogramPlot)
    applet.add_dataset("y", "Y values")
    applet.add_dataset("x", "Bin boundaries", required=False)
    applet.add_dataset("plot_title", 'Plot title', required=False)
    applet.add_dataset("x_units", 'X-axis units', required=False)
    applet.add_dataset("x_label", 'X-axis label', required=False)
    applet.add_dataset("y_label", 'Y-axis label', required=False)
    applet.add_dataset("fit", '', required=False)
    applet.run()

if __name__ == "__main__":
    main()