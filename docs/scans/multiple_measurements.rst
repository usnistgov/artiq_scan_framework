
Performing multiple measurements
=================================
Sometimes it may be desired to perform multiple measurements at each scan point and to save the collected data and
calculated mean values of each measurement to separate datasets .  To perform multiple measurements set the
:code:`measurements` attribute of the scan to a list that contains the name of each measurement.  The data of each
measurement is then saved separately by registering a model for each measurement.

.. code-block:: python

    def build(self, **kwargs):
        # define two separate measurements
        self.measurements = ['rsb', 'bsb']

    def register_models(self):
        # create models to store data for each measurement
        self.bsb_model = BsbModel(self)
        self.rsb_model = RsbModel(self)

        # register each model with it's associated measurement
        self.register_model(self.bsb_model, measurement='bsb')
        self.register_model(self.rsb_model, measurement='rsb')

The scan's :code:`measure()` method will be called multiple times at each scan point repetition, once for every
measurement specified in :code:`self.measurements`.  The scan's :code:`self.measurement` attribute will be set to the
name of the current measurement before :code:`measure()` is called.  This allows the current measurement to be
determined in the :code:`measure()` method.
As an example, in a heating rate scan your :code:`measure()` method may look like this:

.. code-block:: python

    @kernel
    def measure(self, time):
        self.cooling.doppler()

        # perform a blue side-band measurement
        if self.measurement == 'bsb':
            self.raman.set_frequency(self.raman.m1_bsb_frequency)
            self.raman.pulse(self.raman_readout_time)

        # perform a red side-band measurement
        if self.measurement == 'rsb':
            self.raman.set_frequency(self.raman.m1_rsb_frequency)
            self.raman.pulse(self.raman_readout_time)

        # rsb or bsb counts
        # each will be stored to their respective datasets after the scan point completes.
        counts = self.detection.detect()
        return counts
