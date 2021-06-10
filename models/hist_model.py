# -*- coding: utf8 -*-
#
# Author: Philip Kent / NIST Ion Storage & NIST Quantum Processing
# 2016-2021
#
from scan_framework.models.model import *
import numpy as np
from artiq.language.core import *


class HistModel(Model):
    namespace = ""
    mirror_namespace = "current_hist"
    mirror = True
    discrete = True  # True indicates discrete values are being binned (e.g. counts)
    aggregate = False

    # plots
    x_label = ""
    y_label = ""
    x_units = 1
    plot_title = ""

    def build(self, **kwargs):
        super().build(**kwargs)

    def init_bins(self, bin_start, bin_end, nbins):
        """Initialize internal bin boundaries and bins variables"""
        self.bin_start = bin_start
        self.bin_end = bin_end
        self.nbins = nbins

        if self.discrete:
            self.bin_size = (self.bin_end - self.bin_start) / (self.nbins - 1)
            self.bin_boundaries = np.linspace(self.bin_start - 0.5, self.bin_end + 0.5, self.nbins + 1)
        else:
            self.bin_size = (self.bin_end - self.bin_start) / self.nbins
            self.bin_boundaries = np.linspace(self.bin_start, self.bin_end, self.nbins + 1)
        self.bins = np.full(self.nbins, fill_value=0, dtype=np.integer)

        # aggregate hists
        self.aggregate_bins = np.full(self.nbins, fill_value=0, dtype=np.integer)
        self.mirror_aggregate_bins = np.full(self.nbins, fill_value=0, dtype=np.integer)
        self.reset_bins()

    @portable
    def reset_bins(self):
        """Reset internal bins array to all zeros"""
        for i in range(self.nbins):
            self.bins[i] = 0

    @portable
    def reset_aggregate_bins(self):
        """Reset internal bins array to all zeros"""
        if self.aggregate:
            for i in range(self.nbins):
                self.aggregate_bins[i] = 0
                self.mirror_aggregate_bins[i] = 0

    def init_datasets(self, broadcast=None, persist=None, save=None):
        """Initialize all datasets"""
        self.set('bin_boundaries', self.bin_boundaries, broadcast=broadcast, persist=persist, save=save, mirror=True)
        self.set('x_units', self.x_units, broadcast=broadcast, persist=persist, save=save)
        self.set('x_label', self.x_label, broadcast=broadcast, persist=persist, save=save)
        self.set('y_label', self.y_label, broadcast=broadcast, persist=persist, save=save)
        self.set('plot_title', self.plot_title, broadcast=broadcast, persist=persist, save=save)
        self.set('bins', self.bins, broadcast=broadcast, persist=persist, save=save)

        if self.aggregate:
            self.set('aggregate_bin_boundaries', self.bin_boundaries, which='mirror', mirror=True)
            self.set('aggregate_bin_boundaries', self.bin_boundaries, broadcast=broadcast, persist=persist, save=save,
                     which='main', mirror=False)
            self.set('aggregate_bins', self.mirror_aggregate_bins, which='mirror', mirror=True)
            self.set('aggregate_bins', self.aggregate_bins, broadcast=broadcast, persist=persist, save=save, which='main', mirror=False)

    def mutate(self, values, broadcast=None, persist=None, save=None):
        """Bin each value and mutate the bins dataset"""
        if self.aggregate:
            self.mirror_aggregate_bins = self.get('aggregate_bins', mirror=True)

        if isinstance(values, list) or isinstance(values, np.ndarray):
            for val in values:
                self.bin_value(val)
        else:
            self.bin_value(values)
        self.set_bins(broadcast=broadcast, persist=persist, save=save)

    @portable
    def set_bins(self, broadcast=None, persist=None, save=None):
        self.set('bins', self.bins, broadcast=broadcast, persist=persist, save=save)
        if self.aggregate:
            self.set('aggregate_bins', self.aggregate_bins, broadcast=broadcast, persist=persist, save=save, which='main')
            self.set('aggregate_bins', self.mirror_aggregate_bins, broadcast=broadcast, persist=persist, save=save, which='mirror', mirror=True)

    @portable
    def bin_value(self, value):
        """Bin a value and update self.bins"""
        bin = int((value - self.bin_start) / self.bin_size)

        if bin >= self.nbins:
            bin = self.nbins - 1
        self.bins[bin] += 1
        if self.aggregate:
            self.aggregate_bins[bin] += 1
            self.mirror_aggregate_bins[bin] += 1