Lost ion detection and reloading
==================================

If the ion is lost during a scan, the last two data points collected are thrown out, the scan is paused, and the
:code:`load_ion` experiment is scheduled.  After the :code:`load_ion` experiment completes, the scan is resumed two scan points
before the point at which it failed.  This feature must be selectively enabled in the scan by setting

.. code-block:: python

    self.enable_reloading = True


in the scan.


Lost Ion Re-Loading
---------------------------------
Ion's can be automatically loaded by creating a sub-component similar to the loading sub-component in
:code:`examples/loading.py` In that sub-component, presence of an ion is determined by thresholding PMT
counts and loading will stop after a given number of seconds if an ion could not be loaded.

.. note::
    To use lost ion detection and automatic reloading, inherit from the :class:`~artiq_scan_framework.scans.extensions.ReloadingScan`
    class, create a loading library that implements the :class:`~artiq_scan_framework.lib.loading_interface.LoadingInterface`
    interface, and set :code:`self.loading` to an instance of the loading library in the scan:

.. code-block:: python

        self.loading = Loading(self)

During a scan, the data collected for each scan point is analyzed by functions provided by the :code:`ReloadingScan` class
to determine if an ion is still present in the trap.  This preliminary analysis state looks for the presence or absence
of an ion by thresholding PMT counts returned by the scan's :code:`measure()` method.  If more than two successive scan
points fail this analysis stage, a separate measurement is performed by the :code:`ion_present()` method of the loading
sub-component to determine if the ion is present (typically by also thresholding PMT counts).  The ion is considered to
be lost if this final stage fails (:code:`ion_present()` returns :code:`False`).  When the ion is considered lost, the
scan will be paused, and a new ion will be loaded by calling the :code:`schedule_load_ion()` method of the loading
sub-component.  If loading succeeds, the scan will resume at two scan points prior to the point that
originally failed ion detection.

