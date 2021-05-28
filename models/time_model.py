# -*- coding: utf8 -*-
#
# Author: Philip Kent / NIST Ion Storage & NIST Quantum Processing
# 2016-2021
#

from scan_framework.models.scan_model import *


class TimeModel(ScanModel):
    @property
    def x_scale(self):
        return us

    @property
    def x_units(self):
        return 'us'