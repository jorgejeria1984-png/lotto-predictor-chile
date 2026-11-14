import importlib.util
import random
import sqlite3
import unittest
from datetime import date, datetime, timedelta, timezone
from engine import Draw, PROFILES
from advanced import replay, bias_report, LstmChallenger, matrix, OnlineLogit
from prospective import connect, freeze, settle, report
from fetch_history import parse

def sample(p,n=85):
    rng=random.Random(12)
    return [Draw(5400+i,date(2025,1,1)+timedelta(days=i),frozenset(rng.sample(range(1,p.pool+1),p.pick))) for i in range(n)]

class AdvancedTests(unittest.TestCase):
    def test_causal_selection(self):
        for game,p in PROFILES.items():
            h=sample(p)
            a=replay(h,p,simulations=200)
            split=50+2*(len(h)-50)//3
            changed=h[:split]+[Draw(d.number,d.date,frozenset(range(1,p.pick+1))) for d in h[split:]]
            b=replay(changed,p,simulations=200)
            self.assertEqual(a['estrategia'],b['estrategia'])
            self.assertEqual(a['seleccion'],b['seleccion'])
            for line in a['lineas'].values():
                self.assertEqual(len(set(line)),p.pick)
                self.assertTrue(all(1<=x<=p.pool for x in line))
            self.assertEqual(len(bias_report(h,p)),p.pool)

    def test_logit_update(self):
        p=PROFILES['loto']; h=sample(p,11); m=OnlineLogit(p); x=matrix(h[:10],p)
        m.update(x,h[10].numbers)
        self.assertNotEqual(m.weights,[0.0]*len(m.weights))

    def test_freeze_and_settle(self):
        p=PROFILES['loto']; h=sample(p); db=connect(':memory:')
        deadline=datetime.combine(h[-1].date+timedelta(days=1),datetime.min.time(),timezone.utc)
        before=deadline-timedelta(hours=1)
        frozen=freeze(db,'loto',h,deadline,now=before)
        self.assertEqual(frozen['target'],h[-1].number+1)
        with self.assertRaises(ValueError): freeze(db,'loto',h,deadline,now=before)
        with self.assertRaises(sqlite3.DatabaseError): db.execute('UPDATE forecasts SET strategy="wrong"')
        db.rollback()
        actual=Draw(frozen['target'],deadline.date(),frozenset(range(1,7)))
        self.assertEqual(settle(db,'loto',h+[actual],now=before),[])
        modified=[Draw(h[0].number,h[0].date,frozenset(range(1,7)))]+h[1:]+[actual]
        with self.assertRaises(ValueError): settle(db,'loto',modified,now=deadline)
        self.assertEqual(len(settle(db,'loto',h+[actual],now=deadline)),1)
        self.assertEqual(settle(db,'loto',h+[actual],now=deadline),[])
        self.assertEqual(report(db,'loto')['scored'],1)
        db.close()

    def test_source_strict(self):
        text='<table><tr><th>Sorteo</th><th>Fecha Captura</th><th>Matriz Numérica (41 n)</th></tr><tr><td>#5503</td><td>2026-11-12</td><td>7 8 17 25 35 36 9</td></tr></table>'
        result=parse(text,'loto')
        self.assertEqual(result[5503][0].numbers,frozenset([7,8,17,25,35,36]))
        with self.assertRaises(ValueError):parse(text.replace('36 9','36 36'),'loto')
        with self.assertRaises(ValueError):parse(text,'kino')

    @unittest.skipUnless(importlib.util.find_spec('torch'),'optional CPU PyTorch')
    def test_lstm(self):
        p=PROFILES['kino']; h=sample(p,11); m=LstmChallenger(p)
        self.assertEqual(len(m.predict(h[:10])),p.pick)
        m.update(h[:10],h[10].numbers)
        self.assertEqual(len(m.predict(h)),p.pick)

if __name__=='__main__':
    unittest.main()
