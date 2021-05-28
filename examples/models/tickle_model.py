from scan_framework import *


class TickleModel(Model):
    namespace = "tickle.%mode"  #: Dataset namespace
    default_fallback = True

    def build_datasets(self):
        """Create missing tickle datasets"""

        # code isn't falling back to defaults for these
        self.create('frequency', 500 * MHz)
        self.create('mode_1.defaults.frequency', 500 * MHz)
        self.create('mode_2.defaults.frequency', 500 * MHz)


class TickleScanModel(TickleModel, FreqModel):
    """Models ion interaction with the trap tickle."""
    fit_function = fit_functions.SincInv
    main_fit = 'frequency'
    default_fallback = True

    @property
    def simulation_args(self):
        auto_track = hasattr(self.scan, 'auto_track') and self.scan.auto_track
        if self.mode == 'mode_1':
            return {
                'y_min': 1.5,
                'y_max': 10,
                'pi_time': 1*us,
                'frequency': self.scan.frequency_center if auto_track else 1*MHz
            }
        if self.mode == 'mode_2':
            return {
                'y_min': 1.5,
                'y_max': 10,
                'pi_time': 1*us,
                'frequency': self.scan.frequency_center if auto_track else 2*MHz
            }

    @property
    def pre_validators(self):
        return {
            "y_data": {
                "height": {
                    'min_height': 1
                }
            }
        }

    @property
    def strong_validators(self):
        """Scan is halted with a BadFit exception when these validations fail."""
        return {
            "params.y_max": {
                "validate_fit_height": {
                    "min_height": 1.5
                },
            },
            "params.frequency": {
                "between": {
                    "min_": self.scan.min_point - self.tick,
                    "max_": self.scan.max_point + self.tick
                }
            }
        }

    def validate_fit_height(self, field, y_max, min_height):
        """Validates height of y_max above y_min"""
        y_min = self.fit.fitresults['y_min']
        if y_max - y_min >= min_height:
            return True
        else:
            self.validation_errors[field] = "Fitted amplitude of {0} less than minimum " \
                                            "amplitude for tickle fits of {1}" .format(round(y_max-y_min, 1), min_height)
            return False

    # plots
    @property
    def plot_title(self):
        return "Tickle"
