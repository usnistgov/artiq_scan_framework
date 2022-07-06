# tests models/model.py
from ..test_case import *
from ...models.model import *


# tests the built in validation rules in model.py
class TestValidationRules(TestCase):
    def setUp(self):
        super().setUp()
        self.model = Model(self)

    def test_validate_between(self):
        self.assertEqual(self.model.validate_between('', 5, min_=0, max_=10), True)
        self.assertEqual(self.model.validate_between('', 0, min_=0, max_=10), True)
        self.assertEqual(self.model.validate_between('', 10, min_=0, max_=10), True)
        self.assertEqual(self.model.validate_between('', 100, min_=0, max_=10), False)
        self.assertEqual(self.model.validate_between('', -100, min_=0, max_=10), False)

    def test_validate_less_than(self):
        self.assertEqual(self.model.validate_less_than('', 0, max_=10), True)
        self.assertEqual(self.model.validate_less_than('', 10, max_=10), False)

    def test_validate_greater_than(self):
        self.assertEqual(self.model.validate_greater_than('', 10, 10), False)
        self.assertEqual(self.model.validate_greater_than('', 11, 10), True)

    def test_validate_max_change(self):
        self.assertEqual(self.model.validate_max_change('', 1, 1, 0), True)
        self.assertEqual(self.model.validate_max_change('', 1, 0, 0), False)

    def test_validate_height(self):
        self.assertEqual(self.model.validate_height('', np.array([0, 1, 2]), 0), True)
        self.assertEqual(self.model.validate_height('', np.array([0, 1, 2]), 2), True)
        self.assertEqual(self.model.validate_height('', np.array([0, 1, 2]), 3), False)


if __name__ == '__main__':
    unittest.main()
