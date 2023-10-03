import inspect
from artiq.language import *
from ..language import *

class FitArguments:

    def __init__(self):
        self._fit_guesses = {}
        self._fit_holds = {}

    def setattr_argument(self, obj, key, processor=None, group=None, show='auto', tooltip=None):
        # fit guesses
        if isinstance(processor, FitGuess):
            if group is None:
                group = 'Fit Settings'
            setattr_argument(obj, key, NumberValue(default=processor.default_value,
                                                      ndecimals=processor.ndecimals,
                                                      step=processor.step,
                                                      unit=processor.unit,
                                                      min=processor.min,
                                                      max=processor.max,
                                                      scale=processor.scale), group)
            use = None
            if processor.use is 'ask':
                setattr_argument(obj, 'use_{0}'.format(key), BooleanValue(default=processor.use_default), group)
                use = getattr(obj, 'use_{0}'.format(key))
            else:
                use = processor.use

            self._fit_guesses[key] = {
                'fit_param': processor.fit_param,
                'param_index': processor.param_index,
                'use': use,
                'value': getattr(obj, key)
            }
            return True
        elif isinstance(processor, FitHold):
            if group is None:
                group = 'Fit Settings'
            setattr_argument(obj, key, NumberValue(default=processor.default_value,
                                                      ndecimals=processor.ndecimals,
                                                      step=processor.step,
                                                      unit=processor.unit,
                                                      min=processor.min,
                                                      max=processor.max,
                                                      scale=processor.scale), group)
            use = None
            if processor.use is 'ask':
                setattr_argument(obj, 'use_{0}'.format(key), BooleanValue(default=processor.use_default), group)
                use = getattr(obj, 'use_{0}'.format(key))
            else:
                use = processor.use

            self._fit_holds[key] = {
                'fit_param': processor.fit_param,
                'param_index': processor.param_index,
                'use': use,
                'value': getattr(obj, key)
            }
            return True
        else:
            return False

    def guesses(self, fit_function):
        """Maps GUI arguments to fit guesses.  """
        if fit_function:
            guesses = {}
            signature = inspect.getargspec(getattr(fit_function, 'value')).args
            # map gui arguments to fit guesses
            for key in self._fit_guesses.keys():
                g = self._fit_guesses[key]
                if g['use']:
                    # generic fit guess gui arguments specified by position in the fit function signature
                    if g['fit_param'] == None and g['param_index'] != None:
                        i = g['param_index']
                        if i < len(signature):
                            g['fit_param'] = signature[i]
                    if g['fit_param'] is not None:
                        guesses[g['fit_param']] = g['value']
            return guesses
        else:
            return None

    def holds(self, fit_function):
        """Maps GUI arguments to fit guesses.  """
        if fit_function:
            guess = {}
            signature = inspect.getargspec(getattr(fit_function, 'value')).args
            # map gui arguments to fit guesses
            for key in self._fit_holds.keys():
                g = self._fit_holds[key]
                if g['use']:
                    # generic fit guess gui arguments specified by position in the fit function signature
                    if g['fit_param'] is None and g['param_index'] is not None:
                        i = g['param_index']
                        if i < len(signature):
                            g['fit_param'] = signature[i]
                    if g['fit_param'] is not None:
                        guess[g['fit_param']] = g['value']
            return guess
        else:
            return None
