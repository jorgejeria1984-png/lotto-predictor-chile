"""Descriptive diagnostics. No diagnostic is evidence of a winning strategy."""
import math
from collections import Counter
from itertools import combinations
from engine import features,rank
from advanced import replay

def laboratory(draws,p,result,columns=5):
    n=len(draws)
    if not 2<=columns<=15:raise ValueError('Columnas entre 2 y 15')
    counts=Counter(x for d in draws for x in d.numbers)
    pairs=Counter(pair for d in draws for pair in combinations(sorted(d.numbers),2))
    expected_pair=p.pick*(p.pick-1)/(p.pool*(p.pool-1))
    correlation=[]
    for a in range(1,p.pool+1):
        row=[]
        for b in range(1,p.pool+1):
            pa,pb=counts[a]/n,counts[b]/n
            denom=math.sqrt(pa*(1-pa)*pb*(1-pb))
            joint=pairs[tuple(sorted((a,b)))]/n
            row.append(1.0 if a==b and denom else ((joint-pa*pb)/denom if a!=b and denom else None))
        correlation.append(row)
    def shape(d):
        ns=sorted(d.numbers);coords=[divmod(x-1,columns) for x in ns]
        edges=sum(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in combinations(coords,2))
        return {'sum':sum(ns),'odd':sum(x%2 for x in ns),'adjacent':edges,'rows':len({r for r,c in coords}),'columns':len({c for r,c in coords})}
    shapes=[shape(d) for d in draws]
    geometry={'grid_columns':columns,'last':shapes[-1],'mean':{key:sum(s[key] for s in shapes)/n for key in shapes[0]}}
    # Use an explicitly defined recent window; cycles measured in draws, not calendar days.
    tail=draws[-256:];m=len(tail)
    centered=[]
    for ball in range(1,p.pool+1):
        values=[float(ball in d.numbers) for d in tail];mean=sum(values)/m
        centered.append([v-mean for v in values])
    ac=[]
    for lag in range(1,min(30,m//3)+1):
        vals=[sum(x[i]*x[i-lag] for i in range(lag,m))/sum(v*v for v in x) for x in centered if sum(v*v for v in x)>0]
        ac.append({'lag':lag,'mean':sum(vals)/len(vals) if vals else 0})
    spectrum=[]
    for k in range(1,m//2+1):
        cos=[math.cos(2*math.pi*k*t/m) for t in range(m)]
        sin=[math.sin(2*math.pi*k*t/m) for t in range(m)]
        power=sum(sum(x[t]*cos[t] for t in range(m))**2+sum(x[t]*sin[t] for t in range(m))**2 for x in centered)/(p.pool*m*m)
        spectrum.append({'period':m/k,'power':power})
    expected=p.pick*p.pick/p.pool
    theory=[math.comb(p.pick,k)*math.comb(p.pool-p.pick,p.pick-k)/math.comb(p.pool,p.pick) if k>=max(0,2*p.pick-p.pool) else 0 for k in range(p.pick+1)]
    distributions={}
    for name,series in result['series'].items():
        cumulative=0;running=[]
        for matches in series:
            cumulative+=matches-expected;running.append(cumulative)
        distributions[name]={'counts':[series.count(k) for k in range(p.pick+1)],'running':running}
    return {'correlation':correlation,'fair_correlation':-1/(p.pool-1),'expected_pair':expected_pair,
            'geometry':geometry,'cycles':{'window':m,'autocorrelation':ac,'spectrum':spectrum},
            'theory':theory,'distributions':distributions,'draws':result['series_draws'],'hedge_weights':result['hedge_weights']}

SIM_FEATURES=('historica','reciente_25','exponencial','momentum','rezago')
def simulate(draws,p,weights):
    if set(weights)!=set(SIM_FEATURES) or not all(type(v) in (float,int) and math.isfinite(v) and -5<=v<=5 for v in weights.values()):
        raise ValueError('Pesos finitos entre -5 y 5 para los cinco factores')
    if not any(weights.values()):raise ValueError('Al menos un peso no nulo')
    if len(draws)<80:raise ValueError('Se requieren 80 sorteos')
    def line(h):
        f=features(h,p)
        return rank([sum(weights[k]*f[k][i] for k in SIM_FEATURES) for i in range(p.pool)],p)
    matches=[len(line(draws[:i])&draws[i].numbers) for i in range(50,len(draws))]
    return {'n':len(matches),'mean':sum(matches)/len(matches),'expected':p.pick*p.pick/p.pool,
            'histogram':[matches.count(i) for i in range(p.pick+1)],
            'warning':'Ajuste exploratorio sobre el mismo histórico; no es validación independiente.'}
