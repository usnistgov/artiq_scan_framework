Configurations reference
========================
A number of configuration options are available as attributes of a scan model.  These attributes are used to
configure the data that is generated by the model.  Configurations are available to set when and how datasets are created,
configure all aspects of the fit performed by the model including validations of the fitted parameters, and to control
the formatting of plots.  All of the available attributes that can be used for configuration are listed below.

Additionally, certain features can be disabled/enabled entirely.  All available attributes for disabling/enabling
features are also listed below.

.. note::
    All attributes listed below can be set dynamically inside a scan experiment on an instance of a :code:`ScanModel`.
    This can be useful when use of static attributes or defining attributes as a property via :code:`@property`
    do not provide enough flexibility for a particular scan.

Datset configurations
---------------------
.. autoattribute:: scan_framework.models.scan_model.ScanModel.namespace
.. autoattribute:: scan_framework.models.scan_model.ScanModel.mirror_namespace
.. autoattribute:: scan_framework.models.scan_model.ScanModel.broadcast
.. autoattribute:: scan_framework.models.scan_model.ScanModel.persist
.. autoattribute:: scan_framework.models.scan_model.ScanModel.save
.. autoattribute:: scan_framework.models.scan_model.ScanModel.mirror

Fitting configurations
----------------------
.. autoattribute:: scan_framework.models.scan_model.ScanModel.fit_map
.. autoattribute:: scan_framework.models.scan_model.ScanModel.fit_function
.. autoattribute:: scan_framework.models.scan_model.ScanModel.fit_use_yerr
.. autoattribute:: scan_framework.models.scan_model.ScanModel.guess
.. autoattribute:: scan_framework.models.scan_model.ScanModel.man_bounds
.. autoattribute:: scan_framework.models.scan_model.ScanModel.man_scale
.. autoattribute:: scan_framework.models.scan_model.ScanModel.hold
.. autoattribute:: scan_framework.models.scan_model.ScanModel.main_fit
.. autoattribute:: scan_framework.models.scan_model.ScanModel.fits_to_save

Fit validation configurations
-----------------------------
.. autoattribute:: scan_framework.models.scan_model.ScanModel.validators
.. autoattribute:: scan_framework.models.scan_model.ScanModel.strong_validators
.. autoattribute:: scan_framework.models.scan_model.ScanModel.pre_validators

Plotting configurations
-----------------------
.. autoattribute:: scan_framework.models.scan_model.ScanModel.x_label
.. autoattribute:: scan_framework.models.scan_model.ScanModel.y_label
.. autoattribute:: scan_framework.models.scan_model.ScanModel.x_scale
.. autoattribute:: scan_framework.models.scan_model.ScanModel.y_scale
.. autoattribute:: scan_framework.models.scan_model.ScanModel.x_units
.. autoattribute:: scan_framework.models.scan_model.ScanModel.y_units
.. autoattribute:: scan_framework.models.scan_model.ScanModel.plot_title

Enabling/disabling features
---------------------------
.. autoattribute:: scan_framework.models.scan_model.ScanModel.enable_histograms
.. autoattribute:: scan_framework.models.scan_model.ScanModel.aggregate_histogram
.. autoattribute:: scan_framework.models.scan_model.ScanModel.disable_validations
