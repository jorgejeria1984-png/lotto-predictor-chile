"""Standalone dashboard data and explicitly reviewed local writes."""
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from advanced import replay, bias_report, load_history
from laboratory import laboratory, simulate
from engine import PROFILES
from fetch_history import download, parse
from history import DATA, audit, read_records, merge_records, save_atomic
from prospective import connect, freeze, settle, report

ROOT=Path(__file__).resolve().parent

class Dashboard:
    def __init__(self,data=DATA,staging=ROOT/'staging',database=ROOT/'prospective.sqlite'):
        self.data=Path(data)
        self.staging=Path(staging)
        self.database=Path(database)
        self.cache={}

    def records(self,game):
        if game not in PROFILES:
            raise ValueError('Juego inválido')
        return read_records(self.data/f'{game}.csv',game)

    def analysis(self,game,lstm=False,refresh=False):
        records=self.records(game)
        info=audit(records,game)
        n=info['bloque_reciente_contiguo']
        if n<80:
            raise ValueError(f'Solo {n} sorteos consecutivos; se requieren 80.')
        h=[records[k][0] for k in sorted(records)[-n:]]
        p=PROFILES[game]
        key=(game,lstm,self._hash(self.data/f'{game}.csv'))
        if refresh or key not in self.cache:
            result=replay(h,p,lstm=lstm,simulations=100000,details=True)
            result.update({'diagnostico_sesgo':bias_report(h,p),'registros':n,'fecha_ultimo':str(h[-1].date),'auditoria':info,
                           'pool':p.pool,'pick':p.pick,'lstm_disponible':importlib.util.find_spec('torch') is not None})
            counts=Counter(x for d in h for x in d.numbers)
            recent=Counter(x for d in h[-25:] for x in d.numbers)
            result['frecuencias']=[{'numero':x,'historica':counts[x],'reciente':recent[x],
                                    'tasa':counts[x]/n,'tasa25':recent[x]/min(25,n)} for x in range(1,p.pool+1)]
            result['laboratorio']=laboratory(h,p,result,columns=5)
            self.cache={k:v for k,v in self.cache.items() if k[0]!=game or k[2]==key[2]}
            self.cache[key]=result
        return self.cache[key]

    def simulate(self,game,weights):
        return simulate(load_history(game,self.data),PROFILES[game],weights)

    def history(self,game,offset=0,limit=25):
        records=self.records(game)
        if offset<0 or not 1<=limit<=100:
            raise ValueError('Paginación inválida')
        return {'audit':audit(records,game),'total':len(records),'rows':[self._row(*records[k]) for k in sorted(records,reverse=True)[offset:offset+limit]]}

    @staticmethod
    def _row(draw,url):
        return {'draw':draw.number,'date':str(draw.date),'numbers':sorted(draw.numbers),'source':url}

    @staticmethod
    def _hash(path):
        return sha256(path.read_bytes()).hexdigest()

    def stage(self,game):
        current=self.records(game)
        candidates=parse(download(),game)
        # Validate the entire merge before persisting anything; conflicts fail closed.
        combined=merge_records(current,candidates)
        audit(combined,game)
        path=self.staging/f'{game}.csv'
        new={k:v for k,v in candidates.items() if k not in current}
        save_atomic(path,new,game)
        return {'new_count':len(new),'rows':[self._row(*new[k]) for k in sorted(new,reverse=True)],
                'stage_hash':self._hash(path),'audit_after_merge':audit(combined,game)}

    def approve(self,game,stage_hash,reviewed):
        if reviewed is not True:
            raise ValueError('Debe cotejar todos los candidatos con el operador oficial.')
        existing=self.records(game)
        path=self.staging/f'{game}.csv'
        if not path.exists() or self._hash(path)!=stage_hash:
            raise ValueError('La descarga cambió. Vuelva a revisar los candidatos.')
        incoming=read_records(path,game)
        combined=merge_records(existing,incoming)
        info=audit(combined,game)
        if incoming:
            save_atomic(self.data/f'{game}.csv',combined,game)
        path.unlink()
        return info

    def ledger(self,game):
        if game not in PROFILES:
            raise ValueError('Juego inválido')
        if not self.database.exists():
            return {'game':game,'scored':0,'pending':0,'rows':[]}
        with closing(connect(self.database)) as db:
            summary=report(db,game)
            rows=db.execute('SELECT f.target,f.created,f.deadline,f.strategy,f.history_hash,f.payload,r.actual,r.matches FROM forecasts f LEFT JOIN results r USING(game,target) WHERE f.game=? ORDER BY f.target DESC',(game,)).fetchall()
            summary['rows']=[{'target':r[0],'created':r[1],'deadline':r[2],'strategy':r[3],'history_hash':r[4],
                              'numbers':json.loads(r[5])[r[3]],'actual':json.loads(r[6]) if r[6] else None,
                              'matches':json.loads(r[7])[r[3]] if r[7] else None} for r in rows]
            return summary

    def freeze(self,game,deadline,reviewed,lstm=False):
        if reviewed is not True:
            raise ValueError('Confirme el historial completo y hora oficial del próximo sorteo.')
        h=load_history(game,self.data)
        with closing(connect(self.database)) as db:
            result=freeze(db,game,h,datetime.fromisoformat(deadline),lstm=lstm)
        return result

    def settle(self,game,reviewed):
        if reviewed is not True:
            raise ValueError('Confirme el resultado oficial antes de evaluar.')
        h=load_history(game,self.data)
        with closing(connect(self.database)) as db:
            return {'scored':settle(db,game,h)}
