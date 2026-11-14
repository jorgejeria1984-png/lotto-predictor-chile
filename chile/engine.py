"""Experimental lottery analysis; no claim of predictive advantage."""
from dataclasses import dataclass
from datetime import date
from collections import Counter
from itertools import combinations
from math import comb, exp, log, sqrt, fsum
import csv
import random

@dataclass(frozen=True)
class Profile:
    pool: int
    pick: int
    target: int

PROFILES = {'loto': Profile(41, 6, 3), 'kino': Profile(25, 14, 10)}
@dataclass(frozen=True)
class Draw:
    number: int
    date: date
    numbers: frozenset

def load_csv(source, profile):
    """CSV with draw,date,n1,...,nK; date ISO 8601; main game only."""
    reader = csv.DictReader(source)
    required = {'draw', 'date', *(f'n{i}' for i in range(1,profile.pick+1))}
    if not required <= set(reader.fieldnames or []):
        raise ValueError('Columnas requeridas: '+', '.join(sorted(required)))
    draws = []
    seen = set()
    for row in reader:
        try:
            number = int(row['draw']); day = date.fromisoformat(row['date'])
            nums = frozenset(int(row[f'n{i}']) for i in range(1,profile.pick+1))
            if number <= 0 or number in seen or len(nums)!=profile.pick or not all(1<=n<=profile.pool for n in nums):
                raise ValueError('sorteo duplicado o números inválidos')
        except (ValueError, TypeError) as exc:
            raise ValueError(f'Fila {reader.line_num}: {exc}') from exc
        seen.add(number); draws.append(Draw(number,day,nums))
    draws.sort(key=lambda d:d.number)
    if any(a.date>b.date for a,b in zip(draws,draws[1:])):
        raise ValueError('Los identificadores y fechas no siguen el mismo orden')
    return draws

def zscore(values):
    mean=fsum(values)/len(values); sd=sqrt(fsum((v-mean)**2 for v in values)/len(values))
    return [(v-mean)/sd if sd>1e-12 else 0.0 for v in values]

STRATEGIES = ('historica','reciente_10','reciente_25','reciente_50','reciente_100','exponencial','rezago','momentum','bayes','hibrida','pares')

def features(history,p):
    balls=range(1,p.pool+1); n=len(history); prior=p.pick/p.pool
    counts=Counter(x for d in history for x in d.numbers)
    recent={w:Counter(x for d in history[-w:] for x in d.numbers) for w in (10,25,50,100)}
    weights=[2**(-i/10) for i in range(n)]
    decayed=Counter(); last={}
    for i,d in enumerate(reversed(history)):
        for x in d.numbers:
            decayed[x]+=weights[i]; last.setdefault(x,i)
    total=fsum(weights)
    long=[counts[x]/n for x in balls]
    window={w:[recent[w][x]/min(n,w) for x in balls] for w in recent}
    out={'historica':zscore(long),'exponencial':zscore([decayed[x]/total for x in balls]),
         'rezago':zscore([last.get(x,n) for x in balls]),
         'momentum':zscore([r-l for r,l in zip(window[25],long)]),
         'bayes':zscore([(counts[x]+20*prior)/(n+20) for x in balls])}
    out.update({f'reciente_{w}':zscore(v) for w,v in window.items()})
    out['hibrida']=[.25*a+.20*b+.20*c+.20*d+.15*e for a,b,c,d,e in zip(out['historica'],out['reciente_10'],out['reciente_25'],out['exponencial'],out['momentum'])]
    return out

def rank(scores,p):
    return frozenset(sorted(range(1,p.pool+1),key=lambda x:(-scores[x-1],x))[:p.pick])

def predictions(history,p):
    f=features(history,p); result={name:rank(score,p) for name,score in f.items()}
    # Greedy pair-residual selection: compare observed pair counts with expected from marginal frequencies.
    # Use only past draws and regularize; no exclusions or claims of improved odds.
    h=history[-100:]; n=len(h)
    counts=Counter(x for d in h for x in d.numbers)
    pairs=Counter(pair for d in h for pair in combinations(sorted(d.numbers),2))
    def residual(x,y):
        expected=counts[x]*counts[y]/n * (p.pick-1)*p.pool/(p.pick*(p.pool-1))
        return (pairs[tuple(sorted((x,y)))]-expected)/sqrt(expected+5)
    chosen=[]
    while len(chosen)<p.pick:
        def score(x):
            return f['hibrida'][x-1]+(.25*fsum(residual(x,y) for y in chosen)/len(chosen) if chosen else 0)
        chosen.append(max((x for x in range(1,p.pool+1) if x not in chosen),key=lambda x:(score(x),-x)))
    result['pares']=frozenset(chosen)
    return result

def chance_tail(p,threshold):
    return sum(comb(p.pick,k)*comb(p.pool-p.pick,p.pick-k) for k in range(max(threshold,2*p.pick-p.pool,0),p.pick+1))/comb(p.pool,p.pick)

def binomial_tail(n,k,p):
    if k<=0:return 1.0
    if k>n or p==0:return 0.0
    if p==1:return 1.0
    from math import lgamma,log1p
    logs=[lgamma(n+1)-lgamma(j+1)-lgamma(n-j+1)+j*log(p)+(n-j)*log1p(-p) for j in range(k,n+1)]
    m=max(logs); return min(1.0,exp(m)*fsum(exp(v-m) for v in logs))

def analyze(draws,p,warmup=50,seed=42):
    if warmup<10 or len(draws)<warmup+30:
        raise ValueError(f'Se requieren al menos {max(10,warmup)+30} sorteos válidos para entrenamiento y evaluación.')
    rng=random.Random(seed); records={s:[] for s in (*STRATEGIES,'azar')}
    for i in range(warmup,len(draws)):
        pred=predictions(draws[:i],p)
        pred['azar']=frozenset(rng.sample(range(1,p.pool+1),p.pick))
        for name,nums in pred.items(): records[name].append(len(nums & draws[i].numbers))
    split=2*(len(draws)-warmup)//3
    # Choose on early segment, never on the later holdout. Objective: average matches.
    winner=max(STRATEGIES,key=lambda s:(sum(records[s][:split]),s))
    def summarize(values):
        n=len(values); hits=sum(v>=p.target for v in values)
        return {'sorteos':n,'media':sum(values)/n,'objetivo_aciertos':hits,'tasa_objetivo':hits/n}
    train={s:summarize(v[:split]) for s,v in records.items()}
    test={s:summarize(v[split:]) for s,v in records.items()}
    selected=test[winner]; probability=chance_tail(p,p.target)
    pvalue=binomial_tail(selected['sorteos'],selected['objetivo_aciertos'],probability)
    return {'estrategia':winner,'combinacion':sorted(predictions(draws,p)[winner]),'ultimo_sorteo':draws[-1].number,
            'ultima_fecha':str(draws[-1].date),'entrenamiento':train,'validacion':test,
            'azar_media_teorica':p.pick**2/p.pool,'azar_tasa_objetivo':probability,
            'objetivo':p.target,'p_valor_unilateral_objetivo':pvalue,'combinaciones_posibles':comb(p.pool,p.pick),
            'advertencia':'Frecuencias descriptivas. Un sorteo justo da igual probabilidad a todas las combinaciones.'}
