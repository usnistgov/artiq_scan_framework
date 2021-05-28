Examples for the scan framework
===============================
Various examples showing how to use the scan framework. 

## `models` Folder
 Contains various, real-world examples of implementing a `ScanModel` class.  Models in 
 this directory are used by the real-world examples in `examples/scans/heating_rate_scan.py`,
 `examples/scans/secular_freq_calib_scan.py`, `examples/scans/shim_scan.py`, and
 `examples/scans/tickle_scan.py`
 
## `scans` Folder
Contains various examples of implementing a scan using the scan framework.  File names
beginning with exNN_ denote tutorials that are useful for beginning users of the 
scan framework.  These tutorials are meant to be followed in numerical order and introduce
concepts in the scan framework from basic to more advanced. 

## `loading.py` File
The `loading.py` file contains an example ARTIQ sub-component, which implements the 
loading interface required by `ReloadingScan`.  Scans such as `examples/scans/heating_rate_scan.py`
and `examples/scans/shim_scan.py` allow for lost ion detection and ion reloading.  These
scans set an attribute name `loading` to an instance of the loading interface in `examples/loading.py`.

    self.loading = Loading(self, ...)

The scan framework will use `self.loading` to both check for the presence of an ion and 
to load an ion.  This allows each lab to define their own routines for lost ion detection
and ion reloading./