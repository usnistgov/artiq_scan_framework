# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0]

### Support for ARTIQ version 6.0

- Added support for ARTIQ version 6.0.  All users need to upgrade their ARTIQ installation to version 6.0.
- Added a new 'archive' attribute to all models to conform with ARTIQ version 6 which deprecated the 'save' argument in set_dataset() in favor of a renamed argument named 'archive'.
- The 'save' argument of all dataset setting methods in a model has been replaced by an argument named 'archive' to conform with ARTIQ version 6.  
- The 'save' attribute of all model classes and the 'save' argument of dataset setting methods in models may still be used, but a warning message will be printed in the log window of the dashboard indicating that the 'save' argument/attribute has been deprecated.  

## [2.1.0] - 2022-02-27

### New features added
- New continous scan feature added: scans can be run continuously and only stop when a user terminates the scan. 
- New infinite logging for continous scans feature added: all data collected during continuous scan can be logged to an hdf5 file.

## [2.0.2] - 2022-02-09

### Bug fixes
- Fixed bug causing scans with npasses > 1 to disregard measurements from previous passes.

## [2.0.1] - 2021-07-27

- Fixed outdated unittests to work in ARTIQ version 3
- The mutate_datasets(), _set_counts(), & _calculate_all() scan callbacks are now asynchronouse (fire and forget) remote procedure calls.
- Added ability to plot a fitline in the histogram plotting applet


## [2.0.0] - 2021-07-13

### Added

- All existing files for the scan framework currently used at NIST.

### Changes from previous in-house version of the artiq\_ions scan class:
- The previous alias of "fitting" for analysis.curvefits has been renamed to "curvefits".  Adding 
  "from scan_framework import *" now imports the analysis.curvefits submodule with the alias of curvefits.
- The 'frequency_center' attribute has been replaced by '_x_offset' attribute
- TimeFrequencyScan renamed to TimeFreqScan
- FrequencyScan renamed to FreqScan
- Renamed FrequencyModel to FreqModel
- Renamed TimeFrequencyModel to TimeFreqModel
- Removed analysis lib/functions.py
- Renamed the scanning folder to scans
- Removed loc argument from scan\_arguments()
- Added arguments to the scan_arguments() method that allow each GUI argument to be customized or to be omitted (not created)
- Removed the frequency\_center\_default, pulse\_time\_default, freq\_unit, freq\_scale, freq\_start, and freq\_stop attributes from the TimeFreqScan class.  These options are now all supported by the new scan\_arguments() method.
  
### Updating code that uses the old artiq\_ions version of the scan class to work with the new  scan\_framework

1. Search all files in your repository for "artiq\_ions.scanning" and replace each instance with scan\_framework.scans
2. Search all files in your repository for "artiq\_ions" and replace each instance with scan\_framework.
3. Search all files in your repository for "TimeFrequencyScan" and replace each instance with TimeFreqScan.
4. Search all files in your repository for "FrequencyScan" and replace each instance with FreqScan.
5. Search all files in your repository for "frequency\_center\_default", remove these sections and instead set the 'default' key of the 'frequency\_center' dictionary argument of self.scan\_arguments().
6. Search all files in your repository for "freq\_unit", remove these sections and instead set the 'unit' key of either the 'frequencies' or 'frequency\_center' dictionary arguments of self.scan\_arguments().
7. Search all files in your repository for "freq\_scale", remove these sections and instead set the 'unit' key of either the 'frequencies' or 'frequency\_center' dictionary arguments of self.scan\_arguments().
8. Search all files in your repository for "freq\_start" and "freq\_stop", remove these sections and instead set the 'start' and 'stop' keys of the 'frequencies' dictionary argument of self.scan\_arguments().
9. Search all files in your repository for "pulse\_time\_default", remove these sections and instead set the 'default' key of the 'pulse\_time' dictionary argument of self.scan\_arguments().
10. Search all files in your repository for "self.scan_arguments(".  Remove each result that uses the 'loc' argument and instead explicitly indicate which scan arguments should not be rendered by setting their corresponding arguments to False.  For example, if you want to add the npasses, nrepeats, and nbins arguments to the gui in one location and then add the fit_options later in your code, make two calls to self.scan\_arguments().  First call self.scan_arguments(fit_options=False), then later call self.scan_arguments(npasses=False, nrepeats=False, nbins=False)
