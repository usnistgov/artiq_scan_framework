# -*- coding: utf8 -*-
#
# Author: Philip Kent / NIST Ion Storage & NIST Quantum Processing
# 2016-2021
#
from scan_framework.models.scan_model import *


class FrequencyModel(ScanModel):
    @property
    def x_scale(self):
        return MHz

    @property
    def x_units(self):
        return 'MHz'

