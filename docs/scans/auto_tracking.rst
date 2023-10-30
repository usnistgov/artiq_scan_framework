.. _auto_tracking:

Relative scan ranges and auto tracking
======================================

Relative scan ranges
--------------------
Often it is desirable to specify a range of scan points that is relative to some fixed offset.  For example,
scans of atomic resonances vs probe frequencies are often most useful when the probe frequency range is
specified as a range of frequencies relative to some fixed atomic frequency.  A scan range that is much smaller
than the fixed frequency can then easily be entered in the dashboard without having to keep track
of which digit in a large number corresponds to a certain scale (e.g. MHz or KHz portions of a GHz value).

This is easily accomplished by setting :code:`self._x_offset` in the scan class.

.. code-block:: python

    def build(self):
        ...

        # range of frequencies relative to 1.8121*GHz
        self.setattr_argument('frequencies', Scannable(
            default=RangeScan(
                start=-0.1*MHz,
                stop=0.1*MHz,
                npoints=50
            ), unit='MHz', scale=MHz))

    def prepare(self):
        # offset all scan points by this value
        self._x_offset = 1.8121*GHz

    def get_scan_points(self):
        return self.frequencies

In the above example, a narrow range of 200 kHz is being scanned about a center frequency of 1.8121 GHz.  This
narrow range is displayed in the GUI for editing and each realtive scan point value will have 1.81121 GHz added
to it automatically by the framework before the scan is executed.


Auto-tracking
-------------
When working with models, :code:`_x_offset` can be determined automatically by the framework from the last
fitted value for a scan.  This is useful because the center value of an absolute scan range may change
over time, such as in the case of atomic transition frequencies.  Using auto-tracking allows the scan to naturally
follow any drifts in the value being fit as it is periodically run.  To use auto-tracking in a scan, first create
a scan model that has the :attr:`main_fit <artiq_scan_framework.models.scan_model.ScanModel.main_fit>`
attribute defined.  Then register the scan model with the :code:`auto_track` attribute set.

.. code-block:: python

    def prepare(self):
        # Fetch the current dataset given by my_model.main_fit
        # and offset every scan point by this value.
        my_model = MyScanModel(self)
        self.register_model(my_model, auto_track='fit')

When :code:`auto_track='fit'` or :code:`auto_track'fitresults'` are set, the framework automatically offsets
the scan points by the main fit of the scan.  If :code:`auto_track='fit'` is set, the most recently fitted
value of :attr:`main_fit <artiq_scan_framework.models.scan_model.ScanModel.main fit>` is fetched from the datasets
(i.e. from a previous run of the scan) and used to offset the scan points, while setting :code:`auto_track='fitresults'`
causes the fitted value that was just found by the scan to be used (which has not yet been saved to the datasets).


.. note::
    Auto tracking can be disabled entirely in either a :code:`FreqScan` or a :code:`TimeFreqScan` by setting
    :code:`self.enable_auto_tracking = False` in the scan.


Setting :code:`auto_track='fitresults'` is useful in cases where a separate sub-scan is run in the
:code:`measure()` method of a top-level scan and the value returned by the :code:`measure()` method is a
parameter that is fit by the sub-scan.

As an example, and a more advanced usage of the scan framework:

.. code-block:: python

    from artiq_scan_framework.scans import *
    import experiments.scans.tickle_scan as scan
    from lib.models.rf_resonator_model import *
    from artiq_scan_framework.models import *


    class RFResonatorScan(Scan1D, EnvExperiment):
        """RF Resonator Scan

        Scans over RF synth frequencies to find the resonant frequency of the resonator
        between the RF synthesizer output and the ion trap RF electrodes.

        A separate tickle scan is performed at each scan point (RF synth frequency) to find the

        """
        # top-level scan is run on the host (sub-scan is run on the core device)
        run_on_core = False

        def build(self):
            super().build()

            # RF synthesizer device
            self.rf_synth = self.get_device('rf_synth')

            # tickle scan
            self.tickle_scan = scan.TickleScan(self,
               # don't save any fitted values since this is just a sub-scan
               fit_options='Fit',
               # auto-center each sub-scan about the fitted value from the previous scan point
               auto_track=True,
               # don't display fitted values in the log window of the dashboard
               enable_reporting=False)

            self.scan_arguments()

            # range of absolute RF synthesizer frequencies
            self.setattr_argument('rf_frequencies', Scannable(
                default=RangeScan(
                    start=63.72 * MHz,
                    stop=63.74 * MHz,
                    npoints=10
                ),
                unit='MHz',
                scale=1 * MHz,
                ndecimals=4
            ), group='Scan Range')

            # range of relative tickle frequencies
            self.setattr_argument('frequencies', Scannable(
                default=RangeScan(
                    start=-0.1 * MHz,
                    stop=0.1 * MHz,
                    npoints=30
                ),
                unit='MHz',
                scale=1 * MHz,
                ndecimals=4
            ), group='Scan Range')

            # used internally for auto-tracking
            self.tracking_seeded = False

        def prepare(self):
            # set the relative scan points of the sub-scan
            self.tickle_scan.frequencies = self.frequencies
            self.tickle_scan.prepare()

            # register the top-level scan model
            self.model = RfResonatorScanModel(self)
            self.register_model(self.model, measurement=True, fit=True)

        # top-level scan points (RF synth frequencies)
        def get_scan_points(self):
            return self.rf_trap_frequencies

        def set_scan_point(self, i_point, point):
            # set the RF synth frequency
            self.core.break_realtime()
            self.rf_synth.set(point)

        def measure(self, rf_trap_frequency) -> TInt64:
            # find the secular frequency that results for the current RF frequency driving the resonator
            self.tickle_scan.run()

            # fit is not available in datasets since tickle fit's aren't being saved
            if self.tickle_scan.model.fit_valid:
                # start auto-tracking the last fitted tickle freq once we have a good fit
                self.tracking_seeded = True
                return self.tickle_scan.model.fit.frequency
            else:
                return 0

        def after_scan_point(self, i_point, point):
            if self.tracking_seeded:
                # center the next sub-scan about the fitted tickle freq for the
                # current scan point
                self.tickle_scan.auto_track = 'fitresults'

Each time the sub-scan is run within the top-level scan in the example above, its scan range will be automatically
centered around the value of the fitted tickle frequency from the previous scan point.  This allows the sub-scan
range to stay appropriately centered about the fitted value at each scan point, which changes with each scan
point.  This method avoids having to specify a very large scan range that spans all the relevant frequencies
of the sub-scan.


