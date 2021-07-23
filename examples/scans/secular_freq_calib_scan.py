# Real world example scan: secular frequency calibration scan
# Demonstrates how to extend an already defined scan.
#
# Author: Philip Kent / NIST Quantum Processing Group
#
# Note: This example cannot be run as a number of dependencies are not included.
# This scan is provided to give an example of usage of the scan framework in
# an actual lab experiment.


from artiq.experiment import *
import scan_framework.examples.scans.tickle_scan as ts


class SecularFreqCalibScan(ts.TickleScan):
    """Secular Freq Calibration Scan"""
    auto_track = True
    offset_shims = True