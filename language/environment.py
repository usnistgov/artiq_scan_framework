


def setattr_argument(self, key, processor=None, group=None, show='auto', tooltip=None, ds_default=None, ds_default_scale=1.0):
    if ds_default is not None:
        try:
            processor.default_value = self.get_dataset(ds_default, archive=False)*ds_default_scale
        except KeyError:
            pass
    if show is 'auto' and hasattr(self, key) and getattr(self, key) is not None:
        return
    self.setattr_argument(key, processor, group, tooltip=tooltip)
    # set attribute to default value when class is built but not submitted
    if hasattr(processor, 'default_value'):
        if not hasattr(self, key) or getattr(self, key) is None:
            setattr(self, key, processor.default_value)
    if ds_default is not None:
        try:
            self.set_dataset(ds_default, getattr(self, key)/ds_default_scale, broadcast=True, save=True, persist=True)
        except AttributeError:
            pass