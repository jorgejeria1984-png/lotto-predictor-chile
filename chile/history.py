"""Audita y amplía los CSV locales con trazabilidad; nunca inventa sorteos."""
import argparse
import csv
import io
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from engine import PROFILES, load_csv, analyze

DATA = Path(__file__).resolve().parent / 'data'


def read_records(path, game, source=None):
    p = PROFILES[game]
    text = Path(path).read_text(encoding='utf-8-sig')
    draws = load_csv(io.StringIO(text), p)
    rows = {int(row['draw']): row for row in csv.DictReader(io.StringIO(text))}
    result = {}
    for draw in draws:
        if game == 'loto' and draw.number < 2935:
            raise ValueError(f'Loto {draw.number}: fuera de la era 6/41')
        if game == 'kino' and draw.number < 799:
            raise ValueError(f'Kino {draw.number}: fuera de la era 14/25')
        url = (rows[draw.number].get('source_url') or source or '').strip()
        parsed = urlsplit(url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname:
            raise ValueError(f'Sorteo {draw.number}: falta URL de procedencia válida')
        result[draw.number] = (draw, url)
    return result


def audit(records, game):
    draws = [records[k][0] for k in sorted(records)]
    if any(a.date >= b.date for a, b in zip(draws, draws[1:])):
        raise ValueError('Las fechas deben avanzar estrictamente según el número de sorteo')
    gaps = [[a.number + 1, b.number - 1] for a, b in zip(draws, draws[1:]) if b.number > a.number + 1]
    suffix = len(draws)
    if gaps:
        suffix = draws[-1].number - gaps[-1][1]
    return {'juego': game, 'registros': len(draws),
            'primero': draws[0].number if draws else None,
            'ultimo': draws[-1].number if draws else None,
            'fecha_ultimo': str(draws[-1].date) if draws else None,
            'intervalos_faltantes': gaps, 'bloque_reciente_contiguo': suffix,
            'minimo_para_backtest': 80, 'listo_para_backtest': suffix >= 80}


def merge_records(existing, incoming):
    result = dict(existing)
    for key, record in incoming.items():
        if key in result and result[key][0] != record[0]:
            raise ValueError(f'Conflicto en sorteo {key}; verifique ambas fuentes antes de modificarlo')
        result.setdefault(key, record)
    return result


def save_atomic(path, records, game):
    audit(records, game)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='', dir=path.parent, delete=False) as file:
            tmp = Path(file.name)
            writer = csv.writer(file, lineterminator='\n')
            writer.writerow(['draw', 'date', *(f'n{i}' for i in range(1, PROFILES[game].pick + 1)), 'source_url'])
            for key in sorted(records):
                draw, url = records[key]
                writer.writerow([draw.number, draw.date, *sorted(draw.numbers), url])
        os.replace(tmp, path)
    finally:
        if tmp and tmp.exists():
            tmp.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['audit', 'merge', 'analyze'])
    parser.add_argument('--game', required=True, choices=PROFILES)
    parser.add_argument('--file', type=Path, help='CSV entrante para merge')
    parser.add_argument('--source', help='URL de procedencia para filas que no traen source_url')
    parser.add_argument('--data-dir', type=Path, default=DATA)
    args = parser.parse_args()
    path = args.data_dir / f'{args.game}.csv'
    records = read_records(path, args.game) if path.exists() else {}
    try:
        if args.action == 'merge':
            if not args.file:
                parser.error('merge requiere --file')
            records = merge_records(records, read_records(args.file, args.game, args.source))
            save_atomic(path, records, args.game)
        report = audit(records, args.game)
        if args.action == 'analyze':
            if not report['listo_para_backtest']:
                raise ValueError(f"Solo {report['bloque_reciente_contiguo']} sorteos consecutivos; se requieren 80")
            block = sorted(records)[-report['bloque_reciente_contiguo']:]
            report['analisis'] = analyze([records[k][0] for k in block], PROFILES[args.game])
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except ValueError as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
