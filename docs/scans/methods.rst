Methods Available to a Scan
===========================

User Interface Methods
----------------------
The following interface methods may be implemented by a scan class to control the execution of a scan.

Listed in order of execution

=============================================================================== ======================  ==============  ===============  =========== ===========================
| Method                                                                        | Has Default           | Runs On       | Scan Stage     | Required? | Runs When
                                                                                | Behavior?                                                          | Scan is Resumed?
=============================================================================== ======================  ==============  ===============  =========== ===========================
:meth:`create_logger <artiq_scan_framework.scans.scan.Scan.create_logger>`            yes                     host            initialization   no          no
:meth:`build <artiq_scan_framework.scans.scan.Scan.build>`                            yes                     host            initialization   no          no
:meth:`run <artiq_scan_framework.scans.scan.Scan.run>`                                yes                     host            initialization   no          yes
:meth:`get_scan_points <artiq_scan_framework.scans.scan.Scan.get_scan_points>`        sometimes               host            initialization   yes         no
:meth:`get_warmup_points <artiq_scan_framework.scans.scan.Scan.get_warmup_points>`    yes                     host            initialization   no          no
:meth:`report <artiq_scan_framework.scans.scan.Scan.report>`                          yes                     host            initialization   no          no
:meth:`_yield <artiq_scan_framework.scans.scan.Scan._yield>`                          yes                     host            scan loop        no          yes
:meth:`warmup <artiq_scan_framework.scans.scan.Scan.warmup>`                          yes                     portable        scan loop        no          yes
:meth:`measure <artiq_scan_framework.scans.scan.measure>`                             no                      portable        scan loop        yes         yes
:meth:`mutate_datasets <artiq_scan_framework.scans.scan.mutate_datasets>`             yes                     host            scan loop        no          yes
:meth:`_calculate_all <artiq_scan_framework.scans.scan._calculate_all>`               yes                     host            scan loop        no          yes
:meth:`_calculate_all <artiq_scan_framework.scans.scan._set_counts>`                  yes                     host            scan loop        no          yes
:meth:`analyze <artiq_scan_framework.scans.scan.analyze>`                             yes                     host            analysis         no          yes
:meth:`_analyze <artiq_scan_framework.scans.scan._analyze>`                           yes                     host            analysis         no          yes
=============================================================================== ======================  ==============  ===============  =========== ===========================

User Helper Methods
-------------------

=============================================================================== ======================  ==============  ==============  =========== ===========================
| Method                                                                        | Has Default           | Runs On       | Scan Stage    | Required? | Runs When
                                                                                | Behavior?                                                         | Scan is Resumed?
=============================================================================== ======================  ==============  ==============  =========== ===========================
:meth:`register_model <scan_framework.scans.scan.Scan.register_model>`
:meth:`setattr_argument <scan_framework.scans.scan.Scan.setattr_argument>`
:meth:`scan_arguments <scan_framework.scans.scan.Scan.scan_arguments>`
:meth:`register_model <scan_framework.scans.scan.Scan.register_model>`
:meth:`_run_scan_host <scan_framework.scans.scan.Scan._run_scan_host>`
:meth:`_run_scan_core <scan_framework.scans.scan.Scan._run_scan_core>`
:meth:`simulate_measure <scan_framework.scans.scan.Scan.simulate_measure>`
=============================================================================== ======================  ==============  ==============  =========== ===========================

Extension Interface Methods
---------------------------
The following interface methods may be implemented by a scan framework extension classes to control the
execution of a scan.  These methods should not be implemented by user scan classes and are listed here for
reference.

=============================================================================== ======================  ==============  ==============  =========== ===========================
| Method                                                                        | Has Default           | Runs On       | Scan Stage    | Required? | Runs When
                                                                                | Behavior?                                                         | Scan is Resumed?
=============================================================================== ======================  ==============  ==============  =========== ===========================
_offset_points                                                                  no                      host            initialization  yes         no
_load_points                                                                    no                      host            initialization  yes         no
_write_datasets                                                                 no                      host            initialization  yes         yes
_report                                                                         no                      host            initialization  no          no
do_measure                                                                      yes                     portable        scan loop       no          yes
calculate_dim0                                                                  no                      host            scan loop       yes         yes
_mutate_plot                                                                    no                      host            scan loop       yes         yes
=============================================================================== ======================  ==============  ==============  =========== ===========================