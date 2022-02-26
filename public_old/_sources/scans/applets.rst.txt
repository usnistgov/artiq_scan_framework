.. _applets:

Applets
=====================

There are a few applets that need to be created so that scan data may be plotted.  Each applet uses one of the
applet classes defined in the scan_framework/applets folder.  See the applets documentation for more information about
these applet classes.

.. _current-scan-applet:

Current scan applet
----------------------------------------------
The current scan applet plots the mean values calculated as the scan runs.  Mean values will
be added as data points to the plot after each scan point.  The line of best fit is also
plotted in this applet when fit's are performed at the end of a scan.

Add the following command to the applets panel in the dashboard to create the current scan applet:

.. code-block:: console

    $python -m scan_framework.applets.plot_xy current_scan.plots.y
        --x current_scan.plots.x
        --fit current_scan.plots.fitline
        --title current_scan.plots.plot_title
        --x_scale current_scan.plots.x_scale
        --x_units current_scan.plots.x_units
        --y_scale current_scan.plots.y_scale
        --x_label current_scan.plots.x_label
        --y_units current_scan.plots.y_units
        --y_label current_scan.plots.y_label
        --rid current_scan.rid
        --error current_scan.plots.error

See the :ref:`Current Scan Datasets<current-scan-datasets>` section for details about each argument/dataset.

.. note::
    The :code:`--rid` argument is optional.  If it is set, the RID of the current scan as prepended to the plot title.

.. note::
    The current scan applet is used for both 1D and 2D scans

.. _count-monitor-applet:

Count monitor applet
----------------------------------------------
The count monitor applet displays the mean of all values returned by the :code:`measure()` method during
a single  scan point

Add the following command to the applets panel in the dashboard to create the count monitor applet:

.. code-block:: console

   ${artiq_applet}big_number counts

.. _current-hist-applet:

Current histogram applet
----------------------------------------------
The current histogram applet displays a histogram of counts at each scan point as the scan runs.  The histogram will
be updated when a scan point completes.  This is used for realtime monitoring of distributions as the scan runs.

Add the following command to the applets panel in the dashboard to create the current histogram applet:

.. code-block:: console

    $python -m scan_framework.applets.plot_hist current_hist.bins
        --x current_hist.bin_boundaries
        --x_units current_hist.x_units
        --x_label current_hist.x_label
        --plot_title current_hist.plot_title

All datasets needed to plot histograms are automatically created and updated by the scan model.

.. _current-aggregate-hist-applet:

Current aggregate histogram applet
----------------------------------------------
The current aggregate histogram applet displays a histogram of counts over all scan points of a scan.
The histogram will be updated when a scan point completes.

Add the following command to the applets panel in the dashboard to create the current aggregate histogram applet:

.. code-block:: console

    $python -m scan_framework.applets.plot_hist current_hist.aggregate_bins
        --x current_hist.bin_boundaries
        --x_units current_hist.x_units
        --x_label current_hist.x_label
        --plot_title current_hist.plot_title

All datasets needed to plot aggregate histograms are automatically created and updated by the scan model.


.. _current-scan-browser-applet:

Current scan applet for the ARTIQ browser
----------------------------------------------
A separate current scan applet is necessary when browsing experiment runs in the ARTIQ browser.
It is identical to the current scan applet above with the :code:`--trigger` argument set to 1.
This allow the plot to be redrawn when browsing through different experiment runs.

Add the following command to the applets panel in the browser to create the browser current scan applet:

.. code-block:: console

    $python -m scan_framework.applets.plot_xy current_scan.plots.y
    --x current_scan.plots.x
    --fit current_scan.plots.fitline
    --title current_scan.plots.plot_title
    --x_scale current_scan.plots.x_scale
    --x_units current_scan.plots.x_units
    --x_label current_scan.plots.x_label
    --y_units current_scan.plots.y_units
    --y_label current_scan.plots.y_label
    --trigger 1

.. _current-sub-scan-applet:

Current sub-scan applet (for 2D scans)
----------------------------------------------
As a two dimensional scans runs, a fit is performed on each sub-scan when it completes.  Fitted parameter values from
each of these sub-fits are then plotted in the current scan applet.  The current sub-scan applet plot's the mean values
and fitlines of each sub-scan so the results can be viewed as the scan runs.

Add the following command to the applets panel in the dashboard to create the current sub-scan applet:

.. code-block:: console

    $python -m scan_framework.applets.plot_xy current_scan.plots.dim1.y
        --x current_scan.plots.dim1.x
        --fit current_scan.plots.dim1.fitline
        --title current_scan.plots.dim1.plot_title
        --x_scale current_scan.plots.dim1.x_scale
        --x_units current_scan.plots.dim1.x_units
        --x_label current_scan.plots.dim1.x_label
        --y_units current_scan.plots.dim1.y_units
        --y_label current_scan.plots.dim1.y_label
        --trigger current_scan.plots.trigger
        --rid current_scan.rid
        --i_plot current_scan.plots.subplot.i_plot

Current sub-scan applet (For 2D scans, no fits)
-----------------------------------------------
If rendering of the current sub-scan applet is slow, a sub-scan plot with no fits can help speed things up:

.. code-block:: console

    $python -m scan_framework.applets.plot_xy current_scan.plots.dim1.y
        --x current_scan.plots.dim1.x
        --title current_scan.plots.dim1.plot_title
        --x_scale current_scan.plots.dim1.x_scale
        --x_units current_scan.plots.dim1.x_units
        --x_label current_scan.plots.dim1.x_label
        --y_units current_scan.plots.dim1.y_units
        --y_label current_scan.plots.dim1.y_label
        --trigger current_scan.plots.trigger
        --rid current_scan.rid
        --i_plot current_scan.plots.subplot.i_plot

