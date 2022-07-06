Time & frequency scans
======================
Scans over a range of time values or frequency values are common.  To simplify the process of writing these
types of scans, the scan framework provides three base classes from which a scan may inherit.  These
base classes are :class:`TimeScan<artiq_scan_framework.scans.extensions.TimeScan>`,
:class:`FreqScan<artiq_scan_framework.scans.extensions.FreqScan>`, and
:class:`TimeFreqScan<artiq_scan_framework.scans.extensions.TimeFreqScan>`.  Additionally, any of these scans
can also use auto-tracking or set :code:`self._x_offset` to offset the scan points.  See :ref:`auto_tracking`.

Time scans
----------
Time scans create a configurable GUI argument for entering a range of times to scan over.  To create a time
scan, simply inherit from the :class:`TimeScan<artiq_scan_framework.scans.extensions.TimeScan>` class and call
:meth:`scan_arguments()<artiq_scan_framework.scans.scan.Scan.scan_arguments>` in :code:`build()`.

.. code-block:: python

    from artiq_scan_framework.scans import *


    class MyTimeScan(Scan1D, TimeScan, EnvExperiment):

        def build(self):
            ...
            # scan_arguments() creates an additional GUI argument for entering a time range
            self.scan_arguments(
                # the GUI argument can be fully configured via the 'times' argument
                times={
                    'start':0,
                    'stop':100*us,
                    'npoints':50,
                    'unit': 'us',
                    'scale': us,
                    'global_step': 1*us,
                    'ndecimals': 0
                }
            )

When creating a time scan it is not necessary to define the :meth:`get_scan_points()<artiq_scan_framework.scans.scan.Scan.get_scan_points>`
callback method;  the framework will automatically scan over the GUI argument named 'times'.

The scan model that is registered with a time scan can also inherit from the
:class:`TimeModel<artiq_scan_framework.models.time_model.TimeModel>` class which automatically
sets the :attr:`x_units<artiq_scan_framework.models.scan_model.ScanModel.x_units>` and
:attr:`x_label<artiq_scan_framework.models.scan_model.ScanModel.x_label>`
attributes of the scan model.

Frequency scans
---------------
Frequency scans create a configurable GUI argument for entering a range of frequencies to scan over.  To create a
frequency scan, simply inherit from the :class:`FreqScan<artiq_scan_framework.scans.extensions.FreqScan>` class and call
:meth:`scan_arguments()<artiq_scan_framework.scans.scan.Scan.scan_arguments>` in :code:`build()`.

.. code-block:: python

    from artiq_scan_framework.scans import *
    from artiq_scan_framework.models import *


    class MyFreqScan(Scan1D, FreqScan, EnvExperiment):

        def build(self):
            super().build()

            # scan_arguments() creates an additional GUI argument for entering a frequency range
            # the range of frequencies is set to the attribute named 'frequencies' (i.e. self.frequencies)
            self.scan_arguments(
                # the GUI argument can be fully configured via the 'frequencies' argument
                frequencies={
                    'start': -0.1 * MHz,
                    'stop':  0.1 * MHz,
                    'npoints': 50,
                    'unit': 'MHz',
                    'scale': MHz,
                    'global_step': 0.1*MHz,
                    'ndecimals': 1
                }
            )

        def prepare(self):
            # -- like all scans, frequency scans can also use auto-tracking to center a relative scan
            # range about a fixed frequency

            # Create a default fitted frequency for the first run when no fits have been performed yet
            self.set_dataset('example.defaults.frequency', 1*MHz, broadcast=True)
            model = ScanModel(self,
                              namespace='example',
                              main_fit='frequency',
                              # tell framework to use default value above when no fit exists
                              default_fallback=True
                              )

            self.register_model(model, auto_track='fit', measurement=True)


When creating a frequency scan it is not necessary to define the :meth:`get_scan_points()<artiq_scan_framework.scans.scan.Scan.get_scan_points>`
callback method;  the framework will automatically scan over the GUI frequencies argument.

The scan model that is registered with a frequency scan can also inherit from the
:class:`FreqModel<artiq_scan_framework.models.freq_model.FreqModel>` class which automatically
sets the :attr:`x_units<artiq_scan_framework.models.scan_model.ScanModel.x_units>` and
:attr:`x_label<artiq_scan_framework.models.scan_model.ScanModel.x_label>`
attributes of the scan model.

Time/frequency scans
------------------------
Time/frequency scans are provided for scans that need to scan over either a range of frequencies or
a range of times.  This is useful for scans of atomic transitions which need to find both the transition
frequency and the appropriate pi time for the transition.  Creating a :class:`TimeFreqScan<artiq_scan_framework.scans.extensions.TimeFreqScan>`
significantly simplifies these types of scans.  Inheriting from
:class:`TimeFreqScan<artiq_scan_framework.scans.extensions.TimeFreqScan>`

    1. Creates two GUI arguments for entering either a range of frequencies or a range of times.
    2. Creates a GUI argument for specifying if the scan should scan over the range of frequencies or times.
    3. Centers the frequency range about the last fitted frequency when auto-tracking is used.
    4. Determines the scan points automatically (:code:`get_scan_points()` does not need to be implemented).
    5. Uses the last fitted pi time for frequency scans when using auto-tracking.
    6. Uses the last fitted frequency for time scans when using auto-tracking.
    7. Provides a GUI argument to enter the pulse time for frequency scans when auto-tracking is not being used.
    8. Provides a GUI argument to enter the frequency for time scans when auto-tracking is not being used.
    9. Passes both the frequency and time as arguments to the :code:`measure()` method.

To create a Time/frequency scan, simply inherit from the
:class:`TimeFreqScan<artiq_scan_framework.scans.extensions.TimeFreqScan>` class and call
:meth:`scan_arguments()<artiq_scan_framework.scans.scan.Scan.scan_arguments>` in :code:`build()`.  If you are also
using auto-tracking, register a single auto-tracking scan model and use the
:attr:`type<artiq_scan_framework.models.scan_model.ScanModel.type>` attribute in the scan model to dynamically
determine the fit function, main fit, etc based on the type (frequency or time) of scan being performed.
For a full example of a :class:`TimeFreqScan<artiq_scan_framework.scans.extensions.TimeFreqScan>` class that uses
auto-tracking, see the example below.

.. note::

    The scan model that is registered for a time/frequency scan can also inherit from the
    :class:`TimeFreqModel<artiq_scan_framework.models.time_freq_model.TimeFreqModel>` class which automatically
    sets the :attr:`x_units<artiq_scan_framework.models.scan_model.ScanModel.x_units>` and
    :attr:`x_label<artiq_scan_framework.models.scan_model.ScanModel.x_label>`
    attributes of the scan model.

.. note::

    Scan models can also be registered with the :code:`bind` argument set to True in time/frequency scans.
    i.e. :code:`self.register_model(my_model_instance, bind=True)`.  This will cause the model to be
    re-bound after its :code:`type` attribute is set to the current scan type (time or frequency).  This
    is useful if you need to create a dynamic namespace that includes a token for the type of scan.
    e.g. :code:`namespace = 'microwaves.%type'`.  :code:`%type` will be replaced by either 'frequency' or 'time' when
    the model is registered with :code:`bind=True`.


.. code-block:: python

    from artiq_scan_framework.scans import *
    from artiq_scan_framework.models import *
    from artiq_scan_framework.analysis.curvefits import AtomLine, Sine
    import random


    class MicrowaveScan(Scan1D, TimeFreqScan, EnvExperiment):
        """Microwave scan

        Scans frequencies and pulse times of microwave transitions
        """

        def build(self, **kwargs):
            super().build(**kwargs)

            # The atomic transition, identified by an integer to simply logic in
            # the "measure()" method
            self.setattr_argument('transition', EnumerationValue(
                ['0', '1', '2', '3', '4', '5', '6', '7'],
                default='1'))

            # scan settings, scan ranges, etc.
            self.scan_arguments(
                # frequency range can be customized
                frequencies={
                    'start': -0.3*MHz,
                    'stop': 0.3*MHz
                },
                # time range can also be customized
                times={
                    'start': 0*us,
                    'stop': 20*us
                }
            )

            # create devices, instantiate libs, etc.
            ...

        def prepare(self):
            # convert string transition to integer for the "measure()" method
            self.transition = int(self.transition)

            # create and register the scan model
            self.model = MicrowavesScanModel(self,
                 # set the model's transition attribute to the selected transition in the GUI.
                 # this allows the %transition token in the model namespace to be replaced
                 # by the current transition.
                 transition=self.transition
            )
            self.register_model(self.model,
                                # calculate statistics and store all data to the datasets
                                measurement=True,
                                # perform a final fit to the data
                                fit=True,
                                # points will be offset by this model's last fitted frequency value
                                # (a.k.a. it's main fit)
                                auto_track='fit')

        @kernel
        def initialize_devices(self):
            self.core.reset()

        @kernel
        def measure(self, time, frequency):
            self.cooling.doppler()

            if self.transition >= 2:
                self.microwaves.transition_1()
            if self.transition >= 3:
                self.microwaves.transition_2()
            if self.transition >= 4:
                self.microwaves.transition_3()
            if self.transition >= 5:
                self.microwaves.transition_4()

            # pulse dds
            self.microwaves.set_frequency(frequency)
            self.microwaves.pulse(time)

            # detect
            counts = self.detection.detect()
            return counts


    class MicrowavesScanModel(TimeFreqModel):
        """Microwave scan model

        Processes data from microwave scans
        """

        # %transition will be replaced by the transition selected in the GUI
        namespace = 'microwaves.%transition'
        y_label = 'Counts'

        # scales for formatting fit params printed to the log window
        scales = {
            'f': {
                'scale': MHz,
                'unit': 'MHz'
            },
            'phi': {
                'scale': 3.14159,
                'unit': 'pi'
            },
            'f0': {
                'scale': MHz,
                'unit': 'MHz'
            },
            'Omega0': {
                'scale': MHz,
                'unit': 'MHz'
            },
            'T': {
                'scale': us,
                'unit': 'us'
            }
        }

        @property
        def main_fit(self):
            if self.type == 'frequency':
                # save fit param 'f0' to dataset named 'frequency'
                return ['f0', 'frequency']
            if self.type == 'time':
                # save calculated fit param 'pi_time'
                return 'pi_time'

        def before_validate(self, fit):
            # calculate the fit param 'pi_time' from the fit param 'f'
            if self.type == 'time':
                fit.fitresults['pi_time'] = 1/(2*fit.fitresults['f'])

        @property
        def fit_function(self):
            if self.type == 'frequency':
                # frequency scans use the AtomLine fit function
                return AtomLine
            elif self.type == 'time':
                # times scans use the Sine fit function
                return Sine
            else:
                raise Exception('Unknown scan type {}'.format(self.type))

        @property
        def man_scale(self):
            # fit parameter scales, used by analysis.curvefits while fitting
            if self.type == 'frequency':
                return {
                    'A': 1,
                    'Omega0': 1 / (10 * us),
                    'T': 1 * us,
                    'f0': 1 * GHz,
                    'y0': 1
                }
            else:
                return {
                    'A': 10,
                    'f': 1 / (10 * us),
                    'phi': 1,
                    'y0': 1
                }

        @property
        def guess(self):
            # fit parameter guesses, used by analysis.curvefits while fitting
            if self.type == 'time':
                if self.transition in [1, 3, 5, 6, 7]:
                    return {
                        'phi': 0.5*3.14159,
                        'y0': 5,
                        'A': 5,
                    }
                else:
                    return {
                        'phi': 1.5*3.14159,
                        'y0': 5,
                        'A': 5,
                    }
            else:
                return {
                    'T': self.get('pi_time', archive=False)
                }