import unittest
from engine import PROFILES
from uncertainty import compare_mean

class UncertaintyTests(unittest.TestCase):
    def test_exact_single_draw(self):
        from engine import chance_tail
        for p in PROFILES.values():
            a=compare_mean(p,1,p.target,1000)
            self.assertAlmostEqual(a['exact_p'],chance_tail(p,p.target))
    def test_all_minimum(self):
        p=PROFILES['kino'];a=compare_mean(p,2,6,1000)
        self.assertAlmostEqual(a['exact_p'],1.0)
        self.assertEqual(a['monte_carlo_p'],1.0)
    def test_reproducible(self):
        p=PROFILES['loto'];self.assertEqual(compare_mean(p,5,5,1000),compare_mean(p,5,5,1000))
    def test_invalid(self):
        with self.assertRaises(ValueError):compare_mean(PROFILES['kino'],2,0,100)
