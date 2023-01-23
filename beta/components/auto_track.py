from artiq.experiment import *


class AutoTrack(HasEnvironment):

    def get_x_offset(self):
        if self.scan.enable_auto_tracking:
            for entry in self._model_registry:
                model = entry['model']
                if 'auto_track' in entry and entry['auto_track']:
                    # use the last performed fit
                    if entry['auto_track'] == 'fitresults' and hasattr(model, 'fit'):
                        return model.fit.fitresults[model.main_fit]
                    # use dataset value
                    elif entry['auto_track'] == 'fit' or entry['auto_track'] is True:
                        return model.get_main_fit(archive=False)

        # default to no offset if none of the above cases apply
        return 0.0

    def get_fitted_param(self, model, use_fit_result, types=[]):
        def get_mapping(mapping):
            if type(mapping) != list:
                mapping = [mapping, mapping]
            return mapping

        for type in types:
            # would like to migrate to this method, or something similar.  more explicit
            # model defines the dataset name for the fit param explicitly
            type_attrib = '{}_fit'.format(type)
            if hasattr(model, type_attrib):
                param_name, ds_name = get_mapping(getattr(model, type_attrib))
                if use_fit_result:
                    return model.fitresults[param_name]
                else:
                    return model.get(ds_name, archive=False)
            # would like to phase this out.  somewhat implicit.
            # model returns different values for its 'main_fit' attribute,
            # depending on the value of it's 'type' attribute
            elif hasattr(model, 'type'):
                restore = model.type
                model.type = type
                model.bind()
                fit = model.get_main_fit(archive=False)
                model.type = restore
                model.bind()

    def get_main_fit(self, use_fit_result=False, i=None, archive=False) -> TFloat:
        """Helper method. Fetches the value of the main fit from its dataset or from the fitresults.

        :param use_fit_result: If True, the fit param value in the models fit object is returned. Otherwise
                               the fir param value will be fetched from the datasets.
        value.
        """
        if use_fit_result:
            if self.main_fit_param is None:
                raise Exception("Can't get the main fit.  The 'main_fit' attribute needs to be set in the scan model.")
            return self.fit.fitresults[self.main_fit_param]
        else:
            if self.main_fit_ds is None:
                raise Exception("Can't get the main fit.  The 'main_fit' attribute needs to be set in the scan model.")
            return self.get(self.main_fit_ds, archive=archive)
