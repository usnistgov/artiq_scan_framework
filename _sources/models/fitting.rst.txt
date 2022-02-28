Configuring fits
----------------

Fits are performed automatically by the scan framework when a scan model is registered with :code:`fit=True`.
The framework will then use attributes of the scan model to determine how to perform the fit, including what
fit function to use, what initial guesses to use for the fit parameters, if any bounds should be set on the
fitted paramters, etc.