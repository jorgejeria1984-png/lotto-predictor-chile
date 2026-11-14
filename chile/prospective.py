"""Immutable-by-application prospective registry. Local timestamps alone are not proof."""
import argparse
from datetime import datetime, date, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from advanced import load_history, replay, VERSION
from engine import PROFILES
from history import DATA
from uncertainty import compare_mean

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def digest(history):
    return hashlib.sha256(canonical([[d.number,str(d.date),sorted(d.numbers)] for d in history]).encode()).hexdigest()

def connect(path):
    db=sqlite3.connect(path)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS forecasts (
       game TEXT NOT NULL, target INTEGER NOT NULL, created TEXT NOT NULL,
       deadline TEXT NOT NULL, cutoff INTEGER NOT NULL, history_start INTEGER NOT NULL, history_hash TEXT NOT NULL,
       strategy TEXT NOT NULL, version TEXT NOT NULL, payload TEXT NOT NULL,
       PRIMARY KEY(game,target));
    CREATE TABLE IF NOT EXISTS results (
       game TEXT NOT NULL, target INTEGER NOT NULL, scored TEXT NOT NULL,
       actual TEXT NOT NULL, matches TEXT NOT NULL, PRIMARY KEY(game,target),
       FOREIGN KEY(game,target) REFERENCES forecasts(game,target));
    CREATE TRIGGER IF NOT EXISTS forecasts_no_update BEFORE UPDATE ON forecasts BEGIN SELECT RAISE(ABORT,'frozen forecast'); END;
    CREATE TRIGGER IF NOT EXISTS forecasts_no_delete BEFORE DELETE ON forecasts BEGIN SELECT RAISE(ABORT,'frozen forecast'); END;
    CREATE TRIGGER IF NOT EXISTS results_no_update BEFORE UPDATE ON results BEGIN SELECT RAISE(ABORT,'frozen result'); END;
    CREATE TRIGGER IF NOT EXISTS results_no_delete BEFORE DELETE ON results BEGIN SELECT RAISE(ABORT,'frozen result'); END;
    """)
    db.execute('PRAGMA foreign_keys=ON')
    return db

def freeze(db,game,history,deadline,now=None,lstm=False):
    clock=now
    now=clock or datetime.now(timezone.utc)
    if not history:
        raise ValueError('Empty history')
    if deadline.tzinfo is None or now.tzinfo is None or deadline<=now:
        raise ValueError('Deadline must be a verified future draw time with UTC offset')
    if deadline.date()<=history[-1].date:
        raise ValueError('Deadline must follow cutoff draw date')
    target=history[-1].number+1
    if db.execute('SELECT 1 FROM forecasts WHERE game=? AND target=?',(game,target)).fetchone():
        raise ValueError('Forecast already frozen')
    # Recalculate only from the supplied contiguous prefix.
    report=replay(history,PROFILES[game],lstm=lstm,simulations=1000)
    created=clock or datetime.now(timezone.utc)
    if created>=deadline:
        raise ValueError('Analysis finished after deadline; forecast not recorded')
    row=(game,target,created.astimezone(timezone.utc).isoformat(),deadline.isoformat(),history[-1].number,history[0].number,digest(history),report['estrategia'],VERSION,canonical(report['lineas']))
    with db:
        db.execute('INSERT INTO forecasts VALUES (?,?,?,?,?,?,?,?,?,?)',row)
    return {'game':game,'target':target,'created':row[2],'cutoff_hash':row[6],'strategy':row[7],
            'version':row[8],'lines':report['lineas'],'deadline':row[3]}

def settle(db,game,history,now=None):
    now=now or datetime.now(timezone.utc)
    actuals={d.number:d for d in history}
    pending=db.execute('SELECT target,deadline,cutoff,history_start,history_hash,payload FROM forecasts WHERE game=? AND target NOT IN (SELECT target FROM results WHERE game=?) ORDER BY target',(game,game)).fetchall()
    scored=[]
    with db:
        for target,deadline,cutoff,start,hash_value,payload in pending:
            if target not in actuals or now<datetime.fromisoformat(deadline):
                continue
            # Archive expansion before cutoff is permitted only if the original prefix is
            # retained as a suffix; digest matches the exact previously frozen sample.
            prefix=[d for d in history if start<=d.number<=cutoff]
            if digest(prefix)!=hash_value:
                raise ValueError(f'Frozen history changed for draw {target}')
            actual=actuals[target]
            if actual.date!=datetime.fromisoformat(deadline).date():
                raise ValueError(f'Draw {target} date differs from frozen deadline')
            lines=json.loads(payload)
            matches={name:len(set(line)&actual.numbers) for name,line in lines.items()}
            db.execute('INSERT INTO results VALUES (?,?,?,?,?)',(game,target,now.astimezone(timezone.utc).isoformat(),canonical(sorted(actual.numbers)),canonical(matches)))
            scored.append({'target':target,'matches':matches})
    return scored

def report(db,game):
    rows=db.execute('SELECT f.strategy,r.matches FROM forecasts f JOIN results r USING(game,target) WHERE f.game=? ORDER BY f.target',(game,)).fetchall()
    result={'game':game,'scored':len(rows),'pending':db.execute('SELECT COUNT(*) FROM forecasts f WHERE game=? AND NOT EXISTS (SELECT 1 FROM results r WHERE r.game=f.game AND r.target=f.target)',(game,)).fetchone()[0]}
    if rows:
        total=sum(json.loads(matches)[strategy] for strategy,matches in rows)
        result['champion_total']=total
        result['champion_mean']=total/len(rows)
        # Diagnostic, not a sequential stopping rule or an independent promotion test.
        result['diagnostic']=compare_mean(PROFILES[game],len(rows),total,10000)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','settle','report'])
    parser.add_argument('--game',required=True,choices=PROFILES)
    parser.add_argument('--db',type=Path,default=Path(__file__).resolve().parent/'prospective.sqlite')
    parser.add_argument('--data-dir',type=Path,default=DATA)
    parser.add_argument('--deadline',help='Official next draw time, ISO 8601 with offset')
    parser.add_argument('--lstm',action='store_true')
    parser.add_argument('--reviewed',action='store_true',help='Confirm history and draw time independently checked')
    args=parser.parse_args()
    with connect(args.db) as db:
        if args.action=='report':
            out=report(db,args.game)
        else:
            if not args.reviewed:
                parser.error('Check results against official source and pass --reviewed')
            h=load_history(args.game,args.data_dir)
            if args.action=='freeze':
                if not args.deadline:
                    parser.error('freeze requires --deadline')
                out=freeze(db,args.game,h,datetime.fromisoformat(args.deadline),lstm=args.lstm)
            else:
                out=settle(db,args.game,h)
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
