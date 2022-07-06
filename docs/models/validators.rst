.. _model-validators:

Validating fitted parameters
============================

Validators are specified in a model by creating property methods (using the :code:`@property` decorator).
There are three types of validations performed for fitting; **pre-validation**, **validation**, and **strong-validation**.
Pre-validation determines if a fit should even be attempted.  Validation determines if the fit was successful and
generates warnings when it was not.  Strong validation works exactly like validation, but prevents any fitted parameters
from being saved when the fit was not successful.

To validate a fitted parameter of the model's fit function, set a key of :code:`params.<param_name>`.  To perform
validations on custom fit parameters defined by the model's `fit_map` attribute, set a key of :code:`<custom_param_name>`
with the :code:`params.` prefix omitted.  See the Strong Fit Param Validators example below.

The three types of validators
---------------------------------

Pre-Validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
These are specified in the model with a :code:`pre_validators` property method.  They validate the data series being fit
prior to performing the fit.  If any rule fails, the fit is not performed, a "Can't Fit" message is printed, and the
scan is allowed to complete.

Example:

.. code-block:: python

    @property
    def pre_validators(self):
        return {
            # validation performed on the data series to be fit
            "y_data": {
                # fit only performed if max(means) - min(means) > 1
                "height": {
                    'min_height': 1
                }
            }
        }

Fit Param Validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
These are specified in the model with a :code:`validators` property method.  They validate the fitted parameters after
the fit has been performed.  If any rule fails, a "Bad Fit" message is printed, the fit line is plotted, the fitted
parameters are saved (if enabled in GUI) and the scan  is allowed to complete.

Example:

.. code-block:: python

    @property
    def validators(self):
        return {
            # validates the fitted value of fit function's 'pi_time' argument
            "params.pi_time": {
                'between': [90*us, 110*us],
                'max_change': [0.01*us, self.get_main_fit()]
            },
            "analysis.reg_err": {
                "less_than": 0.1
            },
            "analysis.r2": {
                "greater_than": 0.6
            }
        }

.. note::
    :code:`params.pi_time` refers to an actual parameter of the fit function and not to a custom fit parameter.**

Strong Fit Param Validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
These are specified in the model with a :code:`strong_validators` property method.  They validate the fitted parameters
after the fit has been performed.  If any rule fails, a "Bad Fit" message is printed, the fit line is plotted, but the
fitted parameters are not saved (even if enabled in GUI).  The scan is allowed to complete.

Example:

.. code-block:: python

    @property
    def strong_validators(self):
        return {
            # validates a custom 'frequency' param defined by the 'fit_map' attribute
            "frequency": {
                # no fitted params are saved if the fitted frequency is outside the scan range
                "between": {
                    "min_": self.scan.points[0],
                    "max_": self.scan.points[-1]
                }
            }
        }

Validation Methods
---------------------------------


Builtin Validation Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
These are defined in :code:`artiq_scan_framework.models.model.py` and are available to all models.

    - :code:`greater_than(min_)`
    - :code:`less_than(max_)`
    - :code:`between(min_, max_)`
    - :code:`max_change(max_diff, prev_value)`
    - :code:`height(min_height, error_msg=None)`

User Defined Validation Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Any class method of your model can also be specified as the validation method.  For fit param validations, the first
argument passed to your method is the param name, the second is the param value, and the remaining are any arguments
passed in from your validator rule.  For data series validators, the first is the name of the series, the second is the
data series array it self, and the remaining are any arguments passed in from your validator rule.

Custom validation methods return True if the validation passes, or False if the validation fails.  If validation fails,
the method also needs to add an errors message to self.validation_errors.

For Example:

.. code-block:: python

    @property
    def pre_validators(self):
        return {
            "y_data": {
                "my_height_validator": {
                    'min_height': 1
                }
            }
        }

    def my_height_validator(series_name, data, min_height):
        height = max(data) - min(data)
        if height >= min_height:
            return True
        else:
            error_msg = "Amplitude of {0} less than minimum amplitude allowed for {1} of {2}"
            self.validation_errors[series_name] = error_msg.format(round(height,1), series_name, min_height)
            return False
