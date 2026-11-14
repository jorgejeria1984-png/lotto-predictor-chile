"""Causal online challengers for Chile. Experimental, not a winning-number guarantee."""
import argparse
import json
import math
import random
from collections import Counter
from engine import PROFILES, features, predictions, rank, chance_tail, binomial_tail
from history import DATA, audit, read_records
from uncertainty import compare_mean

FEATURES = ('historica','reciente_10','reciente_25','reciente_50','exponencial','rezago','momentum')
VERSION = 'chile-online-v1'

def matrix(history, profile):
    f = features(history, profile)
    return [tuple(max(-4.0,min(4.0,f[name][i])) for name in FEATURES) for i in range(profile.pool)]

def sigmoid(x):
    return 1/(1+math.exp(-max(-35.0,min(35.0,x))))

def dot(a,b):
    return sum(x*y for x,y in zip(a,b))

class OnlineLogit:
    """Independent marginal logistic scores; fixed k by ranking, not independent draw model."""
    def __init__(self,p):
        self.p = p
        self.weights = [0.0]*len(FEATURES)
        self.accum = [1e-6]*len(FEATURES)
        self.intercept = math.log(p.pick/(p.pool-p.pick))

    def predict(self,x):
        return rank([self.intercept+dot(self.weights,row) for row in x],self.p)

    def update(self,x,actual):
        errors = [sigmoid(self.intercept+dot(self.weights,row))-(i+1 in actual) for i,row in enumerate(x)]
        for j in range(len(self.weights)):
            grad = sum(err*row[j] for err,row in zip(errors,x))/self.p.pool + .02*self.weights[j]
            self.accum[j] += grad*grad
            self.weights[j] -= .04*grad/math.sqrt(self.accum[j])

class Evolution:
    """Online genetic search over feature weights; mutate only after scoring a realized draw."""
    def __init__(self,p,seed=42):
        self.p=p
        self.rng=random.Random(seed)
        self.population=[[float(i==j) for i in range(len(FEATURES))] for j in range(len(FEATURES))]
        self.population += [[self.rng.gauss(0,.5) for _ in FEATURES] for _ in range(9)]
        self.reward=[0.0]*len(self.population)
        self.steps=0

    def lines(self,x):
        return [rank([dot(w,row) for row in x],self.p) for w in self.population]

    def pick(self,lines):
        return lines[max(range(len(lines)),key=lambda i:(self.reward[i],-i))]

    def update(self,lines,actual):
        expected=self.p.pick**2/self.p.pool
        self.reward=[.90*r+len(line&actual)-expected for r,line in zip(self.reward,lines)]
        self.steps+=1
        if self.steps%8==0:
            parents=sorted(range(len(lines)),key=lambda i:self.reward[i],reverse=True)
            a,b=self.population[parents[0]],self.population[parents[1]]
            for i in parents[-4:]:
                self.population[i]=[max(-3,min(3,self.rng.choice((u,v))+self.rng.gauss(0,.25))) for u,v in zip(a,b)]
                self.reward[i]=0.0

class LstmChallenger:
    """Optional CPU PyTorch recurrent model. One causal update per draw, no future data."""
    def __init__(self,p,seed=42,window=10):
        try:
            import torch
            from torch import nn
        except ImportError as exc:
            raise RuntimeError('Instale PyTorch CPU para habilitar --lstm') from exc
        self.torch=torch
        torch.manual_seed(seed)
        torch.set_num_threads(1)
        self.p=p
        self.window=window
        self.rnn=nn.LSTM(p.pool,16,batch_first=True)
        self.head=nn.Linear(16,p.pool)
        self.opt=torch.optim.AdamW([*self.rnn.parameters(),*self.head.parameters()],lr=.005,weight_decay=.05)

    def encoding(self,numbers):
        return [float(i in numbers) for i in range(1,self.p.pool+1)]

    def logits(self,history):
        x=self.torch.tensor([[self.encoding(d.numbers) for d in history[-self.window:]]],dtype=self.torch.float32)
        out,_=self.rnn(x)
        return self.head(out[:,-1,:]).squeeze(0)

    def predict(self,history):
        with self.torch.no_grad():
            return rank(self.logits(history).tolist(),self.p)

    def update(self,history,actual):
        self.opt.zero_grad()
        y=self.torch.tensor(self.encoding(actual),dtype=self.torch.float32)
        loss=self.torch.nn.functional.binary_cross_entropy_with_logits(self.logits(history),y)
        loss.backward()
        self.torch.nn.utils.clip_grad_norm_([*self.rnn.parameters(),*self.head.parameters()],1.0)
        self.opt.step()

def validate_history(draws,p):
    if len(draws)<10:
        raise ValueError('Se necesitan al menos 10 sorteos')
    if any(a.number+1!=b.number or a.date>=b.date for a,b in zip(draws,draws[1:])):
        raise ValueError('Historial debe ser cronológico y consecutivo')
    if any(len(d.numbers)!=p.pick or not all(1<=n<=p.pool for n in d.numbers) for d in draws):
        raise ValueError('Bolillas inválidas')

def replay(draws,p,warmup=50,seed=42,lstm=False,simulations=10000):
    validate_history(draws,p)
    if warmup<10 or len(draws)<warmup+30:
        raise ValueError('Se requieren 80 sorteos con protocolo de 50 de calentamiento')
    rng=random.Random(seed)
    logit=OnlineLogit(p)
    genetic=Evolution(p,seed)
    neural=LstmChallenger(p,seed) if lstm else None
    records={}
    for i in range(10,len(draws)):
        h=draws[:i]; actual=draws[i].numbers
        x=matrix(h,p); candidates=genetic.lines(x)
        if i>=warmup:
            lines=predictions(h,p)
            lines['logit_online']=logit.predict(x)
            lines['evolutivo_online']=genetic.pick(candidates)
            if neural:
                lines['lstm_online']=neural.predict(h)
            lines['azar']=frozenset(rng.sample(range(1,p.pool+1),p.pick))
            for name,line in lines.items():
                records.setdefault(name,[]).append(len(line&actual))
        # The actual draw is only consumed AFTER forecasts have been generated.
        logit.update(x,actual)
        genetic.update(candidates,actual)
        if neural:
            neural.update(h,actual)
    split=2*(len(draws)-warmup)//3
    winner=max((s for s in records if s!='azar'),key=lambda s:(sum(records[s][:split]),s))
    def summary(v):
        return {'n':len(v),'total':sum(v),'media':sum(v)/len(v),'objetivo':sum(x>=p.target for x in v)}
    selection={s:summary(v[:split]) for s,v in records.items()}
    holdout={s:summary(v[split:]) for s,v in records.items()}
    x=matrix(draws,p)
    lines=predictions(draws,p)
    lines['logit_online']=logit.predict(x)
    lines['evolutivo_online']=genetic.pick(genetic.lines(x))
    if neural:
        lines['lstm_online']=neural.predict(draws)
    # Freeze the selection rule; holdout never chooses champion.
    chosen=holdout[winner]
    return {'version':VERSION,'ultimo_sorteo':draws[-1].number,'estrategia':winner,
            'seleccion':selection,'validacion_exploratoria':holdout,
            'azar_media':p.pick**2/p.pool,'objetivo':p.target,
            'p_objetivo':binomial_tail(chosen['n'],chosen['objetivo'],chance_tail(p,p.target)),
            'contraste_media':compare_mean(p,chosen['n'],chosen['total'],simulations,seed),
            'lineas':{s:sorted(v) for s,v in lines.items()},
            'advertencia':'Los datos históricos ya explorados no constituyen validación independiente de estas nuevas estrategias.'}

def bias_report(draws,p):
    """Marginal frequency test with Bonferroni control; cannot identify physical cause."""
    validate_history(draws,p)
    n=len(draws); prob=p.pick/p.pool
    counts=Counter(x for d in draws for x in d.numbers)
    result=[]
    for ball in range(1,p.pool+1):
        k=counts[ball]
        tail=min(binomial_tail(n,k,prob),binomial_tail(n,n-k,1-prob))
        adjusted=min(1.0,2*p.pool*tail)
        result.append({'numero':ball,'apariciones':k,'esperado':n*prob,
                       'z':(k-n*prob)/math.sqrt(n*prob*(1-prob)),
                       'p_bonferroni':adjusted,'alerta':adjusted<.05})
    return sorted(result,key=lambda x:(x['p_bonferroni'],x['numero']))

def load_history(game,folder=DATA):
    records=read_records(folder/f'{game}.csv',game)
    count=audit(records,game)['bloque_reciente_contiguo']
    keys=sorted(records)[-count:] if count else []
    return [records[k][0] for k in keys]

def main():
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',required=True,choices=PROFILES)
    parser.add_argument('--data-dir',type=Path,default=DATA)
    parser.add_argument('--lstm',action='store_true')
    parser.add_argument('--simulations',type=int,default=100000)
    args=parser.parse_args()
    h=load_history(args.game,args.data_dir); p=PROFILES[args.game]
    result=replay(h,p,lstm=args.lstm,simulations=args.simulations)
    result['diagnostico_sesgo']=bias_report(h,p)
    # Report is descriptive. Lines for prospective scoring are archived separately.
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
