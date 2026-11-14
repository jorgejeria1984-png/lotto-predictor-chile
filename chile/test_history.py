import tempfile
import unittest
from datetime import date
from pathlib import Path
from engine import Draw
from history import audit, merge_records, read_records, save_atomic

URL = 'https://example.org/results'

class HistoryTests(unittest.TestCase):
    def entry(self, n, day, nums=range(1, 7)):
        return (Draw(n, date(2026, 1, day), frozenset(nums)), URL)

    def test_gap(self):
        records = {5400: self.entry(5400, 1), 5402: self.entry(5402, 3), 5403: self.entry(5403, 5)}
        result = audit(records, 'loto')
        self.assertEqual(result['intervalos_faltantes'], [[5401, 5401]])
        self.assertEqual(result['bloque_reciente_contiguo'], 2)
        self.assertFalse(result['listo_para_backtest'])

    def test_merge_conflict(self):
        old = {5400: self.entry(5400, 1)}
        self.assertEqual(merge_records(old, old), old)
        with self.assertRaises(ValueError):
            merge_records(old, {5400: self.entry(5400, 1, range(2, 8))})

    def test_round_trip_and_era(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'loto.csv'
            rows = {5400: self.entry(5400, 1)}
            save_atomic(file, rows, 'loto')
            self.assertEqual(read_records(file, 'loto'), rows)
            file.write_text(file.read_text().replace('5400', '2934'))
            with self.assertRaises(ValueError):
                read_records(file, 'loto')

    def test_dates(self):
        with self.assertRaises(ValueError):
            audit({5400: self.entry(5400, 3), 5401: self.entry(5401, 1)}, 'loto')

if __name__ == '__main__':
    unittest.main()
