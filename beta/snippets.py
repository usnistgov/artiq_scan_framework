from artiq.experiment import *
from artiq_scan_framework.exceptions import Paused
import numpy as np


@portable
def check_pause(obj):
    # cost: 3.6 ms
    if obj.scheduler.check_pause():
        # yield
        raise Paused


def get_registered_models(scan, **kwargs):
    entries = []
    for entry in scan._model_registry:
        append = True
        for k, v in kwargs.items():
            if entry[k]:
                if isinstance(v, bool):
                    pass
                elif isinstance(v, list):
                    if entry[k] not in v:
                        append = False
                    break
                else:
                    if entry[k] != v:
                        append = False
        if append:
            entries.append(entry)
    return entries


def get_meas_models(scan, measurement):
    models = []
    for entry in scan._model_registry:
        # model registered for this measurement
        if entry['measurement']:
            models.append(entry['model'])
    return None


@rpc(flags={"async"})
def set_counts(obj, mean, digits=-1):
    if digits >= 0:
        mean = round(mean, digits)
    obj.set_dataset('counts', mean, broadcast=True, persist=True)


def get_points(scan):
    if scan._points is None:
        points = list(scan.get_scan_points())
    else:
        points = list(scan._points)
    return points


def get_warmup_points(scan):
    if scan._warmup_points is None:
        warmup_points = scan.get_warmup_points()
    else:
        warmup_points = list(scan._warmup_points)
    return warmup_points


def trigger_plot(model):
    model.set('plots.trigger', 1, which='mirror')
    model.set('plots.trigger', 0, which='mirror')




