Getting Started with Scans
============================

As an example of how to use the scan framework to create a scan of an experimental parameter, below steps through how
to create a 1D scan over a set of frequencies.

Creating a 1D Scan
----------------------------

To create a 1D scan, a few basic things are needed:

1. Include the scan framework classes using :code:`from artiq_scan_framework.scans import *`
2. Create an experiment that inherits from :code:`artiq_scan_framework.scans.scan.Scan1D`.
3. (optional) Call :code:`super().build()` to create the :code:`self.core` and :code:`self.scheduler` devices.
4. Call :code:`self.scan_arguments()` in the build method.
5. (optional) Create an instance of a scan model and register it by calling :code:`register_model()` in either :code:`build()`
   or :code:`prepare()`.
6. Implement the :code:`get_scan_points()` method to return the scan points.  Typically this just returns a GUI argument
   of type :code:`Scannable`, but can return any object that is iterable such as a list or a numpy array.
7. Implement the :code:`measure()` method.

Inheriting from :code:`Scan1D` provides all the logic that is needed for executing a scan.  The scan framework
then interfaces with your class by over-ridding the :code:`run()` method and calling two template methods that must be
implemented in your class -- :code:`get_scan_points()`, and :code:`measure()`.  The :code:`get_scan_points()`
method returns a list of scan points that the framework will automatically loop over, and the :code:`measure()` method
will be called multiple times at each scan point within the main loop (once at each repetition of the scan point).
The :code:`measure()` method performs a measurement at the current scan point and returns the value of that measurement
as an integer (typically a number of integer PMT counts).  You may also write your own :code:`run()` method, which
allows for greater control over the procedural flow of a scan.  See the source code for the
:meth:`run() <artiq_scan_framework.scans.scan.Scan.run>` method in the :meth:`Scan <artiq_scan_framework.scans.scan.Scan>` class.
It is easiest to copy and paste that entire run method into your class and make modifications as necessary.  A few
GUI arguments for controlling the execution of the scan are also needed.  These are created by calling
:code:`self.scan_arguments()` in the :code:`build()` method.

Finally, if you wish to use the scan framework to process the data that is generated, a scan model needs to be instantiated
and registered with the framework.  This is done by calling :code:`register_model()`.  There are a number of
arguments to the :code:`register_model()` method that instruct the framework how to use your model -- such as
if it should calculate statistics or perform a fit on the statistics generated  (see :meth:`register_model() <artiq_scan_framework.scans.scan.Scan.register_model>`
for a full listing of these arguments).  If you need to perform custom statistics or simply want more control over, say,
fitting, you can opt to not register a model and perform statistics calculations and fitting manually within the scan.
Typically, this is not needed, however.  Please consult :ref:`scans_api` for details on how to perform manual
data processing.

Following these requirements a typical, but basic, 1D scan might look something like:

.. code-block:: python

    # include all classes needed for writing scan experiments
    from artiq_scan_framework.scans import *

    # include your scan model class
    from my_repository.models.my_model import MyModel


    class MyScan(Scan1D, EnvExperiment):

        def build(self):
            # create self.core and self.scheduler
            super().build()

            # create the scan range GUI argument
            self.setattr_argument('frequencies', Scannable(default=RangeScan(
                start=450*MHz,
                stop=550*MHz,
                npoints=50),
                scale=1*MHz,
                ndecimals=4,
                unit="MHz"))

            # create GUI arguments for configuring the scan
            self.scan_arguments()

        def prepare(self):
            # create an instance of your scan model
            self.model = MyModel(self)

            # register your scan model with the framework
            # setting measurement=True
            #   instructs the framework to calculate statistics using the model and to also
            #   store all collected or calculated data under the model's namespace
            #
            # setting fit=True
            #    instructs the framework to perform a fit on the calculated mean values using
            #    the fit function specified by the model's `fit_function` attribute
            self.register_model(self.model, measurement=True, fit=True)

        def get_scan_points(self):
            # return the set of scan points to the framework
            return self.frequencies

        @kernel
        def measure(self, point):
           # `point` is set to the value of the current scan point.
           # In this case it is the current frequency in `self.frequencies`

           # ... ARTIQ commands to perform measurement: e.g. cooling, pulse sequences, detection.

           # return the result of the measurement as an integer (i.e. PMT counts)
           return counts

Creating a Scan Model
----------------------------
To process the data collected by a scan, a scan model is also needed.  All processing of scan data and data handling
is performed by the scan model, which is a Python class that extends from :class:`ScanModel <artiq_scan_framework.models.scan_model.ScanModel>`
and has built-in data processing capabilities.  In its most basic form, a scan model only needs to define a
:attr:`namespace <artiq_scan_framework.models.scan_model.ScanModel.namespace>` attribute, which specifies the dataset key under which
all data will be saved.  If the model is to be used for fitting, additionally the
:attr:`fit_function <artiq_scan_framework.models.scan_model.ScanModel.fit_function>` and
:attr:`main_fit <artiq_scan_framework.models.scan_model.ScanModel.main_fit>` attributes need to be specified.

A very basic scan model might look something like:

.. code-block:: python

    # include all classes needed for creating scan models
    from artiq_scan_framework.models import *


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

        # Specifies the fit param of interest.
        # This fit param will be broadcast and persisted to the datasets and is visible in the dashboard
        # when the fit passes any defined validations (more on validations later in this guide)
        @property
        def main_fit(self):
            if self.type == 'frequency':
                return 'frequency'
            if self.type == 'time':
                return 'pi_time'

Here, the :code:`fit_function` property specifies what fit function to use during fitting and the :code:`main_fit`
property specifies the name of the fitted param of interest that is to be saved for later use (e.g. a transition
frequency or a pi time).  If 'Fit and Save' is selected in the GUI, and a fit was successful, the fit param named
by :code:`main_fit` will be broadcast, persisted, and saved to the datasets.

.. note::
    By default, all dataset except the :code:`main_fit` dataset are created with :code:`broadcast=False, persist=False, save=True` as to
    not clutter up the datasets in the dashboard but still be available in the hdf5 file for post-processing.  See
    the :ref:`models` section for more details.


Finally, the :code:`%transition` portion of the :code:`namespace` attribute is an optional token that will be replaced with
the value of the scan model attribute named :code:`transition`, if it exists.