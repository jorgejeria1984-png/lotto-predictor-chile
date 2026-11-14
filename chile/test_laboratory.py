import random
import unittest
from datetime import date,timedelta
from engine import Draw,PROFILES
from advanced import replay
from laboratory import laboratory,simulate,SIM_FEATURES

class LaboratoryTests(unittest.TestCase):
    def test_both_games(self):
        for p in PROFILES.values():
            rng=random.Random(42)
            h=[Draw(i+3400,date(2025,1,1)+timedelta(days=i),frozenset(rng.sample(range(1,p.pool+1),p.pick))) for i in range(82)]
            r=replay(h,p,simulations=100,details=True)
            self.assertIn('hedge_online',r['series'])
            self.assertAlmostEqual(sum(r['hedge_weights'].values()),1)
            l=laboratory(h,p,r)
            self.assertEqual(len(l['correlation']),p.pool)
            self.assertAlmostEqual(sum(l['theory']),1)
            for d in l['distributions'].values():
                self.assertEqual(sum(d['counts']),len(l['draws']))
            self.assertAlmostEqual(l['correlation'][0][1],l['correlation'][1][0],places=12)
            sim=simulate(h,p,{key:1 for key in SIM_FEATURES})
            self.assertEqual(sum(sim['histogram']),32)
            with self.assertRaises(ValueError):simulate(h,p,{key:0 for key in SIM_FEATURES})
