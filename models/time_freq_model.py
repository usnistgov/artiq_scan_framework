# -*- coding: utf8 -*-
#
# Author: Philip Kent / NIST Ion Storage & NIST Quantum Processing
# 2016-2021
#

from scan_framework.models.scan_model import *


class TimeFreqModel(ScanModel):
    @property
    def x_scale(self):
        if self.type == 'frequency':
            return MHz
        if self.type == 'time':
            return us

    @property
    def x_units(self):
        if self.type == 'frequency':
            return 'MHz'
        if self.type == 'time':
            return 'us'
