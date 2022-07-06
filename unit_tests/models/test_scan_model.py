from ...models.scan_model import *
from ...scans.scan import Scan
from ...analysis.curvefits import Sine
from ..test_case import *
import math
import numpy as np


class TestScanModel(TestCase):
    def setUp(self):
        super().setUp()
        self.scan = Scan(self, nrepeats=3, nbins=50, npasses=1, npoints=100)
        self.scan._dim = 1

        self.model = ScanModel(self,
                               namespace='unit_tests',
                               broadcast=True,
                               persist=True,
                               fit_function=Sine)
        self.model.enable_histograms = False
        self.model.attach(self.scan)

    def test_init_datasets(self):
        self.model.init_datasets(shape=100, plot_shape=100, points=np.linspace(0, 1, 100), dimension=0)
        mean = self.model.get('stats.mean')
        points = self.model.get('stats.points')

        # tests
        self.assertEqual(points[0], 0)
        self.assertEqual(points[-1], 1.0)
        self.assertTrue(math.isnan(mean[0]))
        self.assertTrue(math.isnan(mean[-1]))

    def test_mutate_all(self):
        self.model.init_datasets(shape=100, plot_shape=100, points=np.linspace(0, 1, 100), dimension=0)
        self.model.mutate_datasets(i_point=0, point=1, counts=[2, 3, 4])
        self.model.mutate_datasets(i_point=1, point=2, counts=[3, 4, 5])
        mean = self.model.get('stats.mean')
        points = self.model.get('stats.points')

        # tests
        self.assertEqual(points[0], 1)
        self.assertEqual(mean[0], 3)
        self.assertEqual(points[1], 2)
        self.assertEqual(mean[1], 4)

    def test_fit(self):
        self.model.init_datasets(shape=100, plot_shape=100, points=np.linspace(0, 1, 100), dimension=0)

        for i in range(50):
            self.model.mutate_datasets(i_point=i, point=i, counts=[math.sin(i * (2 * math.pi / 50))] * 3)
        self.model.fit_use_yerr = False
        self.model.fit_data(x_data=self.model.stat_model.get('points'),
                            y_data=self.model.stat_model.get('mean'),
                            errors=self.model.stat_model.get('error'),
                            fit_function=Sine)
        self.model.set_fits()

        # tests
        f = self.model.get('fits.params.f')
        self.assertEqual(round(f, 5), 1 / 50)


if __name__ == '__main__':
    unittest.main()