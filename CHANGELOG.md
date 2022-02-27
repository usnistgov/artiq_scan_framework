# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added 

- Added support for ARTIQ version 6 in the artiq-6 branch
- Version 2.0: Added support for returning multiple measurements from the `measure()` method 

## [2.1.0] - 2021-07-27

- Fixed outdated unittests to work in ARTIQ version 3
- The mutate_datasets(), _set_counts(), & _calculate_all() scan callbacks are now asynchronouse (fire and forget) 
  remote procedure calls.
- Added ability to plot a fitline in the histogram plotting applet

## [2.0.0] - 2021-07-13

### Added

- All existing files for the scan framework currently used at NIST.

### Changes from previous in-house version of the scan framework:
- The previous alias of "fitting" for analysis.curvefits has been renamed to "curvefits".  Adding 
  "from scan_framework import *" now imports the analysis.curvefits submodule with the alias of curvefits. 
- The 'frequency_center' attribute has been replaced by '_x_offset' attribute
- TimeFrequencyScan renamed to TimeFreqScan
- FrequencyScan renamed to FreqScan
- Renamed FrequencyModel to FreqModel
- Renamed TimeFrequencyModel to TimeFreqModel
- Removed analysis lib/functions.py
- Renamed the scanning folder to scans
- Removed loc argument from scan_arguments()
- Added arguments to the scan_arguments() method that allow each GUI argument to be customized 
  or to be omitted (not created)
- Removed the frequency_center_default, pulse_time_default, freq_unit, freq_scale, freq_start, and 
  freq_stop attributes from the TimeFreqScan class.  These options are now all supported by the new 
  scan_arguments() method.
