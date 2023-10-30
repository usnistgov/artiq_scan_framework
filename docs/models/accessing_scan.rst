Accessing the scan inside a scan model
======================================

The scan experiment that created a scan model can always be accessed via the attribute :code:`self._scan` inside
the scan model (once the :code:`_initialize()` method of the scan class has executed).  This can be particularly useful
in attributes defined as properties via :code:`@property`.  Checks can then be performed on attributes of the scan class
inside :code:`@property` methods in the scan model to dynamically determine the appropriate value for a particular
configuration.

For example, the fit function to use for fitting could be set via a GUI argument using this method:

.. code-block:: python

    from artiq.experiment import *
    from artiq_scan_framework import *


    class MyModel(ScanModel):
        namespace = "my_namespace"

        @property
        fit_function(self):
            if self._scan.fit_function == 'Sin':
                return fitting.Sine
            if self._scan.fit_function == 'RabiSpectrum':
                return fitting.RabiSpectrum

        ...


    class MyScan(Scan1D, EnvExperiment):

        def build(self):
            super().build()
            self.scan_arguments()
            self.setattr_argument('fit_function', EnumerationValue([
                'Sin',
                'RabiSpectrum',
            ]))

        ...

Alternatively, the same can be accomplished by simply setting the scan model's :code:`fit_function` attribute directly
in the scan based off the :code:`fit_function` argument.  The ability to access the scan instance via :code:`self._scan`
within a scan model may be necessary or more convenient, however, in other circumstances.