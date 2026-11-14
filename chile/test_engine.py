import unittest, random, io
from datetime import date,timedelta
from math import comb
from engine import *

class EngineTests(unittest.TestCase):
    def test_profiles_and_chance(self):
        for p in PROFILES.values():
            self.assertAlmostEqual(chance_tail(p,p.pick),1/comb(p.pool,p.pick))
            self.assertAlmostEqual(chance_tail(p,0),1)
    def test_models(self):
        for p in PROFILES.values():
            rng=random.Random(8)
            draws=[Draw(i+1,date(2025,1,1)+timedelta(days=i),frozenset(rng.sample(range(1,p.pool+1),p.pick))) for i in range(85)]
            a=analyze(draws,p); b=analyze(draws,p)
            self.assertEqual(a,b); self.assertEqual(len(a['combinacion']),p.pick)
            self.assertTrue(all(1<=x<=p.pool for x in a['combinacion']))
            self.assertEqual(a['validacion']['azar']['sorteos'],12)
            self.assertTrue(0<=a['p_valor_unilateral_objetivo']<=1)
            changed=draws[:73]+[Draw(d.number,d.date,frozenset(range(1,p.pick+1))) for d in draws[73:]]
            self.assertEqual(a['estrategia'],analyze(changed,p)['estrategia'])
    def test_csv(self):
        p=PROFILES['loto']; header='draw,date,n1,n2,n3,n4,n5,n6\n'
        good=header+'2,2025-01-02,1,2,3,4,5,6\n1,2025-01-01,3,4,5,6,7,8\n'
        self.assertEqual([d.number for d in load_csv(io.StringIO(good),p)],[1,2])
        for row in ('1,2025-01-01,1,1,2,3,4,5\n','1,2025-01-01,1,2,3,4,5,42\n'):
            with self.assertRaises(ValueError):load_csv(io.StringIO(header+row),p)
    def test_small_history(self):
        with self.assertRaises(ValueError):analyze([],PROFILES['kino'])
    def test_binomial(self):
        self.assertAlmostEqual(binomial_tail(3,2,.5),.5)
if __name__=='__main__':unittest.main()
