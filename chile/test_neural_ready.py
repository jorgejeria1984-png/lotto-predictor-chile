import importlib.util
import sys
import unittest
from unittest.mock import patch
from app import neural_status
from dashboard import Dashboard

class NeuralReadyTests(unittest.TestCase):
    def tearDown(self):
        neural_status.cache_clear()

    def test_missing_dependency(self):
        neural_status.cache_clear()
        with patch.dict(sys.modules,{'torch':None}):
            self.assertFalse(neural_status()['available'])

    def test_portable_without_torch(self):
        neural_status.cache_clear()
        with patch.object(sys,'frozen',True,create=True):
            self.assertFalse(neural_status()['available'])

    @unittest.skipUnless(importlib.util.find_spec('torch'),'optional CPU PyTorch')
    def test_cpu_and_both_games(self):
        neural_status.cache_clear()
        capability=neural_status()
        self.assertTrue(capability['available'],capability['message'])
        self.assertTrue(capability['version'])
        for game,pick in [('loto',6),('kino',14)]:
            result=Dashboard().analysis(game,lstm=True)
            self.assertIn('lstm_online',result['seleccion'])
            self.assertIn('lstm_online',result['validacion_exploratoria'])
            self.assertEqual(len(set(result['lineas']['lstm_online'])),pick)
            self.assertIn('lstm_online',result['laboratorio']['distributions'])
