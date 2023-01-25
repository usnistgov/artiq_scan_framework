from artiq.language import NumberValue

class FitGuess(NumberValue):
    def __init__(self, fit_param=None, param_index=None, use_default=True, use=True, i_result=None, *args, **kwargs):
        self.i_result = i_result
        self.fit_param = fit_param
        self.use_default = use_default
        self.param_index = param_index
        self.use = use
        super().__init__(*args, **kwargs)


class FitHold(NumberValue):
    def __init__(self, fit_param=None, param_index=None, use_default=True, use=True, i_result=None, *args, **kwargs):
        self.i_result = i_result
        self.fit_param = fit_param
        self.use_default = use_default
        self.param_index = param_index
        self.use = use
        super().__init__(*args, **kwargs)