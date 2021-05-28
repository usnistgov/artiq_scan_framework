Auto tracking & centering scan ranges
========================================
register model  with auto_track='fit' or  auto_track='fitresults' to center scan around the main
fit of the scan.  auto_track='fit' uses the last fitted value of the main fit while
auto_track='fitresults' uses the fitted value that was just found by the scan.  The latter case can
be useful in some situations, but auto_track='fit' is the most common use case.

.. code-block:: python

    self.register_model(MyScanModel(self), auto_track='fit')
