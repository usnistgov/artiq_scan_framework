#!/usr/bin/env python3.5
import scan_framework.applets.plot as parent
import pyqtgraph as pg
import PyQt5
import numpy as np


class SimpleApplet(parent.SimpleApplet):

    def add_datasets(self):
        # plot title
        self.add_dataset("title", 'plot title', required=False)
        self.add_dataset("rid", "RID for experiment", required=False)

        # x/y data
        self.add_dataset("y", "Y values")
        self.add_dataset("y2", "Y2 values", required=False)
        self.add_dataset("trigger", "", required=False)
        self.add_dataset('i_plot', "", required=False)
        self.add_dataset("x", "X values", required=False)

        # error
        self.add_dataset("error", "Error bars for each X value", required=False)

        # fit
        self.add_dataset("fit", "Fit values for each X value", required=False)

        # axes
        self.add_dataset("x_label", 'x-axis label', required=False)
        self.add_dataset("x_units", 'x-axis units', required=False)
        self.add_dataset("x_scale", 'x-axis scale', required=False)
        self.add_dataset("y_scale", 'y-axis scale', required=False)
        self.add_dataset("y_label", 'y-axis label', required=False)
        self.add_dataset("y_units", 'y-axis label', required=False)


class XYPlot(parent.Plot):
    """Applet for plotting X-Y data.  A single trace is plotted by providing two 1D arrays for the x and y values.
    Multiple traces can be plotted by providing two 2D arrays for the x and y values.  The plot style can be customized
    by modifiying the `style` attribute.  When plotting multiple traces, each trace uses a separate symbol
    for its data points defined by :code:`style['plot']['symbol']`.

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
            'pen': pg.mkPen(color='r', width=4)
        },
        'plot': {
            'symbol': ['o',  't', 'd', 's', 'd'],
            'size': [10, 12, 15, 10, 10],
            'color': ['r', 'b', 'g', 'm', 'c', 'y'],
            'pen': None,
            'symbol2': ['t', 'd', 's', 'd', 'o'],
            'size2': [12, 15, 10, 10, 10],
            'color2': ['b', 'g', 'm', 'c', 'y', 'r'],
            'pen2': None
        },
        'axes': {
            'size': 15,
            'tick_offset': 30,
            'label': {
                'font-size': '15pt',
                "font-bold": "True"
            }
        },
        'title': {
            'size': '20px'
        }
    }  #: Specifies the style of the plot.
    started = False
    def __init__(self, args):
        super().__init__(args)
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.cursor_text=pg.TextItem()
        self.error_bars=pg.ErrorBarItem()
        self.addItem(self.error_bars)
        self.addItem(self.cursor_text)
        self.addItem(self.vLine, ignoreBounds=True)
        self.vb=self.getPlotItem().vb
        self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)
        self.curve_plot=self.plot()
        self.curve_fit_plot=self.plot()
        self.curve_y2_plot=self.plot()
        
    def load(self, data):
         # don't plot if not triggered
        self._load(data, 'trigger', default=1, ds_only=False)
        if self.started and not self.trigger:
            return False

        # defaults
        self.x_scale = 1
        self.y_scale = 1
        self.fit = None
        self.error = None
        self.x_label = None
        self.y_label = None
        self.i_plot = None

        """Load the data from datasets"""
        # load dataset values
        self._load(data, ['title', 'x_label', 'y_label', 'x_units', 'y_units'])
        self._load(data, 'x_scale', default=1)
        self._load(data, 'y_scale', default=1)
        self._load(data, ['x', 'y'], default=None)
        self._load(data, 'y2', default=None)

        self._load(data, 'i_plot', default=None)

        self._load(data, 'fit', default=None)
        self._load(data, 'error', default=None)
        self._load(data, 'rid', default=None)

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
        if len(self.y.shape) == 1:
            self.y = np.array([self.y])
            self.y2 = np.array([self.y2])
            self.x = np.array([self.x])
            if self.fit is not None:
                self.fit = np.array([self.fit])
            if self.error is not None:
                self.error = np.array([self.error])

        if self.x_scale is not None:
            self.x = self.x / self.x_scale
        if self.y_scale is not None:
            self.y = self.y / self.y_scale
            if self.error is not None:
                self.error = self.error/ self.y_scale
            if self.fit is not None:
                self.fit = self.fit / self.y_scale

    def validate(self):
        """Validate that the data can be plotted"""
        try:
            if not self.y.shape == self.x.shape:
                print("plot_xy applet: x and y shapes don't agree")
                return False

            if self.fit is not None and not self.fit.shape == self.x.shape:
                print("plot_xy applet: x and fit shapes don't agree")
                return False
        except AttributeError:
            return False

    def draw(self):
        """Plot the data"""
        # dimensions of the data
        shape = self.y.shape

        # draw title
        style = self.style['title']
        if self.rid is None:
            title = self.title
        else:
            title = "RID {}: {}".format(self.rid, self.title)
        self.setTitle(title, size=style['size'])

        # draw data
        if self.i_plot is not None:
            self.draw_series(self.i_plot)
        else:
            for i in range(shape[0]):
                self.draw_series(i)

        # draw axes
        axis_font = PyQt5.QtGui.QFont()
        axis_font.setPixelSize(self.get_style('axes.size'))

        # draw x axis
        x_axis = self.getAxis('bottom')
        x_axis.tickFont = axis_font
        # somehow tickTextOffset necessary to change tick font
        x_axis.setStyle(tickTextOffset=self.get_style('axes.tick_offset'))
        x_axis.enableAutoSIPrefix(False)
        if self.x_label is not None:
            self.setLabel('bottom', self.x_label, units=self.x_units, **self.get_style("axes.label"))

        # draw y axis
        y_axis = self.getAxis('left')
        y_axis.tickFont = axis_font
        y_axis.setStyle(tickTextOffset=self.get_style('axes.tick_offset'))
        if self.y_label is not None:
            self.setLabel('left', self.y_label, units=self.y_units, **self.get_style("axes.label"))

    def draw_series(self, i):
        x = self.x[i]
        y = self.y[i]
        y2 = None
        if self.y2 is not None:
            y2 = self.y2[i]

        # don't draw if all values are nan
        if not np.isnan(y).all():
            # style
            brush = pg.mkBrush(color=self.get_style('plot.color', i))
            symbol = self.get_style('plot.symbol', i)
            size = self.get_style('plot.size', i)
            pen = self.get_style('plot.pen')

            # plot
            self.curve_plot.setData(x, y, pen=pen, symbol=symbol, size=size, symbolBrush=brush)

            # style 2
            brush2 = pg.mkBrush(color=self.get_style('plot.color2', i))
            symbol2 = self.get_style('plot.symbol2', i)
            size2 = self.get_style('plot.size2', i)
            pen2 = self.get_style('plot.pen2')

            # plot y2
            if y2 is not None:
                self.curve_y2_plot.setData(x, y2, pen=pen2, symbol=symbol2, size=size2, symbolBrush=brush2)

        # draw fit
        if self.fit is not None:
            fit = self.fit[i]
            if fit is not None:
                # style
                pen = self.get_style('fit.pen')
                self.curve_fit_plot.setData(x, fit, pen=pen)

        # draw error
        if self.error is not None:
            error = self.error[i]
            if not np.isnan(error).all():
                # See https://github.com/pyqtgraph/pyqtgraph/issues/211
                if hasattr(error, "__len__") and not isinstance(error, np.ndarray):
                    error = np.array(error)
                if len(error) == len(x):
                    self.error_bars.setData(x=np.array(x),y=np.array(y),height=2*error)
                    #errbars = pg.ErrorBarItem(
                    #    x = np.array(x), y = np.array(y), height = 2 * error)
                    #self.addItem(errbars)
    def mouseMoved(self,evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.sceneBoundingRect().contains(pos):
            mousePoint = self.vb.mapSceneToView(pos)
            x_cursor = mousePoint.x()
            x=self.x[0]
            y=self.y[0]
            index=0
            if x_cursor > x[0] and x_cursor < x[-1]:
                #cursor within bounds of data, get approximate index of x data 
                for i in range(len(x)):
                    if x[i]>x_cursor:
                        #x_cursor definitely greater than x[0], find first x[i]>x_cursor
                        if abs(x[i]-x_cursor)<abs(x[i-1]-x_cursor):
                            index=i
                        else:
                            index=i-1
                        break            
            if x_cursor > x[-1]:
                index=-1
            self.cursor_text.setText("x=%f,y=%f" %(x[index],y[index]))
            self.cursor_text.setPos(x[index],y[index])
            self.vLine.setPos(x[index])

def main():
    applet = SimpleApplet(XYPlot)
    applet.run()


if __name__ == "__main__":
    main()
