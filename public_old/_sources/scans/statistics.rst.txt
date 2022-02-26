
Processing and handling of scan data
====================================

All processing of data is performed by a scan model, which is registered to instruct the framework
to use this model for specific data processing tasks.

Generating statistics and mutating datasets
-------------------------------------------

The mean of measured values at each scan point and the standard error of this mean value are generated
by registering a class of type :class:`ScanModel<scan_framework.models.scan_model.ScanModel>` with the :code:`measurement`
argument set to the name of the measurement (or simply to True in the case of a single measurement).  For the
case of a single measurement, executing

.. code-block:: python

    self.model = MyScanModel(self)
    self.register_model(self.model, measurement=True)

instructs the framework to calculate the mean and standard error after each scan point completes and to mutate
the corresponding :ref:`datasets<datasets>` with these values.  The standard framework :ref:`applets<applets>`
then plot the mean and standard error after each scan point completes.

This greatly simplifies the task of data processing, as the framework handles data processing for you with a
single call to :meth:`register_model()<scan_framework.scans.scan.Scan.register_model>`.  If, however, more control over the generation of statistics and mutating
of datasets is needed, the :meth:`mutate_datasets()<scan_framework.models.scan_model.ScanModel.mutate_datasets>` method
can be overridden in the scan model class that is registered.

Histograms are also generated and updated at the end of each scan point by registering a model as a
'measurement' model (i.e. by setting the :code:`measurement` argument as shown above)

Performing fits
---------------
A final fit of a function to the generated mean values is performed by registering a class of type
:class:`ScanModel<scan_framework.models.scan_model.ScanModel>` with the :code:`fit` argument set to the name of the
fit (or simply to True in the case of a single fit).  Usually this is the same scan model registered
to generated statistics but this is not strictly required -- any registered fit model will simply perform a fit on the values
that it finds for the :code:`points` and :code:`mean` datasets under its namespace.

For the case of a single measurement and a single fit, executing

.. code-block:: python

    self.model = MyScanModel(self)
    self.register_model(self.model, measurement=True, fit=True)

instructs the framework to generate statistics and perform a fit to these statistics at the end of the scan using
the specified scan model.  The model's data will be fit to the function specified by its :code:`fit_function` attribute.

The :meth:`fit_data()<scan_framework.models.scan_model.ScanModel.fit_data>` method of every registered fit model is called
by the framework when the scan completes.  The :meth:`fit_data()<scan_framework.models.scan_model.ScanModel.fit_data>` method
then fetches the data to use in the fit via :meth:`get_fit_data()<scan_framework.models.scan_model.ScanModel.get_fit_data>`,
which returns the contents of the :code:`points` and :code:`mean` datasets.  Either of these methods may be
overridden in the scan model if more control over the fitting procedure is needed.

Fitting is then performed by :mod:`curvefits<scan_framework.analysis.curvefits>` package, which uses four arguments
when performing fits: :code:`hold`, :code:`man_guess`, :code:`man_bounds`, and :code:`man_scale`.  Each of these
arguments can be specified within the model to hold fit parameters at fixed values, provided initial guesses, bound
fit parameters, and set the scale of a fit parameters respectively.  In the scan model, the :code:`guess` attribute
sets  fit guesses, the :code:`man_scale` attribute sets fit scales, the :code:`man_bounds` attribute sets fit bounds,
and the :code:`hold` attribute specifies which parameters should be held.

For example, the following scan model specifies a fit function, guesses for the fit params,

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

Avoiding bad fits: fit validations
----------------------------------
To ensure that incorrect fitted parameters are not saved, three types of validators can be defined in any
:class:`ScanModel<scan_framework.models.scan_model.ScanModel>` that perform fits for the scan.

1. Pre-validators:
    These run on the data to be fit prior to performing a fit.  If any pre-validator of a model fails, a fit will not
    be performed by that model.  Pre-validators are defined by the
    :attr:`pre_validators<scan_framework.models.scan_model.ScanModel.pre_validators>` property of the
    :class:`ScanModel<scan_framework.models.scan_model.ScanModel>`.
2. Fit param validators:
    These validate the fitted parameters after a fit is performed.  If any fail, a warning message is displayed in
    the log window of the dashboard to notify the user and the model's :code:`main_fit` fit parameter will be broadcast
    and persisted to the datasets. Fit param validators are defined by the
    :attr:`validators<scan_framework.models.scan_model.ScanModel.validators>` property of the
    :class:`ScanModel<scan_framework.models.scan_model.ScanModel>`.
3. Strong fit param validators:
    These also validate fitted parameters after a fit is performed.  If any strong validators fail, an error message is
    displayed in the log windows of the dashboard and the model's :code:`main_fit` fit parameter will **not** be
    broadcast and persisted to the datasets.  Strong fit param validators are defined by the
    :attr:`validators<scan_framework.models.scan_model.ScanModel.strong_validators>` property of the
    :class:`ScanModel<scan_framework.models.scan_model.ScanModel>`.

Pre-validators are useful as a pre-check on the measured values of the scan.  This allows a scan to only perform a fit
when, for example, the measured values are within some correct range or have some correct features.  Fit param
validators and strong fit param validators are useful to ensure that the fitted parameters are not outside some range of
acceptable values.  Used in combination, fit validations can be quite robust in avoiding the use of incorrect
values for experimental parameters due to fits that simply didn't converge to the correct value or were attempted
on data that was inadequate to fit.  Fit validations are not guaranteed to catch all cases of incorrect fits, however.

See the :ref:`Model Validators<model-validators>` section for details about each type of validation and how to define
validators.

Custom handling of fits
-----------------------
The framework calls the :meth:`after_fit()<scan_framework.scans.scan.Scan.after_fit>` method of the scan class after
any fit is performed.  Implementing the optional callback :meth:`after_fit()<scan_framework.scans.scan.Scan.after_fit>` in
a scan experiment then allows custom handling of the fitted parameters.  The fit object
:class:`Fit<scan_framework.analysis.curvefits.Fit>` can be accessed in this callback using :code:`model.fit` where
:code:`model` is the model argument passed to :meth:`after_fit()<scan_framework.scans.scan.Scan.after_fit>`.

The arguments passed to :meth:`after_fit()<scan_framework.scans.scan.Scan.after_fit>`
are
    1. The name of the fit.  This name is set by the :code:`fit` argument of :meth:`register_model()<scan_framework.scans.scan.Scan.register_model>`.
    2. If the fit is considered valid by the fit validations (see below for info on fit validations).
    3. If the main fit param was saved.
    4. The instance of the model that was registered to perform the fit.

See :meth:`after_fit()<scan_framework.scans.scan.Scan.after_fit>` for a full description this callback and its
arguments.

For example:

.. code-block:: python

    def after_fit(self, fit_name, valid, saved, model):
        # if the fit passed validations and was saved (i.e. the user selected 'Fit and Save' in the GUI)
        if valid and saved:
            # update the frequency of the RF synthesizer to the new value that was found by the scan
            freq = model.fit.x0
            self.dds_rf.set(freq)

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

