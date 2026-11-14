import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from threading import Thread
from http.client import HTTPConnection
from http.server import HTTPServer
from datetime import timedelta
from app import Handler,TOKEN
from dashboard import Dashboard
from engine import Draw
from history import DATA

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        shutil.copytree(DATA,self.root/'data')
        self.d=Dashboard(self.root/'data',self.root/'staging',self.root/'registry.sqlite')
    def tearDown(self):
        self.tmp.cleanup()
    def test_analysis_and_pagination(self):
        for game,pick,pool in [('loto',6,41),('kino',14,25)]:
            report=self.d.analysis(game)
            self.assertEqual(len(report['lineas'][report['estrategia']]),pick)
            self.assertEqual(len(report['frecuencias']),pool)
            self.assertEqual(sum(x['historica'] for x in report['frecuencias']),pick*report['registros'])
            self.assertEqual(report['contraste_media']['simulations'],100000)
            self.assertIs(report,self.d.analysis(game))
            self.assertEqual(len(self.d.history(game,25)['rows']),25)
        self.assertEqual(self.d.ledger('loto')['rows'],[])
    def test_reviewed_candidates_and_conflict(self):
        current=self.d.records('loto')
        last=current[max(current)][0]
        candidate=Draw(last.number+1,last.date+timedelta(days=1),last.numbers)
        with patch('dashboard.download',return_value='fixture'),patch('dashboard.parse',return_value={candidate.number:(candidate,'https://example.org/source')}):
            stage=self.d.stage('loto')
        self.assertEqual(stage['new_count'],1)
        self.assertEqual(len(self.d.records('loto')),len(current))
        with self.assertRaises(ValueError):self.d.approve('loto',stage['stage_hash'],False)
        with self.assertRaises(ValueError):self.d.approve('loto','incorrect',True)
        self.assertEqual(self.d.approve('loto',stage['stage_hash'],True)['registros'],len(current)+1)
        bad=Draw(last.number,last.date,frozenset(range(1,7)))
        with patch('dashboard.download',return_value='fixture'),patch('dashboard.parse',return_value={bad.number:(bad,'https://example.org/source')}):
            with self.assertRaises(ValueError):self.d.stage('loto')
    def test_http_and_security(self):
        d=self.d
        class TestHandler(Handler):
            dashboard=d
        server=HTTPServer(('127.0.0.1',0),TestHandler)
        t=Thread(target=server.serve_forever,daemon=True);t.start()
        client=HTTPConnection('127.0.0.1',server.server_port,timeout=30)
        try:
            client.request('GET','/')
            response=client.getresponse();self.assertEqual(response.status,200)
            self.assertIn(b'Lotto Predictor Chile',response.read())
            client.request('GET','/dashboard.js');response=client.getresponse()
            self.assertEqual(response.status,200);response.read()
            client.request('GET','/chile-api/history?game=kino')
            response=client.getresponse();self.assertEqual(response.status,200)
            self.assertGreaterEqual(json.loads(response.read())['total'],80)
            client.request('GET','/',headers={'Host':'evil.example'})
            response=client.getresponse();self.assertEqual(response.status,403);response.read()
            body=json.dumps({'game':'loto'})
            client.request('POST','/chile-api/stage',body=body,headers={'Content-Type':'application/json','Origin':'http://evil.example','X-Chile-Token':TOKEN})
            response=client.getresponse();self.assertEqual(response.status,403);response.read()
            origin=f'http://127.0.0.1:{server.server_port}'
            client.request('POST','/chile-api/settle',body=body,headers={'Content-Type':'application/json','Origin':origin,'X-Chile-Token':TOKEN})
            response=client.getresponse();self.assertEqual(response.status,400);response.read()
        finally:
            client.close();server.shutdown();server.server_close();t.join()

if __name__=='__main__':unittest.main()
