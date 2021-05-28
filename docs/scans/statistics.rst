
Calculating statistics and fitting in a scan
==============================================

Calculating statistics and mutating datasets
-----------------------------------------------

Statistics of the values returned by a scan's :code:`measure()` method can be automatically generated
by registering a class that extends from :code:`ScanModel`

All model datasets are mutated as data becomes available during the scan.  After each scan point, the model datasets
are mutated.

Fitting
---------------------
Fitting is automatically performed at the end of a scan on all registered fit models when
:code:`self.enable_fitting` is set to :code:`True`.  The model's data will be fit to the function specified by its
:code:`fit_function` attribute.  To perform fitting, register a fit model in the scan class:

.. code-block:: python

    self.model = MyScanModel(self)
    self.register_model(self.model, measurement=True, fit=True)

The :code:`fit_data()` method of each registered fit model will be called automatically, which in turn passes
the model's :code:`x` and :code:`mean` datasets to the :class:`~scan_framework.analysis.curvefits.Fit` class
to perform the fit.

The provided curvefits package uses four arguments when performing fits: :code:`hold`, :code:`man_guess`,
:code:`man_bounds`, and :code:`man_scale`.  Each of these arguments are specified within the model to hold
fit parameters at fixed values, provided initial guesses, bound fit parameters, and set the scale of a
fit parameters respectively.  In the scan model, the :code:`guess` attribute sets  fit guesses, the
:code:`man_scale` attribute sets fit scales, the :code:`man_bounds` attribute sets fit bounds, and the
:code:`hold` attribute specifies which parameters should be held.

.. code-block:: python

    class MyScanModel(ScanModel):
        namespace = "my_scan_model"
        fit_function = fitting.Power

        guess = {
            'A': 1,
            'alpha': 2,
            'y0': 0
        }
        man_scale = {
            'A': 1,
            'alpha': 1,
            'y0': 1
        }
        man_bounds = {
            'A': [.9, 1.1],
            'alpha': [1.5, 2.5]
        }
        hold = {
            'y0': 0.0
        }

        # 3. Specify the fit param to save
        main_fit = ''


Setting fit guesses in the GUI
------------------------------
Fit guesses may also be set in the dashboard GUI using fit guess arguments.  Fit guess arguments are created
just like ARTIQ :code:`NumberValue()` GUI arguments except that the :code:`FitGuess` processor is used instead.
For example, a fit guess for the fit param named :code:`alpha` can be entered in the GUI by creating a
fit guess argument in the :code:`build()` method of the scan:

.. code-block:: python

    def build(self):
        self.setattr_argument('guess_alpha', FitGuess(
            fit_param='alpha',
            default=2.0,
            scale=1.0,
            unit='',
            use='ask',
            step=0.1
        ))

When submitted, the framework will register :code:`self.guess_alpha` as the guess for the fit param named :code:`alpha`
and will use this as the initial guess for :code:`alpha` when performing fits.  The name of the fit param is always
explicitly set using the :code:`fit_param` argument to :code:`FitGuess(...)`.  The :code:`use` argument of
:code:`FitGuess(...)` specifies when to use the guess in fitting and can take on one of three values:

1. :code:`use='ask'`: An additional checkbox will be created to manually enable/disable using the guess during fitting.
2. :code:`use=True`: The guess is always used during fitting.
3. :code:`use=False`: The guess is never used during fitting.  Either the guess defined in the scan model or an auto-generated
   guess from the :code:`FitFunction` class will be used.

Any argument accepted by the ARTIQ :code:`NumberValue(...)` processor can be passed to `FitGuess()` to adjust the
scale, unit, step size, etc.

Fit Validations
---------------------------------------------
To ensure that incorrect fitted parameters are not saved, three types of validators can be defined in any :code:`ScanModel`
that perform fits for the scan.

1. Pre-Validators:
    These run on the data to be fit prior to performing a fit.  If any pre-validator of a model fails, a fit will not
    be performed by that model.  Pre-validators are defined by the :code:`pre_validators` property of a :code:`ScanModel`.
2. Fit Param Validators:
    These validate the fitted parameters after a fit is performed.  If any fail, a warning message will be displayed in
    the logs to notify the user. Fit param validators are defined by the :code:`validators` property of a :code:`ScanModel`.
3. Strong Fit Param Validators:
    These also validate fitted parameters after a fit is performed.  If any strong validators fail, an error message is
    displayed and the model's 'main fit' will **not** be saved.  Strong fit param validators are defined by the
    :code:`strong_validators` property of a :code:`ScanModel`.

Pre-validators are useful as a pre-check that the data provided is in the right range or has the correct features
before attempting a fit.  Both fit param validators are useful to ensure that the fitted parameters are not outside
some range of acceptable values.

See the :ref:`Model Validators<model-validators>` section for details about each type of validation and how to define
validators.
