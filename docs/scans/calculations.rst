Performing calculations
---------------------------------------------
Calculations can be performed and written to datasets after each scan point.  To use calculations, create a model
for the calculation and register it with the scan with the name :code:`calc_model` (or simple assign :code:`self.calc_model`
to the model instance in your scan).  After each scan point, a method named :code:`calculate()` which you define in the
model will be called and passed the index of the current scan point.  The :code:`calculate()` method must then return a
tuple of (value, error) which is the calculated value and it's error.  Datasets under the calc model's namespace and
the mirror namespace will be mutated with these calculated values after each scan point.  See
:code:`scans/heating_rate_scan.py` and :code:`lib/models/heating_rate.py` for examples.
