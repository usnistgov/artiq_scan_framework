#!/usr/bin/env python3.5

from artiq.applets.simple import SimpleApplet
import scan_framework.applets.plot as parent
import pyqtgraph as pg
import PyQt5
import numpy as np
import os

class CurrentScanApplet(SimpleApplet):
    def __init__(self, main_widget_class, cmd_description=None,
                 default_update_delay=0.0):
        #this is the applet class that is called when artiq creates the applet. It uses as argument main_widget_class which it creates as a widget object and then calls only
        #data_changed(self, data, mods) on that object (main_widget_class) to update the dataset
        super().__init__(main_widget_class, cmd_description, default_update_delay)
        self.n_namespaces= 10 #max number of arguments to applet command (number of curves to plot)
        self.add_datasets() #create arguments expected from artiq applet call
    def add_datasets(self):
        ###add namespaces, up to n namespace locations to pull from and get plot data/fits. plots is added for you for all arguments, so give e.g. current_scan not current_scan.plots
        ###based on number of arguments passed datasets will be pulled from for every namespace passed in arguments, then plots only plotted up to having the same
        ###rid as namespace 1
        self.add_dataset("ns0", "namespace location of items under scan_framework conventions") #only required argument that doesn't need --arg_name before it "ns" stands for namespace
        for i in range(1,self.n_namespaces):
            #generate ns1 through ns(n-1) namespace arguments
            self.add_dataset("ns"+str(i), str(i)+"th namespace location of items under scan_framework conventions",required=False) #requires --ns(i) argument before in applet command        
        #allow disable cursor argument
        self.add_dataset("cursor","set true/false if you want cursor or not",required=False)
    def args_init(self):
        self.args = self.argparser.parse_args()
        self.generate_namespace_args()
        self.embed = os.getenv("ARTIQ_APPLET_EMBED")
        self.datasets = {getattr(self.args, arg.replace("-", "_"))
                         for arg in self.dataset_args}
    def generate_namespace_args(self):
        #generate one time only namespace args from ns1, namely plot_title,x/ylabel/unit/scale,rid
        plot_items=['plot_title','x_label','x_units','x_scale','y_scale','y_label','y_units']
        namespace=self.args.ns0
        for name in plot_items:
            location=namespace+'.plots.'+name
            self.dataset_args.add(name)
            setattr(self.args,name,location)
        self.dataset_args.add('rid')
        self.args.rid=namespace+'.rid'
        
        #generate args unique from all namespaces
        
        #list of items to import from each namespace (in this case most all are prepended by .plots.)
        plot_items=['x','y','error','fitline','trigger']#could add x/y scale/unit to all of these possibly
        for i in range(self.n_namespaces):
            ns_string='ns'+str(i)
            namespace=getattr(self.args,ns_string)
            ns_string+='_'
            if namespace:
                for name in plot_items:
                    location=namespace+'.plots.'+name
                    name=ns_string+name
                    self.dataset_args.add(name) #add this as an argument to pull from
                    setattr(self.args,name,location) #add this as the location of whene that argument points to
                #rid different location, don't prepend .plots
                self.dataset_args.add(ns_string+'rid')
                setattr(self.args,ns_string+'rid',namespace+'.rid')   
                self.n_namespaces=i+1
            else:
                #reached max number of namespace args passed, stop for loop set n_namespaces for this instance of the applet
                break
        self.args.n_namespaces=self.n_namespaces #save n_namespaces to args to pass to plot widget __init__ call
            
            

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
    xs=[0]#needed to avoid first cursor init call error
    ys=[0]
    def __init__(self, args):
        #set self.args and get max_curves (number of arguments passed in artiq applet commands)
        super().__init__(args)
        self.args_dict=vars(self.args) #create dictionary version of args
        self.max_curves=self.args.n_namespaces
        self.n_curves=self.max_curves #this is modified based on number of matching rid plots
        
        #create cursor if desired
        self.cursor_enabled=self.args.cursor
        if self.cursor_enabled==None:
            self.cursor_enabled=True
        if self.cursor_enabled:        
            self.vLine = pg.InfiniteLine(angle=90, movable=False)#create cursor (vertical line)
            self.cursor_text=pg.TextItem()#create text for coordinate of cursor at data point
            self.addItem(self.cursor_text) #add cursor text item that says cursor coordinate values
            self.addItem(self.vLine, ignoreBounds=True) #add cursor item
            self.vb=self.getPlotItem().vb #getting viewbox to convert between Q coordinates from mouse to coordinate on plot
            self.proxy = pg.SignalProxy(self.scene().sigMouseMoved, rateLimit=60, slot=self.mouseMoved)#used to call update whenever mouse moved over plot
        
        #create list of curves/error bars/legend objects for max number of curves
        self.curve_objs=[self.plot() for i in range(self.max_curves)] #access curve n object by self.curve_obs[n]
        self.fit_objs=[self.plot() for i in range(self.max_curves)] #access fit n object by self.fit_obs[n]
        self.error_objs=[pg.ErrorBarItem() for i in range(self.max_curves)]#create error bars item list
        for error_obj in self.error_objs:
            self.addItem(error_obj) #add error bar item
    def _load_plots(self, data, key, ds_only=True, default=None):
        """Helper method to load a single dataset value and return it. Lists of args therefore not passable

        Falls back to an explicit value being specified in arguments or a given default value when the
        dataset doesn't exist.
        """

        argval =self.args_dict[key]
        val = data.get(argval, (False, default))
        ds_found = val[0]

        if ds_found:
            # get value from dataset
            if val[1] is not None:
                val = val[1]
            else:
                val = None
        else:
            if argval is not None and not ds_only:
                val = argval
            else:
                val = default

        return val
    def load(self, data):
        #always load and plot everything if first starting up plot, after which started=True,
        #then only load data/plot if one of the plots is triggered
        self.triggers=[self._load_plots(data,'ns%i_trigger'%i,default=0) for i in range(self.n_curves)]
        self.trigger=sum(self.triggers)

        if self.started and not self.trigger:
            return False

        """Load the one time data and set it as attribute of XYPlot"""
        # load dataset values
        self._load(data, ['plot_title', 'x_label', 'y_label', 'x_units', 'y_units'])
        self._load(data, 'x_scale', default=1)
        self._load(data, 'y_scale', default=1)
        self._load(data,'rid',default=None)
        
        #get number of curves to import by checking how many mach first rid
        self.rids=[self._load_plots(data,'ns%i_rid'%i) for i in range(self.max_curves)]
        self.n_curves=0 
        print(self.rids,self.started)
        for rid in self.rids:
            if self.rid==rid:
                self.n_curves+=1
                
        #load datasets for all curves with matching rid
        plot_items=['x','y','fitline','error']
        for item in plot_items:
            setattr(self,item+'s',[self._load_plots(data,'ns%i_'%i+item) for i in range(self.n_curves)])
        
    def validate(self):
        """Validate that the data can be plotted"""
        try:
            index=0
            for trigger in self.triggers[0:self.n_curves]:
                if trigger or not self.started:
                    x=self.xs[index]
                    y=self.ys[index]
                    fit=self.fitlines[index]
                    error=self.errors[index]
                    if not y.shape == x.shape:
                        print("plot_xy applet: x and y shapes in namespace %s don't agree" %self.args_dict['ns'+str(index)])
                        return False

                    if fit is not None and not fit.shape == x.shape:
                        print("plot_xy applet: x and fit shapes in namespace %s don't agree" %self.args_dict['ns'+str(index)])
                        return False
                    
                    if error is not None and not error.shape == y.shape:
                        print("plot_xy applet: y and error shapes in namespace %s don't agree" %self.args_dict['ns'+str(index)])
                        return False
                index+=1
        except:
            return False
    def clean(self):
        """scale data"""
        x_sc=self.x_scale
        y_sc=self.y_scale
        if x_sc is not None:
            for i in range(self.n_curves):
                if self.xs[i] is not None:
                    self.xs[i]=self.xs[i]/x_sc
        if y_sc is not None:
            for i in range(self.n_curves):
                if self.ys[i] is not None:
                    self.ys[i]=self.ys[i]/y_sc
                if self.errors[i] is not None:
                    self.errors[i]=self.errors[i]/y_sc
                if self.fitlines[i] is not None:
                    self.fitlines[i]=self.fitlines[i]/y_sc
    def draw(self):
        """Plot the data"""
        if self.triggers[0] or not self.started:
            # draw title
            style = self.style['title']
            if self.rid is None:
                title = self.plot_title
            else:
                title = "RID {}: {}".format(self.rid, self.plot_title)
            self.setTitle(title, size=style['size'])
    
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
              
            #if cursor enabled, move position (and text) to first point
            if self.cursor_enabled:
                self.set_cursor(0)
        index=0
        for trigger in self.triggers:
            if trigger or not self.started:
                self.draw_series(index)
            index+=1
    def draw_series(self, i):
        print('drawing series',i)
        x = self.xs[i]
        y = self.ys[i]
        fit=self.fitlines[i]
        error=self.errors[i]
        
        #get plot objects for index i
        error_obj=self.error_objs[i]
        fit_obj=self.fit_objs[i]
        curve_obj=self.curve_objs[i]        

        # don't draw if all values are nan 
        if not np.isnan(y).all():
            # style
            brush = pg.mkBrush(color=self.get_style('plot.color', i))
            symbol = self.get_style('plot.symbol', i)
            size = self.get_style('plot.size', i)
            pen = self.get_style('plot.pen')

            # plot
            curve_obj.setData(x, y, pen=pen, symbol=symbol, size=size, symbolBrush=brush)
        else:
            curve_obj.clear()
            
        # draw fit
        if fit is not None:
            if not np.isnan(fit).all():
                # style
                pen = self.get_style('fit.pen')
                fit_obj.setData(x, fit, pen=pen)
            else:
                fit_obj.clear()
        else:
            fit_obj.clear()
            
        # draw error
        if error is not None:
            if not np.isnan(error).all() or error!=None:
                error_obj.setData(x=np.array(x),y=np.array(y),height=2*error)
            else:
                error_obj.clear()
        else:
            error_obj.clear()
                
    def mouseMoved(self,evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.sceneBoundingRect().contains(pos):
            mousePoint = self.vb.mapSceneToView(pos)
            x_cursor = mousePoint.x()
            x=self.xs[0]
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
            self.set_cursor(index)
    def set_cursor(self,index):
        x=self.xs[0]
        y=self.ys[0]
        self.cursor_text.setText("x=%f,y=%f" %(x[index],y[index]))
        self.cursor_text.setPos(x[index],y[index])
        self.vLine.setPos(x[index])

def main():
    applet = CurrentScanApplet(XYPlot)
    applet.run()


if __name__ == "__main__":
    main()
