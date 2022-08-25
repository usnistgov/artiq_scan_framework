from artiq.experiment import *
from artiq_scan_framework.models.scan_model import *
import numpy as np
from math import *
import logging


class MultiresultModel(ScanModel):
    """
    An extension of the :class:`~scan_framework.models.scan_model.ScanModel` class that acts as a model of models, so that
    a single measurerment can have multiple results, and therefore multiple models for a single measurement. By combining
    the results under this multiresult model, calculations, plots, etc. can be defined that can access all results data e.g. 
    by looping through the list of self.models and accessing self.models[i].stat_model.counts or self.models[i].plots.y etc.
    
    To instantiate this model, instantiate the submodels corresponding to the nresults you want for this measurement, and add them to a list, 
    along with a second list of which of those models to fit. Lastly you can pass an argument fitself=true to perform a fit on the calculation within this larger model
    
    
    for a clear example, say you want to do a microwave scan using a microwave model that is now a multiresult model (MicrowaveMultiresultModel),and you'll have Be+ and Mg+ ions, 
    and you have a model for each, e.g. Be_MicrowaveModel and Mg_Microwave_model, then in the prepare stage of your experiment you would write:
        
    Bemodel=Be_MicrowaveModel(arguments to instantiate model)
    Mgmodel=Mg_MicrowaveModel(arguments to instantiate model)
    Bemodel.namespace="be_ions"
    Mgmodel.namespace="mg_ions"
    
    models=[Bemodel,Mgmodel]
    fit_models=[Bemodel]
    measurement_model=MicrowaveMultiresultModel(models,fit_models,fitself=True)
    self.register_model(measurement_model, measurement='measurement_name', fit=True,nresults=2)
    
    if overwrite_namespace is true (set true by default), when measurement_model is instantiated, the submodel's namespaces are overwritten to prepend the namespace of 
    MicrowaveMultiresultModels before each one. E.g. if MicrowaveMultiresultModel's namespace is 'microwave', then Bemodel and Mgmodel's namespaces will be overwritten 
    as microwave.be_ions and microwave.mg_ions. In addition to saying which subset of the submodels you want to fit in the models_dictionary, you can say whether 
    a fit should be called for the multiresult model (on a calculation) on instantiation of the measurement model where fitself=True is set. By default this is false

    Alternatively to this above method, a specific multimeasurement model can be created that handles generating all subscans already, and then instantiating the model
    can be handled all in one call if the subset of result models doesn't change. e.g. the above MicrowaveMultiResultModel can create all these submodels call the build method
    itself. A dictionary is also created in the build method that is not strictly necessary either, but may be used to help access the datasets by name for example in a calculation.
    
    **Model/ScanModel functions overriden here**

    - model.attach is overridden to attach each submodel to the scan, as well as the MultiresultModel so that every model, including this one, can access
      dynamically sent info from the scan class.
    - init_datasets, write_datasets,reset_state overridden in the initialization phase to call these for all submodels, and if desired, the multiresultmodel itself by
      enabling multiresult_data=True (true by default, useful for calculations)
    - mutate_datasets/mutate_plots overridden assuming to take in arrays or lists of data respectively and call the function for each submodel. However,
      mutate_plots also checks for single data values assumed to be calculations of the multiresult model.
    
    **Model/ScanModel functions not overriden here**
    
    - scan.py loops over fits using the multiresultmodel's self.fit_models list. A fit for a calculation in the multiresult model can be done by either using the above
      instantiation example with fitself=True, or adding self to the fit_models array (see build method below).
    - Calculations can be defined inside submodels for individual measurements, or here directly in the MultiresultModel, allowing access to all results
      Submodel only calculations would need to be registered seperately from the registration of this multiresultmodel, i.e. if you register this multiresult
      model as a calculation, it is assumed that calculate is defined for this multiresultModel. Otherwise, if you would like to do a calculation(s) for a submodel(s)
      only, you should additionally register that submodel seperately as a calculation.
    - auto_tracking currently assumes you have a main_fit for this multiresult model, i.e. from a calculation. If you would like to track a result from a submodel,
      register that submodel again with auto_tracking=True so that it is clear what model you would like to autotrack.
    - simulation_args,simulate not overridden, these are looped over in the scan.py definitions of simulate_measure and init_simulations because lists of dictionaries for _simulation_results not functional
    
    **Organization of datasets**

    See scan_model.py for how a single dataset is organized. For a multiresult model, every submodel will be under the given measurement.result_name
    e.g.
    - **<namespace>.measurement.submodel1_namespace** 
        - **<namespace>.measurement.submodel1_namespace.stats** Contains statistical data, raw data from the scan, and the list of scan points.
        - **<namespace>.measurement.submodel1_namespace.fits:** Contains all fit data
        - **<namespace>.measurement.submodel1_namespace.plots:** Contains all data necessary to plot the scan
    - **<namespace>.measurement.submodel2_namespace** 
        - **<namespace>.measurement.submodel2_namespace.stats** Contains statistical data, raw data from the scan, and the list of scan points.
        - **<namespace>.measurement.submodel2_namespace.fits:** Contains all fit data
        - **<namespace>.measurement.submodel2_namespace.plots:** Contains all data necessary to plot the scan
    - **<namespace>.measurement** 
        - **<namespace>.measurement.stats** Contains statistical data for a multiresult_model calculation using the above subresults
        - **<namespace>.measurement.fits:** Contains fit data for a multiresult_model fit on a calculation
        - **<namespace>.measurement.plots:** Contains plot data for a multiresult_model on calculation data
        
    :param models_dict: Dictionary of models keyed by their name (namespace) e.g. models_dict["rsb"]=rsb_model
    :type models_dict: dictionary
    :param models: list of all submodels for each result. Assumed that this measurement will return nresults given by the number of submodels in self.models
    :type models: list
    :param fit_models: list of all submodels to fit. This list should be filled with any submodels in self.models that you would like to fit
    :type fit_models: list
    :param overwrite_namespace: By default overwrite all submodels namespaces to prepend this multiresultmodel's namespace
    :type overwrite_namespace: bool
    :param multiresult_data: Enables the above datasets under <namespace>.measurement.stats,plots,fits etc to be created for a calculation. Assumed to always be true, disabling makes the datasets not be created.
    :type multiresult_data: bool
    
    """
    
    models_dict={}
    models=[]
    fit_models=[]
    multiresult_data=False #By defualt init_datasets will call super().init_datasets, creating stats, plots, fit, and if enable_histograms histograms, but setting this to False disables all of these
    overwrite_namespace=True #By default overwrite all submodels namespaces to prepend this multiresultmodel's namespace
    enable_histograms=False #False by default assuming a calculation only don't need histogram here
    def build(self,models,fit_models=None,fitself=False,**kwargs):
        namespace=self.namespace
        self.models=models
        self.fit_models=fit_models
        for model in self.models:
            name=model.namespace
            self.models_dict[name]=model
            if self.overwrite_namespace:
                model.namespace=namespace+"."+name
                model.build()
        if fitself:
            self.fit_models.append(self)
        super().build(**kwargs)
    def reset_state(self):
        """Reset state variables for every subscan and this scan"""
        super().reset_state()
        for model in self.models:
            model.reset_state()

    def attach(self, scan):
        """ Attach a scan to the model.  Gather's parameters of the scan -- such as scan.nrepeats, scan.npasses,
        etc. --  and sets these as attributes of the model. Then attach each submodel in self.models, TODO: possibly self.fit_models but need to think about this."""
        super().attach(scan)
        for model in self.models:
            model.attach(scan)
    def init_datasets(self, shape, plot_shape, points, dimension=0):
        """Initializes all datasets pertaining to scans for every submodel.  This method is called by the scan during the initialization
        stage. If self.multiresult_data is true all datasets are initialized for the multiresult model as well."""
        if self.multiresult_data:
            ###Note, this creates plots, stats, fit, and if enable_histograms true histograms. 
            ###If the user doesn't like the sizing of these datasets override this init_datasets to the size arrays/plots etc you would like
            super().init_datasets(shape,plot_shape,points,dimension=0)
        for model in self.models:
            model.init_datasets(shape,plot_shape,points,dimension=0)

    def write_datasets(self, dimension):
        """Writes all internal values to their datasets.  This method is called by the scan when it is resuming from a
         pause to restore previous scan values to their datasets."""
        if self.multiresult_data:
            ###see comment in init_datasets for overriding this
            super().write_datasets(dimension)
        for model in self.models:
            model.write_datasets(dimension)

    def mutate_datasets(self, i_point, poffset, point, counts):
        """calls mutate_datasets for every submodel, returns array of means, errors of all submodels
        """
        means=[]
        errors=[]
        i=0
        for model in self.models:
            mean,error=model.mutate_datasets(i_point,poffset,point,counts[i])
            #print(counts[i])
            means.append(mean)
            errors.append(error)
            i+=1

        return means,errors

    def mutate_plot(self, i_point, x, y, error=None, dim=None):
        """if y is an array, mutate_plot of every submodel, else assume that it is a single float that was the result of a calculation for the
           multiresult_model, and mutate_plot the multiresult_model with the point.
        """
        ###checking y can be called len(y), so y can be a list or np array and be indexed [i] if true, otherwise assume it's just a single value
        
        if hasattr(y, "__len__"):
            i=0
            for model in self.models:
                model.mutate_plot(i_point,x,y[i],error[i],dim)
                i+=1
        else:
            ###calculation has been done and y is a single float, mutate plot of the multiresult_model. Assuming multiresult_data is True
            super().mutate_plot(i_point,x,y,error,dim)