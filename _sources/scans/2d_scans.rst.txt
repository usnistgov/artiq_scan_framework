2D Scans
========================

2D scans can be created by inheriting from the :code:`Scan2D` class.  2D scans are similar to 1D scans with the following
changes:

    1. Two scan models are registered
    2. Two sets of scan points are defined and returned by :code:`get_scan_points()` (one for each dimension).
    3. The :code:`calculate_dim0(self, dim1_model)` callback must be implemented in the scan.
    4. The :code:`point` and :code:`i_point` parameters passed to callback methods will be lists with two entries containing the point and point index of each dimension.

To create a 2D scan, inherit from the :code:`Scan2D` class, register two models, and return a list from
:meth:`get_scan_points()<scan_framework.scans.scan.Scan.get_scan_points>`  with two entries containing the scan points for both dimensions.  The :code:`dimension` argument
passed to :code:`register_model()` specifies the dimension of the model.  Dimension 1 is the sub-scan, and dimension 0
is the top level scan.

The :code:`calculate_dim0` Callback
--------------------------------------
The :code:`calculate_dim0(self, dim1_model)` callback returns a fitted parameter or a calculated value along with the error
in that value after a sub-scan completes.  After a sub-scan completes and a fit has been performed on that sub-scan ,
:code:`calculate_dim0()` will be called and passed the dimension 1 model.  The dimension 1 model can then be used in
:code:`calculate_dim0()` to fetch the fitted parameters or other data needed to calculate the value and error to
return.  The value returned will be plotted as the y-value in the dimension 0 plot.  The error returned will weight that
value when the final fit is performed along dimension 0 using the y-values and errors returned by :code:`calculate_dim0()`.
The corresponding x-values used by the dimension 0 fit are the scan points of the top level (dimension 0) scan.


Example 2D Scan
---------------------------------
An example of a 2D scan that scans over the RF trap frequency and performs a sub-scan over tickle frequencies might look
like:

.. code-block:: python

    from scan_framework.scans import *
    from scan_framework.models import *
    from lib.cooling import *
    from lib.detection import *

    class RfResonatorScan(Scan2D, EnvExperiment):

        def build(self):
            super().build()

            # devices
            self.setattr_device('ttl_tickle')
            self.setattr_device('dds_tickle')

            # libs
            self.cooling = Cooling(self)
            self.detection = Detection(self)

            # arguments
            self.setattr_argument('rf_frequencies', Scannable(
                default=RangeScan(
                    start=64.44 * MHz,
                    stop=64.48 * MHz,
                    npoints=20
                ),
                unit='MHz',
                scale=1 * MHz,
                ndecimals=4
            ), group='Scan Range')
            self.setattr_argument('tickle_frequencies', Scannable(
                default=RangeScan(
                    start=4.6 * MHz,
                    stop=4.8 * MHz,
                    npoints=50
                ),
                unit='MHz',
                scale=1 * MHz,
                ndecimals=4
            ), group='Scan Range')

            # scan arguments
            self.scan_arguments()

        def prepare(self):
            # Dimension 0 model (top level, RF trap frequencies)
            self.rf_model = ScanModel(self,
                                      namespace="rf_resonator",
                                      fit_function = fitting.Lor,
                                      main_fit = 'x0')
            self.register_model(self.rf_model,
                                dimension=0,
                                # Peform a final fit on the fitted parameters from each sub-scan
                                fit=True,
                                set=True)

            # Dimension 1 model (sub-scan level, tickle frequencies)
            self.tickle_model = ScanModel(self,
                                          fit_function = fit_functions.SincInv
                                          main_fit = 'frequency')
            self.register_model(self.tickle_model,
                                dimension=1,
                                # Data is collected by the dimension 1 model only
                                measurement=True,
                                # Do save the fitted param values to the current_scan namespace
                                set=True,
                                # Don't save the fitted frequency as the current tickle freq
                                save=False)

        def get_scan_points(self):
            # assign the trap frequencies and tickle frequencies as the scan points
            return [
                self.rf_frequencies,  # dimension 0 (trap freqs)
                self.tickle_frequencies,  # dimension 1 (tickle freqs)
            ]

        @kernel
        def set_scan_point(self, i_point, point):
            trap_freq = point[0]
            tickle_freq = point[1]

            # set the trap frequency at the start of the tickle sub-scan
            self.core.break_realtime()
            if i_point[1] == 0:
                self.dds_rf.set(trap_freq)
                delay(3*us)

            # set the tickle frequency
            self.dds_tickle.set(tickle_freq)
            delay(3*us)

        @kernel
        def measure(self, point):
            # cool
            self.cooling.doppler()

            # pulse the tickle TTL
            self.ttl_tickle.pulse(100*us)

            # detect
            counts = self.detection.detect()
            return counts

        def calculate_dim0(self, dim1_model):
            # plot this dimension 1 fitted value in the dimension 0 plot
            param = dim1_model.fit.params.frequency
            # weight final fit by error in this dimension 1 fit param
            error = dim1_model.fit.errs.frequency_err
            return param, error
