from django.test import TestCase
from shuttle.services.geo import haversine_m
from shuttle.services.occupancy import HIGH, LOW, MEDIUM, occupancy_level


class OccupancyLevelTests(TestCase):
    def test_thresholds(self):
        self.assertEqual(occupancy_level(5, 40), LOW)
        self.assertEqual(occupancy_level(20, 40), MEDIUM)
        self.assertEqual(occupancy_level(35, 40), HIGH)

    def test_hysteresis(self):
        self.assertEqual(occupancy_level(31, 40, previous=HIGH), HIGH)
        self.assertEqual(occupancy_level(30, 40, previous=HIGH), MEDIUM)


class GeoTests(TestCase):
    def test_haversine_reasonable(self):
        meters = haversine_m(26.306350, 50.147000, 26.307900, 50.151200)
        self.assertGreater(meters, 300)
        self.assertLess(meters, 600)
