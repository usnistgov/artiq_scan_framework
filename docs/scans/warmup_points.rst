Running warmup points
=========================

A set of warmup points can be run on the core device before a scan starts allowing equipment up to be brought up to
a desired operating temperature before it is used to perform measurements in the scan.

The default behavior of a scan is to execute the :meth:`measure(point) <scan_framework.scans.scan.Scan.measure>`
interface method :attr:`self.nwarmup_points <scan_framework.scans.scan.Scan.nwarmup_points>`
number of times for each registered measurement with the :code:`point` argument set to :code:`0.0`.

:code:`self.warming_up` is set to :code:`True` immediately before warmup points are execute and is set to :code:`False`
immediately after all warmup points have executed.  This allows determining when to run warmup points within the
measure method.

.. code-block:: python

    def measure(self, point):
        if self.warming_up:
            # ... execute commands for warming up devices
            # e.g. set dds frequency and turn on TTL
        else:
            # ... execute commands for the measurement

If the :meth:`warmup() <scan_framework.scans.scan.Scan.warmup>` interface method is implemented
:meth:`warmup(point) <scan_framework.scans.scan.Scan.warmup>` will be executed instead of
:meth:`measure(point) <scan_framework.scans.scan.Scan.measure>`.  This allows warmup and measurement commands
to be separated and also results in faster execution of the :code:`measure()` method since it does not need to check
:code:`self.warming_up` each time it is called during the execution of the scan.

.. code-block:: python

    def warmup(self, point):
        # ... execute commands for warming up devices
        # e.g. set dds frequency and turn on TTL

    def measure(self, point):
        # ... execute commands for the measurement


Additionally, if the :meth:`get_warmup_points() <scan_framework.scans.scan.Scan.get_warmup_points>` interface method
is implemented the returned set of points will be iterated over and the :code:`point` argument of either
:code:`measure(point)` or :code:`warmup(point)` will be set to the current warmup point.

