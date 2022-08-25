# Example 14: Multi-results models
#
# Showing how to create a multiresult measurement scan.
#   In this example, two measurements are created, one a standard
#   measurement like in example 6, another a multimeasurement model that
#   uses as it's submodels the same model. Additionally, a calculation is done on the multiresult model,
#   and various subsets of models/calculations can be fit.
#
# NOTE: Also create in the dashboard the applet for this experiment in scan_framework/examples/scans/ex14_applet.txt
from artiq.experiment import *
from artiq_scan_framework import *

class ExMultiResultScan(Scan1D, EnvExperiment):
    enable_simulations=True #enabling this populates the simulation GUI arguments. Running a simulation does the whole scan on the host no core device utilized
    #disable the above if you have a core device and would like to see what a scan might look like and modify the measure method pulses below
    def build(self):
        super().build()
        
        self.scan_arguments()
        
        self.setattr_argument('frequencies', Scannable(
            default=RangeScan(
                start=0,
                stop=7,
                npoints=30
            ),
            unit='Hz',
            scale=1
        ))
        
        self.setattr_device("core") #comment these two lines out if no core device available, and enable simulations
        self.setattr_device("ttl2") #comment these two lines out if no core device available, and enable simulations
        
    def prepare(self):
        # 1. create a normal model the same as in example 6: the namespace below with simply be example14.m1 where you will find all datasets for this measurement
        #  Setting mirror will copy all information to the current_scan and current_histogram namespaces. Mirroring multiple measurements will simply overwrite this
        #  And only show the last measurement mirrored over
        measurement1_model=Example14Model(self,mmnt_name='m1',mirror=False)

        # 2. create a multiresult model. To do this we need to instantiate submodels for each result for this measurement. For this example we will use the same
        #  model as the measurement above, but pretend we have be+ ion counts, and mg+ ion counts and just set their namespace to be their mmnt_name
        be_model = Example14Model(self,
            # Note: All arguments of the constructor are assigned to attributes of the model.
            namespace="%mmnt_name",mmnt_name='be_ions',mirror=False
        )
        mg_model = Example14Model(self, namespace="%mmnt_name", mmnt_name="mg_ions",mirror=False)
        
        # 3. after instantiating our submodels, be_model and mg_model, we want to put them together into a single measurement (these results will be returned
        #  for a single measure() call so the pulse sequence doesn't need to be repeated for another measurement). First we add the models into a list of all submodels
        #  used in the measurement. If you plan to return nresults for this measurement you must have n models in this list        
        models=[be_model,mg_model]
        
        # 4. Now select any subsets of the submodels in the models list that you would like to perform fits on and put them in a fit_models list
        fit_models=[be_model]
        #fit_models=[be_model,mg_model] #uncomment this line to try fitting both models
        
        # 5. Now instantiate a multi-result measurement model using the models and fit_models lists. If fit_models is not passed no fits will be performed
        #  on any submodels. Additionally, another argument can be passed fitself=True if you would like to perform a fit on the multiresult model itself.
        #  This will only be the case if there is a calculation performed on the multiresult model, which will then generate data in the multiresult model that
        #  can then be fit to. To make a calculation you will need to override multiresult_data=True in the multiresult model (see below). Lastly by default
        #  The multiresult model has overwrite_namespace=True, meaning the be and mg ion models above will have their namspaces prepended by the multiresult
        #  model namespace, in this case multiresult.be_ions and multiresult.mg_ions. Disabling this would keep the individual submodels namespaces unaffected
        
        multiresult_measurement=MultiresultExModel(self,models,fit_models,fitself=True,mirror=True) #set fitself=False if you don't plan to fit a calculation with this multiresult model
        
        # 6. Finally register the models of the measurements. Note you MUST pass nresults=2 for the case of the multiresult model with 2 results, otherwise the
        #  other models will be ignored and the model will be treated as a standard single result model. Setting fit=True will fit all models in the fit_models list
        #  along with fitting the calculation performed in the multiresult model if fitself=True
        
        self.register_model(measurement1_model,measurement="m1",fit=True)
        
        #Here I've also created an example calculation that uses all of the submodel's data. You could also put this in another register model line (commented below)
        #To mirror the mean/error/fit to the current scan mutate_plot=True must be passed when registering the calculation
        self.register_model(multiresult_measurement,measurement="multiresult",fit=True,calculation="multiresult_calculation",nresults=2,mutate_plot=True)
        #self.register_model(multiresult_measurement,measurement="multiresult",fit=True,nresults=2) # use this to ignore calculations. You can also set multiresult_data false (see below)
        #self.register_model(multiresult_measurement,measurement="multiresult",fit=True,calculation="multiresult_calculation",nresults=2,mutate_plot=True)
        
        
        
    def get_scan_points(self):
        return self.frequencies
    @kernel
    def initialize_devices(self):
        self.core.reset()
        delay(10*ms)
    @kernel
    def measure(self, frequency,results):
        ###these first two slack lines are just examples to show how to see what the slack looks like at the start of each measurement
        #slack = self.core.mu_to_seconds(now_mu() - self.core.get_rtio_counter_mu())
        #print(slack / us, "us", "start of measure")
        self.ttl2.on()
        delay(2000*us)
        self.ttl2.off()
        delay(1000*us)
        
        if self.measurement=="multiresult":
            results[0]=int(frequency ** 2)
            results[1]=int(frequency ** 0.5)
        elif self.measurement=="m1":
            results[0]=int(frequency**3)

class MultiresultExModel(MultiresultModel):
    
    namespace='multiresult'
    broadcast = True
    persist = True
    save = True 
    fit_function = curvefits.Power


    models_dict={} #This line isn't necessary but is a reminder that you can access models_dict[name] to get each model, where name is the namespace before being overwritten (see below)
    multiresult_data=True #By defualt init_datasets will call super().init_datasets, creating stats, plots, fit, and if enable_histograms histograms, 
                           #but setting this to False disables all of these. You MUST set this to True if you would like to make a calculation.
    overwrite_namespace=True #By default overwrite all submodels namespaces to prepend this multiresultmodel's namespace
    enable_histograms=False #False by default assuming a calculation only don't need histogram here
    
    
    def calculate(self,i_point,calculation):
        be_means = self.models_dict["be_ions"].stat_model.means[i_point]
        #you can access the submodels by name using the models_dict like above, or use the self.models[i] list like below (but you must remember the index order i):
        #be_means = self.models[0].stat_model.means[i_point] 
        be_error = self.models_dict["be_ions"].stat_model.errors[i_point]
        mg_means = self.models_dict["mg_ions"].stat_model.means[i_point]
        mg_error = self.models_dict["mg_ions"].stat_model.errors[i_point]

        avg = (be_means+mg_means)/2
        error = (be_error +mg_error)/2
        return avg, error
    @property
    def guess(self):
        return {
                'A':1,
                'alpha': 1.5,
                'y0':0
            }
    # Set the scale of each fit parameter by setting `man_scale` (see analysis/curvefits.py)
    man_scale = {
        'A': 1,
        'alpha': 1,
        'y0': 1
    }

    # Bound the allowed fit parameters by setting `man_bounds` (see analysis/curvefits.py)
    @property
    def man_bounds(self):
        return {'A': [.5, 5],'alpha': [0.1, 2.5]}
    
# Note: A single model can be used for both measurements
class Example14Model(ScanModel):
    # 2a. Reference the attribute using namespace tokens.
    #     `%mmnt_name` is a namespace token and will be replaced by the model's `mmnt_name` attribute.
    namespace = "example_14.%mmnt_name"
    broadcast = True
    persist = True
    save = True
    fit_function = curvefits.Power

    # 2b. Use @property to dynamically determine an attribute
    @property
    def guess(self):
        # Fit `x^2` to the `be_ions result` measurement means
        if self.mmnt_name == 'be_ions':
            return {
                'A': 1,
                'alpha': 2,
                'y0': 0
            }
        # Fit `x^.5` to the `mg_ions result` measurement means
        if self.mmnt_name == 'mg_ions':
            return {
                'A': 1,
                'alpha': .5,
                'y0': 0
            }
        # Fit `x^3` to the `m1` measurement means
        if self.mmnt_name == 'm1':
            return {
                'A':1,
                'alpha': 3,
                'y0':0
            }
    @property
    def simulation_args(self):
        # Use `x^2` to the `be_ions result` measurement simulation
        if self.mmnt_name == 'be_ions':
            return {
                'A': 1,
                'alpha': 2,
                'y0': 0
            }
        # Use `x^.5` to the `mg_ions result` measurement simulation
        if self.mmnt_name == 'mg_ions':
            return {
                'A': 1,
                'alpha': .5,
                'y0': 0
            }
        # Use `x^3` to the `m1` measurement simulation
        if self.mmnt_name == 'm1':
            return {
                'A':1,
                'alpha': 3,
                'y0':0
            }

    # Set the scale of each fit parameter by setting `man_scale` (see analysis/curvefits.py)
    man_scale = {
        'A': 1,
        'alpha': 1,
        'y0': 1
    }

    # Bound the allowed fit parameters by setting `man_bounds` (see analysis/curvefits.py)
    @property
    def man_bounds(self):
        if self.mmnt_name == 'be_ions':
            return {
                'A': [.9, 1.1],
                'alpha': [1.5, 2.5]
            }
        if self.mmnt_name == 'mg_ions':
            return {
                'A': [.9, 1.1],
                'alpha': [0.1, 1.0]
            }
        if self.mmnt_name == 'm1':
            return {
                'A':[.9,1.1],
                'alpha': [2.5,3.5]
            }