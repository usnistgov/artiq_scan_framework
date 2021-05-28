Creating Histograms
========================
There is a generic Histograms Model (:class:`HistModel <scan_framework.models.hist_model.HistModel>`) that can be used
for binning values, saving the histogram to a dataset, and viewing the data in an applet.

To use the model, first instantiate an instance, specify the bin boundaries, and initialize the datasets:

.. code-block:: python

    model = HistModel(self, namespace='my_histogram')
    model.init_bins(bin_start=0,
                    bin_end=50,
                    nbins=51)
    model.initialize_datasets()

## Binning single values ##
To bin a single value use the :code:`bin_value()` method:

.. code-block:: python

    model.bin_value(9)

After you are done binning, call the `set_bins()` method to write the histogram to it's dataset which will be named
:code:`bins` under the model namespace:

.. code-block:: python

    model.set_bins() # write data to 'my_histogram.bins'

To clear out the histogram and start binning new values, e.g. for a new measurement or datapoint, call the
:code:`reset_bins()` method

.. code-block:: python

    model.reset_bins()

Binning multiple values at once
-------------------------------

To bin multiple values and set the :code:`bins` dataset all in one go, use the :code:`mutate()` method.

.. code-block:: python

    model.mutate([42, 42, 42, 42, 42, 41, 43], broadcast=True, persist=False, archive=False)

Binning Continuous Values
-------------------------
By default, the :class:`HistModel <scan_framework.models.hist_model.HistModel>` class assumes the data being binned is
discretely valued such as from PMT counts.  Non-discrete values can also be binned by setting the model's :code:`discrete`
attribute to False.

Plots
-------------------------------
In addition to the binned data, :code:`initialize_datasets()` sets datasets that can be used in plots: :code:`x_units`,
:code:`x_label`, :code:`y_label`, and :code:`plot_title`.  Values are defined through model attributes:

.. code-block:: python

    model = HistModel(self,
        namespace="my_histogram",
        x_label="PMT Counts",
        plot_title="My Plot",
    )
    model.init_bins(bin_start=0,
                    bin_end=50,
                    nbins=51)
    model.initialize_datasets()  # set's `my_histogram.x_label` to "PMT Counts" & `my_histogram.plot_title` to "My Plot"

