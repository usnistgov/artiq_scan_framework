#!/usr/bin/env python3.5
# -*- coding: utf8 -*-
#
# Author: Philip Kent / NIST Ion Storage & NIST Quantum Processing
# 2016-2021
#
# Base class for plot applets used in the NIST scan framework
import artiq.applets.simple as plot_xy_parent
import pyqtgraph


class SimpleApplet(plot_xy_parent.SimpleApplet):

    def __init__(self, main_widget_class, cmd_description=None,
                 default_update_delay=0.0):
        super().__init__(main_widget_class, cmd_description, default_update_delay)
        self.add_datasets()

    def add_datasets(self):
        pass


class Plot(pyqtgraph.PlotWidget):
    """Base class for plot applets.  Provides a basic framework for plot applets.  When data has changed, dataset values
    are loaded, reshaped (optional), validated, cleaned, and plotted."""
    style = {
        'background': {
            'color': 'w'
        },
        'foreground': {
            'color': 'k'
        }
    }  #: default colors are white background with black foreground

    def get_style(self, key, i=0):
        """Helper method to get a style value using a dotted key.  For example, self.style['background']['color'] can
        be returned by passing key='background.color'"""
        entry = self.style
        for k in key.split('.'):
            entry = entry[k]
        try:
            if not isinstance(entry, dict):
                entry = entry[i % len(entry)]
        except TypeError:
            pass
        return entry

    def __init__(self, args):
        self.args = args
        self.set_config(pyqtgraph)
        pyqtgraph.PlotWidget.__init__(self)

    def set_config(self, pyqtgraph):
        pyqtgraph.setConfigOption('background', self.style['background']['color'])
        pyqtgraph.setConfigOption('foreground', self.style['foreground']['color'])

    def data_changed(self, data, mods):
        """Data changed handler.  load, reshape, validate, clean, and then plot the new data."""
        if self.load(data) is not False:
            self.reshape()
            try:
                pass
            except ValueError:
                print("Error reshaping")
                pass
            else:
                if self.validate() is not False:
                    self.clean()
                    self.clear()
                    self.draw()

    def load(self, data):
        """Load the data from datasets"""
        pass

    def reshape(self):
        """Reshape data into the correct dimension"""
        pass

    def clean(self):
        """Clean the data so it can be plotted"""
        pass

    def validate(self):
        """Validate the data can be plotted"""
        pass

    def draw(self):
        """Plot the data"""
        pass

    def _load(self, data, key, ds_only=True, default=None):
        """Helper method to load a single dataset value and assign it to an attribute of self.

        Falls back to an explicit value being specified in arguments or a given default value when the
        dataset doesn't exist.
        """
        if isinstance(key, list):
            for k in key:
                self._load(data, k, default)
            return

        argval = getattr(self.args, key)
        val = data.get(argval, (False, default))
        ds_found = val[0]

        if ds_found:
            # get value from dataset
            if val[1] is not None:
                val = val[1]
            else:
                val = None
        else:
            if argval is not None and not ds_only:
                val = argval
            else:
                val = default

        setattr(self, key, val)