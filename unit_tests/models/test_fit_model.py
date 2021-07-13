from scan_framework.unit_tests.test_case import *
from scan_framework.models.fit_model import *
import scan_framework.analysis.fit_functions as fit_functions


# test validation of fit params
class TestValidation(TestCase):
    def setUp(self):
        super().setUp()
        self.model = FitModel(self, fit_function=fit_functions.InvCos)

        # perform a fit
        points = np.linspace(0, 100*us, 100, dtype=np.float64)
        means = np.full(100, fill_value=0, dtype=np.float64)
        for i_point, point in enumerate(points):
            m = 0
            for i_repeat in range(100):
                m += self.model.simulate(point,
                                         noise_level=0,
                                         simulation_args={
                                              'amplitude': 5,
                                              'pi_time': 10*us,
                                              'phase': 0,
                                              'y_min': 3
                                          })
            means[i_point] = m/100.0

        self.model.fit_data(points, means,
                            fit_function=fit_functions.InvCos,
                            hold={},
                            guess={
                                'amplitude': 5,
                                'pi_time': 10 * us,
                                'phase': 0,
                                'y_min': 3
                            }
        )

    def run_validation(self, validators):
        try:
            valid = True
            self.model.validate(validators=validators)
        except BadFit:
            valid = False
        return valid

    def test_validators(self):
        # between validation
        self.assertEqual(self.run_validation({
            "params.pi_time": {
                'between': [0 * us, 1 * us],
            },
        }), False)
        self.assertEqual(self.run_validation({
            "params.pi_time": {
                'between': [0 * us, 100 * us],
            },
        }), True)

        # reg_err
        self.assertEqual(self.run_validation({
            "analysis.reg_err": {
                "less_than": 0.00001
            },
        }), False, "invalid reg_err")
        self.assertEqual(self.run_validation({
            "analysis.reg_err": {
                "less_than": 10
            },
        }), True, "valid reg_err")


if __name__ == '__main__':
    unittest.main()
