
Time & frequency scans
---------------------------------------------
The scan that accompanies the :code:`MicrowavesModel` example above would need to create GUI arguments for specifying
both the scanned frequency and time ranges, what type of scan to perform (time or frequency), and pass on the type of
scan (frequency or time) to the model by setting :code:`self.model.type`.  Additionally, overrides would be needed to
pass either a frequency or a time value to the measure method depending on the type of scan.  This overhead can be
taken care of automatically by inheriting from :code:`scan_framework.scans.extensions.TimeFreqScan` instead of the base
:code:`Scan` class.  The :code:`TimeFreqScan` class also provides additional features such as **auto_tracking** of
fitted frequencies.


Time/frequency scans and frequency scans can track the last fitted value of a frequency it is scanning.  These scans
can then scan over a range of frequencies centered on the last fit value.
To use auto tracking first enable auto tracking in the scan::

    class MyScan(Scan1D, FreqScan, EnvExperiment):
        enable_auto_tracking = True
        ...

Then register an auto tracking model in the scan::

    self.model = MyModel()
    self.register_model(self.model, auto_track=True)

The last fitted frequency will be fetched from the auto tracking model and the scan points will be offset by the that
frequency automatically.

.. note::
    Auto tracking can be disabled entirely in either a :code:`FreqScan` or a :code:`TimeFreqScan` by setting
    :code:`self.enable_auto_tracking = False` in the scan.


In a time/frequency scan (:code:`TimeFreqScan`), or in a frequency scan (:code:`FreqScan`), tracking of the fitted
frequency can be accomplished by enabling auto tracking and then specifying an auto tracking model:

.. code-block:: python

    def MyScan(Scan1D, TimeFreqScan, EnvExperiment):
         enable_auto_tracking = True

         ...

         def prepare(self):
              self.model = MyModel(self)
              self.register_model(self.model, auto_track=True)


This will cause the center of the scanned frequency range to always be centered on the last fitted frequency.
The min and max values of the frequency range in the GUI then specify frequencies above and below the last fitted
frequency.  In a :code:`TimeFreqScan`, the last fitted time value (e.g. pi times) will also be fetched from the model and passed to the measure
method along with the current frequency value when scanning over frequencies.  Likewise, the last fitted frequency value
will be passed to the measure method along with the current time value when scanning over times.
