# -*- coding: utf8 -*-
#
# Author: Philip Kent / NIST Ion Storage & NIST Quantum Processing
# 2016-2021
#
from artiq.language.environment import NoDefault
from artiq.language import *
import numpy as np


#TODO:  Several methods need doc comments
class Model(HasEnvironment):
    """Class for encapsulating datsaet handling"""
    namespace = ""
    mirror_namespace = "current"
    mirror = False              #: Set to True to enable dataset mirroring or False to disable dataset mirroring.
    errors = {}
    valid = True
    validators = {}             #: Dictionary containing definitions all fit validations
    broadcast = True            #: If true the default behavior is to broadcast datasets when they are created.
    persist = True              #: If true the default behavior is to persist datasets when they are created.
    save = True                 #: If true the default behavior is to archive datasets to the hdf5 file when they are created.
    default_fallback = False

    def build(self, bind=True, **kwargs):
        """Build the model.

        :param namespace: Tokened namespace of the model.  All dataset keys passed to get(), set(),
                          mutate(), and exists() are prefixed with the namespace.
        :param mirror_namespace: Tokened namespace of the mirror.  All changes to datasets through set() and
                                 mutate() are mirrored under this namespace.
        :param bind: Map the namespace and mirror namespace and bind future calls to them.  If set to False,
                     bind should be called manually.
        :param mirror: If True, all datasets set or mutated will be mirrored to the mirror namespace.  Can
                       be disabled by setting model.mirror = False after model is built.
        """
        self.__dict__.update(kwargs)
        self._namespace = self.namespace
        self._mirror_namespace = self.mirror_namespace
        self.validation_errors = {}
        if bind:
            self.bind()

    # --- namespace binding methods

    def bind(self, **kwargs):
        """ Map the namespace and mirror namespace from the model's current attribute values
        and bind all future dataset access to those namespaces"""
        self.__dict__.update(kwargs)
        if self._namespace:
            self.namespace = self.map_namespace(self._namespace)
        if self._mirror_namespace:
            self.mirror_namespace = self.map_namespace(self._mirror_namespace)
        return self

    def map_namespace(self, namespace):
        """Replace tokens in the provided namespace with model attributes of the same name.
        If there is not a model attribute for a token it is omited.
        Example: model.build_namespace("raman.%temp.%transition") will return "raman.m1_rsb"
        if model.transition is set to "m1_rsb" but model.temp does not exist.
        """

        s = namespace.split('/')
        _namespace = []
        for key in s[0].split('.'):
            if "%" in key:
                key = key.replace("%", "")
                if hasattr(self, key):
                    val = getattr(self, key)
                    _namespace.append(str(val))
            else:
                _namespace.append(key)

        return ".".join(_namespace)

    def key(self, key, mirror=False):
        """Prefix key with the namespace and return the prefixed key.
        :param mirror: Set to True to return key prefixed with the mirror namespace instead.
        """
        if isinstance(key, list):
            key = ".".join(key)
        if mirror:
            if self.mirror_namespace.strip():
                return self.mirror_namespace + "." + key
            else:
                return key
        else:
            if self.namespace.strip():
                return self.namespace + "." + key
            else:
                return key

    def default_key(self, key):
        """Returns the dataset key where default values for the dataset identified by key are stored.
        For example, if key is raman.rsb.frequency, the key raman.rsb.defaults.frequency will be returned.

        :param key: Key of the datset whose default values are needed.
        :returns: Key of the data set that contains the default values for key.
        :rtype: string
        """
        key = key.split(".")
        key.append(key[-1])
        key[-2] = 'defaults'
        return self.key(".".join(key))

    def init(self, key, shape=0, varname=None, fill_value=np.nan, dtype=np.float64, init_local=True,
             broadcast=None, persist=None, save=None, which='both'):
        """Set a dataset with the specified shape and initializes its values to the specified fill_value.
        A local member variable of the model can also be initialized to the same value as the dataset.  This
        is useful when using methods like mutate() which updates the local variable with values as the associated
        dataset is mutated.

        :param key: The datsaet key.  This key will be prefixed with the namespace automatically
        :type key: String
        :param shape: The shape of the data.  See numpy.full.
        :type shape: Integer or tuple
        :param fill_value: Initialize the each element of the dataset to this value.  See numpy.full.
        :type fill_value: Any data time
        :param dtype: The datatype of each element of the dataset.  See numpy.full.
        :type dtype: Numpy datatype
        :param init_local: Set to True to also set a member variable of the model which contains the a copy of the
                           data that is written to the dataset.  The variables name defaults to the key parameter
                           if none is provided.
        :type init_local: Boolean
        :param varname: The name of the variable which will contain a local copy of the dataset.
        :param broadcast: When setting the dataset, this value of the broadcast argument is used. see ARTIQ
                          documentation.
        :type broadcast: Boolean
        :param persist: When setting the dataset, this value of the persist argument is used. see ARTIQ documentation.
        :type persist: Boolean
        :param save: When setting the dataset, this value of the save argument is used. see ARTIQ documentation.
        :type save: Boolean
        :param which:  ['both', 'main', or 'mirror'] Set to 'both' (default) to set the datasets under both the model
                       namespace and mirror namespace, set to 'main' to set only the dataset under the model namespace,
                       set to 'mirror' to set only the dataset under the mirror namespace.
        :type which: String

        """

        # default variable name to key
        if varname is None:
            varname = key

        # the initialized value
        if shape is not 0:
            value = np.full(shape, fill_value, dtype)
        else:
            value = fill_value

        # initialize the local variable
        if init_local:
            setattr(self, varname, value)

        # set the dataset
        self.set(key, value, which, broadcast, persist, save)

    def load(self, key, varname=None, default=NoDefault, mirror=False, archive=True):
        """Assign the value stored in a dataset to an attribute of the model.
        :param key: The dataset's key.
        :param varname: The name of the model attribute.  Defaults to the value of the key argument.
        :param default: Default value to use if the datset doesn't exist.
        :param mirror: Set to True to load the value of the datset stored under the mirror namespace instead.
        """
        if varname is None:
            varname = key
        setattr(self, varname, self.get(key, default, mirror, archive=archive))
        return self

    def write(self, key, varname=None, which='both', broadcast=None, persist=None, save=None):
        """Set a dataset with the value of an attribute of the model.

        :param key: Key of the dataset to set.
        :param varname: The name of the model attribute.  Defaults to the value of the key argument.
        :param which: Set to 'both' (default) to set the datasets stored under
                      both the model namespace and mirror namespace, set to 'main' to set only the dataset
                      stored under the model namespace, set to 'mirror' to set only the dataset stored under
                      the mirror namespace.
        :type which: String ['both', 'main', or 'mirror']
        :param broadcast: When setting the dataset, this value of the broadcast argument is used. see ARTIQ
                          documentation.
        :param persist: When setting the dataset, this value of the persist argument is used. see ARTIQ documentation.
        :param save: When setting the dataset, this value of the save argument is used. see ARTIQ 1documentation.

        """

        # default variable name to key
        if varname is None:
            varname = key

        # fetch local value
        value = getattr(self, varname)

        # set local value to it's dataset
        self.set(key, value, which, broadcast, persist, save)

    def set(self, key, value=None, which='both', broadcast=None, persist=None, save=None, mirror=None):
        """Set the dataset with the specified key to the specified value.  By default, the dataset is also
          set under the mirror namespace.

        :param key: The datsaet key.  This key will be prefixed with the namespace automatically.
        :type key: String
        :param value: The value to write to the dataset.
        :type value: Any datatype
        :param which: Set to 'both' (default) to set the datasets under
                      both the model namespace and mirror namespace, set to 'main' to set only the dataset under
                      the model namespace, set to 'mirror' to set only the dataset under the mirror namespace.
        :type which: String ['both', 'main', or 'mirror']
        :param broadcast: When setting the dataset, this value of the broadcast argument is used. see ARTIQ
                          documentation.
        :type broadcast: Boolean
        :param persist: When setting the dataset, this value of the persist argument is used. see ARTIQ documentation.
        :type persist: Boolean
        :param save: When setting the dataset, this value of the save argument is used. see ARTIQ documentation.
        :type save: Boolean
        """

        # write all lists an numpy arrays
        if isinstance(value, list):
            value = np.array(value)

        # default these to class settings
        if broadcast is None:
            broadcast = self.broadcast
        if persist is None:
            persist = self.persist
        if save is None:
            save = self.save

        # set the main dataset
        if which == 'both' or which == 'main':
            self.set_dataset(self.key(key), value, broadcast=broadcast, persist=persist, save=save)

        # set the mirror dataset
        if mirror or (self.mirror and (which in ['both', 'mirror'])):
            self.set_dataset(self.key(key, mirror=True), value, broadcast=True, persist=True, save=True)

    def get_default(self, key, archive=False):
        """Get the dataset that contains default values for the dataset specified by key.
        :param key: Key of the dataset whose default dataset will be returned."""
        return self.get_dataset(self.default_key(key), archive=archive)

    def get(self, key, default=NoDefault, mirror=False, default_fallback=None, archive=True):
        """Get the value of a dataset that is stored under the model namespace or the mirror namespace.
        :param key: The dataset key.  The key is automatically prefixed with either the model or mirror namespace.
        :param default: The default value to return if the dataset does not exist.
        :param default_fallback: If True and no value for the default argument is provided, attempt to
        use the default value stored in the default dataset for the specified key.  If no default dataset exists,
        and the main dataset do not exist, a KeyError exception is thrown.
        :param mirror: Set to True to get the value of the datset stored under the mirror namespace
        """
        if isinstance(key, list):
            vals = {}
            for k in key:
                vals[k] = self.get(k, default, mirror, default_fallback)
            return vals
        if (self.default_fallback or default_fallback is True) and default == NoDefault:
            try:
                default = self.get_default(key)
            except KeyError:
                default = NoDefault
        return self.get_dataset(self.key(key, mirror), default=default, archive=archive)

    def mutate(self, key, i, value, which='both', varname=None, update_local=True):
        """Prefix key with the namespace and call self.mutate_dataset() using the prefixed key.
        Prefix key with the mirror namespace and call self.mutate_dataset() using the prefixed key
        (if mirroring is enabled).

        :param which ['both', 'main', or 'mirror']:  Set to 'both' (default) to mutate the datasets under
         both the model namespace and mirror namespace, set to 'main' to mutate only the dataset under the model
         namespace, set to 'mirror' to set only the dataset under the mirror namespace.
        """

        if update_local:
            if varname is None:
                varname = key

            # update local variable
            if hasattr(self, varname):
                var = getattr(self, varname)
                var[i] = value
        if which == 'both' or which == 'main':
            self.mutate_dataset(self.key(key), i, value)
        if self.mirror and (which == 'both' or which == 'mirror'):
            self.mutate_dataset(self.key(key, mirror=True), i, value)

    def exists(self, key):
        """Return true if a dataset with the specified key exists under the model namespace.
        :param key: Key of the dataset, this will be automatically prefixed with the model namespace.
        """
        try:
            self.get(key)
        except(KeyError):
            return False
        return True

    def create(self, key, value):
        """Create dataset if it doesn't already exist"""
        if not self.exists(key):
            self.set(key, value)

    def setattr(self, key, default=NoDefault, archive=True):
        """Set the contents of a dataset under the model namespace as a class attribute. The name of the
        dataset and the name of the attribute are the same."""
        setattr(self, key, self.get_dataset(self.key(key), default=default, archive=archive))

    # --- validation helpers
    def _get_validation_func(self, method):
        # get the validation function
        if hasattr(self, method):
            func = getattr(self, method)
        else:
            func = getattr(self, 'validate_%s' % method)
        return func

    def _call_validation_method(self, method, field, value, args):
        func = self._get_validation_func(method)
        if isinstance(args, dict):
            return func(field, value, **args)
        elif isinstance(args, list):
            return func(field, value, *args)
        else:
            return func(field, value, args)

    def validate_greater_than(self, field, value, min_):
        """Return False if value <= min\_ and add a validation error for the field."""
        if value <= min_:
            _, _, sval = Model._format(field, value)
            _, _, smin = Model._format(field, min_)
            self.validation_errors[field] = "{0} of {1} is not greater than {2}".format(field, sval, smin)
            return False
        return True

    def validate_less_than(self, field, value, max_):
        """Return False if value >= max\_ and add a validation error for the field."""
        if value >= max_:
            _, _, sval = Model._format(field, value)
            _, _, smax = Model._format(field, max_)
            self.validation_errors[field] = "{0} of {1} is not less than {2}".format(field, sval, smax)
            return False
        return True

    def validate_between(self, field, value, min_, max_):
        """Return False if value is not between min\_ and max\_ and add a validation error for the field."""
        if not min_ <= value <= max_:
            _, _, sval = Model._format(field, value)
            _, smin, _ = Model._format(field, min_)
            _, _, smax = Model._format(field, max_)
            self.validation_errors[field] = "{0} of {1} is not between {2} and {3}".format(field, sval, smin, smax)
            return False
        return True

    def validate_max_change(self, field, value, max_diff, prev_value):
        """Return False if value has changed by more than max_diff from it's previous value and add a validation
        error for the field."""
        if value - prev_value > max_diff:
            _, _, sval = Model._format(field, value)
            _, _, sdiff = Model._format(field, max_diff)
            _, _, sprev = Model._format(field, prev_value)
            self.validation_errors[field] = "{0} of {1} has changed by more than {2} from " \
                                 "it's previous value of {3}".format(field, sval, sdiff, sprev)
            return False
        return True

    def validate_height(self, series_name, data, min_height, error_msg=None):
        """Return False if the difference between the max value in data and the min value in data is greater or equal
        to the specified minimum height and add a validation error for the field."""
        """Validates height of y_max above y_min"""
        height = max(data) - min(data)
        if height >= min_height:
            return True
        else:
            if error_msg is None:
                error_msg = "Span of ydata ({0}) is less than {2}."
            self.validation_errors[series_name] = error_msg .format(round(height,1), series_name, min_height)
            return False

    @staticmethod
    def _format(key, value, obj=None):
        unit = ''
        scaled = value
        if isinstance(value, float):
            if obj is not None and hasattr(obj, 'scales') and key in obj.scales:
                scale = obj.scales[key]['scale']
                unit = obj.scales[key]['unit']
                scaled = value / scale
            else:
                if Model._is_frequency_param(key):
                    scale = MHz
                    unit = 'MHz'
                    scaled = value / scale
                if Model._is_time_param(key):
                    scale = us
                    unit = 'us'
                    scaled = value / scale
            scaled = round(scaled, 3)
        if unit:
            text = "{0} {1}".format(scaled, unit)
        else:
            text = scaled
        return unit, scaled, text

    @staticmethod
    def _is_frequency_param(param):
        if 'frequency' in param:
            return True
        return False

    @staticmethod
    def _is_time_param(param):
        if 'pi_time' in param:
            return True
        return False
