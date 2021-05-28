Pausing, resuming, & early termination
======================================
By default, a scan will always yield to a higher priority experiment that has been submitted to the ARTIQ master.
Scans always complete the current scan point before checking with the scheduler if they need to pause via
:code:`self.scheduler.check_pause()`.  If :code:`self.scheduler.check_pause()` indicates that the scan needs to
yield to another experiment, the scan state is saved and the scan yields to the higher priority experiment.
After the higher priority experiment experiment completes, the scan will automatically resume at the scan point
following the scan point that was completed before yielding.

To disable pausing, resuming, and early termination and not incure the performance hit of
:code:`self.scheduler.check_pause()` set the :code:`enable_pausing` attribute of the scan to :code:`False`

.. code-block:: python

    class MyScan(Scan1D, EnvExperiment):
        enable_pausing = False
        ...

.. note::
    Not all callbacks are executed when a scan resumes after yielding.  See the :ref:`Callbacks<callbacks>`
    section for which callbacks will execute when the scan resumes.

.. note::
    Models should only be registered in either the :code:`build()` or :code:`prepare()` methods since these methods
    will not be executed when the scan resumes.  If a model is registered in another method, such as the
    :code:`prepare_scan()` method, it will be re-registered when the scan resumes causing it to be registered twice.

