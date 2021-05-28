Getting Started with Scans
============================

When learning how to use the scan framework, it is best to start with creating a basic 1D scan.

Creating a 1D Scan
----------------------------

In order to create a 1D scan experiment, a few basic requirements are needed:

1. Create an experiment that inherits from :code:`scan_framework.scans.scan.Scan1D`.
2. (optional) Call :code:`super().build()` to create the :code:`self.core` and :code:`self.scheduler` devices.
3. Call :code:`self.scan_arguments()` in the build method to add GUI arguments for configuring the scan.
4. Create an instance of a scan model and register it by calling :code:`register_model()` in either :code:`build()`
   or :code:`prepare()`.
5. Implement the :code:`get_scan_points()` method to return the scan points.  Typically this just returns a GUI argument
   of type :code:`Scannable`, but can return any object that is iterable such as a list or a numpy array.
6. Implement the :code:`measure()` method.  The measure method is called automatically at each repetition of each scan
   point and executes a sequence of ARTIQ instructions to perform a measurement at each scan point.  It must return
   an integer, which typically is the number of PMT counts collected during a detection.

A basic 1D scan might look something like:

.. code-block:: python

    from scan_framework.scans import *
    from my_repository.models.my_model import MyModel


    class MyScan(Scan1D, EnvExperiment):

        def build(self):
            super().build()

            # Create the scan range GUI argument.
            self.setattr_argument('frequencies', Scannable(default=RangeScan(
                start=450*MHz,
                stop=550*MHz,
                npoints=50),
                scale=1*MHz,
                ndecimals=4,
                unit="MHz"))

            # Create the GUI arguments for scan configuration.
            self.scan_arguments()

        def prepare(self):
            # Create and register the Scan Model.
            self.model = MyModel(self)

            # Setting measurement=True
            #   Instructs the framework to calculate statistics using the model and to also
            #   store all collected or calculated data using the model (i.e. under its namespace).
            #
            # Setting fit=True
            #    Instructs the framework to perform a fit on the calculated mean values using the fit function
            #    specified by the model's `fit_function` attribute.
            self.register_model(self.model, measurement=True, fit=True)

        def get_scan_points(self):
            # Return the set of scan points to the framework.
            return self.frequencies

        @kernel
        def measure(self, point):
           # `point` is set to the value of the current scan point.
           # In this case it is the current frequency in `self.frequencies`

           # ... cooling, pulse sequences, detection.
           return counts

Creating a Scan Model
----------------------------
All processing of scan data and data handling is performed by what is known as a scan model, which is a Python
class that extends from :code:`scan_framework.models.ScanModel` and has built-in data processing capabilities.  In
its most basic form, a scan model only needs to define a :code:`namespace` attribute, which specifies the dataset
key under which all data will be saved.  If the model is to be used for fitting, additionally the :code:`fit_function`
and :code:`main_fit` attributes need to be specified.

A very basic scan model might look something like:

.. code-block:: python

    from scan_framework.models import *


    class MyScanModel(ScanModel):
        # All datasets will be created under the dataset key given by the namespace attribute.
        namespace = 'microwaves.%transition'

        # Specifies what fit function to use
        @property
        def fit_function(self):
            if self.type == 'frequency':
                return fit_functions.RabiSpectrum
            if self.type == 'time':
                return fit_functions.Sine

        # Specifies the fit param of interest.  This fit param will be broadcast and persisted.
        @property
        def main_fit(self):
            if self.type == 'frequency':
                return 'frequency'
            if self.type == 'time':
                return 'pi_time'

Here, the :code:`fit_function` property specifies what fit function to use during fitting and the :code:`main_fit`
property specifies the name of the fitted param of interest that is to be saved for later use (e.g. a transition
frequency or a pi time).  If 'Fit and Save' is selected in the GUI, and a fit was successful, the fit param named
by :code:`main_fit` will be broadcast, persisted, and saved/archived to the datasets.

.. note::
    By default, all dataset except the :code:`main_fit` dataset are created with :code:`broadcast=False, persist=False, save=True` as to
    not clutter up the datasets in the dashboard but still be available in the hdf5 file for post-processing.  See
    the :ref:`models` section for more details.


The :code:`%transition` portion of the :code:`namespace` attribute is an optional token that will be replaced with
the value of the scan model attribute named :code:`transition`, if it exists.