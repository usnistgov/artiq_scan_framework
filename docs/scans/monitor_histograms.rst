Monitor histograms
============================

All model's automatically generate a histogram for a datapoint each time the model datasets are mutated and save the
histogram to the :code:`current_hist` namespace.  This allows you to view a measurement's distribution at each scan point
in a scan as it runs.  To view these histograms, create an applet for viewing the histogram with the following command

.. code-block:: console

    $python -m scan_framework.applets.plot_hist current_hist.bins --x current_hist.bin_boundaries
    --x_units current_hist.x_units --x_label current_hist.x_label --plot_title current_hist.plot_title


It's contents will automatically be updated by a scan.  For example, in a microwave frequency scan, the
:code:`current_hist.bins` dataset will contain the distribution of the current scan point after all repetitions of the
measurement at that point are compete.  To turn off monitor histograms, set :code:`self.enable_histograms = False` in
your model.