# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added 

- Added support for ARTIQ version 6 in the artiq-6 branch
- Version 2.0: Added support for returning multiple measurements from the `measure()` method 

## [2.0.0] - 2021-05-27

### Added

- All existing files for the scan framework currently used at NIST.
Changes from previous in-house version of the scan framework
- TimeFrequency renamed to ScanTimeFreqScan
- FrequencyScan renamed to FreqScan
- Removed analysis function in lib/functions.py
- Renamed the scanning folder to scans
- Renamed Frequency model to FreqModel
- Renamed TimeFrequencyModel to TimeFreqModel
- Removed loc argument from scan_arguments()
- Added arguments to scan_arguments() that allow each GUI argument to be customized or to be omitted (not created)
- Removed the frequency_center_default, pulse_time_default, freq_unit, freq_scale, freq_start, and freq_stop attributes
  from the TimeFreqScan class.  These options are now all supported by the new scan_arguments() method.
