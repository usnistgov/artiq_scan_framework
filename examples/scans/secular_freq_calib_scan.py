import scan_framework.tickle_scan as ts


class SecularFreqCalibScan(ts.TickleScan):
    """Secular Freq Calibration Scan"""
    auto_track = True
    offset_shims = True