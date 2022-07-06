.. _callbacks:

Callbacks
==================================================================
Callbacks methods are optional methods that can be implemented within a scan.  These methods are then called by the
scan framework at certain points within the life cycle of a scan which allows you to execute code at predefined stages
of the scan.

User Callbacks
--------------------
User callbacks can be implemented in any scan that you write.  The most commonly used callbacks are
:meth:`prepare_scan() <artiq_scan_framework.scans.scan.Scan.prepare_scan>`,
:meth:`initialize_devices() <artiq_scan_framework.scans.scan.Scan.initialize_devices>`,
:meth:`set_scan_point() <artiq_scan_framework.scans.scan.Scan.set_scan_point>`,
and :meth:`cleanup() <artiq_scan_framework.scans.scan.Scan.cleanup>`.  These callbacks should allow you to accomplish what
what is needed the majority of the time.  Additional callbacks are available for more advanced usage.  Below is
a list of all available callbacks listed in order of execution.

Notes:
    - Names below wrapped in [] are in fact iterface methods, and not strictly callbacks.  They are included here to show the
      complete order of execution of both interface methods and callback methods.  See :doc:`/scans/methods` for
      additional information on interface methods.
    - Callbacks indicated as "Runs On: portable" run on the core device
      unless :attr:`run_on_core <artiq_scan_framework.scans.scan.Scan.run_on_core>`
      is set to :code:`False`, or :meth:`_run_scan_host <artiq_scan_framework.scans.scan.Scan._run_scan_host>`
      is called manually.


**In order of execution, all callbacks available to a scan are:**

=================================================================================== ======================  ===============  ==============      ===========================
| Callback                                                                          | Has Default           | Runs  On       | Scan Stage        | Runs When
                                                                                    | Behavior?                                                  | Scan is Resumed?
=================================================================================== ======================  ===============  ==============      ===========================
:meth:`[create_logger] <artiq_scan_framework.scans.scan.Scan.create_logger>`              yes                     host             __init__            no
:meth:`[build] <artiq_scan_framework.scans.scan.Scan.build>`                              yes                     host             __init__            no
:meth:`[get_scan_points] <artiq_scan_framework.scans.scan.Scan.get_scan_points>`          sometimes               host             initialization      no
:meth:`[get_warmup_points] <artiq_scan_framework.scans.scan.Scan.get_warmup_points>`      yes                     host             initialization      no
:meth:`[report] <artiq_scan_framework.scans.scan.Scan.report>`                            yes                     host             initialization      yes
:meth:`prepare_scan <artiq_scan_framework.scans.scan.Scan.prepare_scan>`                  no                      host             initialization      yes
:meth:`lab_prepare_scan <artiq_scan_framework.scans.scan.Scan.lab_prepare_scan>`          no                      host             initialization      yes
:meth:`before_scan <artiq_scan_framework.scans.scan.Scan.before_scan>`                    no                      host             initialization      yes
:meth:`lab_before_scan_core <artiq_scan_framework.scans.scan.Scan.lab_before_scan_core>`  no                      core device      scan loop           yes
:meth:`initialize_devices <artiq_scan_framework.scans.scan.Scan.initialize_devices>`      no                      portable         scan loop           yes
:meth:`before_pass <artiq_scan_framework.scans.scan.Scan.before_pass>`                    no                      portable         scan loop           no
:meth:`[warmup] <artiq_scan_framework.scans.scan.Scan.warmup>`                            yes                     portable         scan loop           yes
:meth:`offset_point <artiq_scan_framework.scans.scan.Scan.offset_point>`                  no                      portable         scan loop           yes
:meth:`set_scan_point <artiq_scan_framework.scans.scan.Scan.set_scan_point>`              no                      portable         scan loop           yes
:meth:`before_measure <artiq_scan_framework.scans.scan.Scan.before_measure>`              no                      portable         scan loop           yes
:meth:`lab_before_measure <artiq_scan_framework.scans.scan.Scan.lab_before_measure>`      no                      portable         scan loop           yes
:meth:`[measure] <artiq_scan_framework.scans.scan.Scan.measure>`                          no                      portable         scan loop           yes
:meth:`after_measure <artiq_scan_framework.scans.scan.Scan.after_measure>`                no                      portable         scan loop           yes
:meth:`lab_after_measure <artiq_scan_framework.scans.scan.Scan.lab_after_measure>`        no                      portable         scan loop           yes
:meth:`[mutate_datasets] <artiq_scan_framework.scans.scan.Scan.mutate_datasets>`          yes                     host             scan loop           yes
:meth:`before_calculate <artiq_scan_framework.scans.scan.Scan.before_calculate>`          no                      host (via RPC)   scan loop           yes
:meth:`after_scan_point <artiq_scan_framework.scans.scan.Scan.after_scan_point>`          no                      portable         scan loop           yes
:meth:`[_set_counts] <artiq_scan_framework.scans.scan.Scan._set_counts>`                  yes                     host (via RPC)   scan loop           yes
:meth:`cleanup <artiq_scan_framework.scans.scan.Scan.cleanup>`                            no                      portable         scan loop           yes
:meth:`after_scan_core <artiq_scan_framework.scans.scan.Scan.after_scan_core>`            no                      core device      scan loop           yes
:meth:`lab_after_scan_core <artiq_scan_framework.scans.scan.Scan.lab_after_scan_core>`    no                      core device      scan loop           yes
:meth:`after_scan <artiq_scan_framework.scans.scan.Scan.after_scan>`                      no                      host             analysis            yes
:meth:`[_analyze] <artiq_scan_framework.scans.scan.Scan._analyze>`                        yes                     host             analysis            yes
:meth:`before_analyze <artiq_scan_framework.scans.scan.Scan.before_analyze>`              no                      host             analysis            yes
:meth:`before_fit <artiq_scan_framework.scans.scan.Scan.before_fit>`                      no                      host             analysis            yes
:meth:`after_fit <artiq_scan_framework.scans.scan.Scan.after_fit>`                        no                      host             analysis            yes
:meth:`report_fit <artiq_scan_framework.scans.scan.Scan.report_fit>`                      yes                     host             analysis            yes
:meth:`lab_after_scan <artiq_scan_framework.scans.scan.Scan.lab_after_scan>`              no                      host             analysis            yes
=================================================================================== ======================  ===============  ==============      ===========================


Extension Callbacks
-------------------------
Extension callbacks are implemented by scan extension class of the scan framework and should not be implmented
in user scan classes.

=================================================================================== ======================  ===============  ==============      ===========================
| Callback                                                                          | Has Default           | Runs  On       | Scan Stage        | Runs When
                                                                                    | Behavior?                                                  | Scan is Resumed?
=================================================================================== ======================  ===============  ==============      ===========================
_add_processors                                                                     no                      host             initialization      no
_scan_arguments                                                                     no                      host             initialization      no
_map_arguments                                                                      no                      host             initialization      no
:meth:`_before_loop <artiq_scan_framework.scans.scan.Scan._before_loop>`                  no                      portable         scan loop           yes
_after_scan_point                                                                   no                      portable         scan loop           yes
_analyze_data                                                                       no                      portable         scan loop           yes
=================================================================================== ======================  ===============  ==============      ===========================