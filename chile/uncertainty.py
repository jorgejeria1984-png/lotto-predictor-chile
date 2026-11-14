"""Compare a frozen holdout result against independent fair draws."""
from math import comb, fsum, sqrt
from random import Random
from bisect import bisect_left


def compare_mean(profile, trials, observed_total, simulations=100_000, seed=42):
    if trials < 1 or simulations < 1:
        raise ValueError('trials and simulations must be positive')
    k, n = profile.pick, profile.pool
    low = max(0, 2*k-n)
    if not isinstance(observed_total, int) or not low*trials <= observed_total <= k*trials:
        raise ValueError('observed total outside possible range')
    probs = [comb(k,j)*comb(n-k,k-j)/comb(n,k) if j>=low else 0.0 for j in range(k+1)]
    dist = [1.0]
    for _ in range(trials):
        out = [0.0]*(len(dist)+k)
        for i, mass in enumerate(dist):
            for j in range(low,k+1):
                out[i+j] += mass*probs[j]
        dist = out
    exact = min(1.0, fsum(dist[observed_total:]))
    cdf = []
    total = 0.0
    for prob in probs:
        total += prob
        cdf.append(total)
    cdf[-1] = 1.0
    rng = Random(seed)
    hits = sum(sum(bisect_left(cdf,rng.random()) for _ in range(trials)) >= observed_total for _ in range(simulations))
    estimate = hits/simulations
    z = 1.959963984540054
    denom = 1+z*z/simulations
    center = (estimate+z*z/(2*simulations))/denom
    half = z*sqrt(estimate*(1-estimate)/simulations+z*z/(4*simulations**2))/denom
    return {'trials':trials,'observed_total':observed_total,'exact_p':exact,'simulations':simulations,'monte_carlo_p':estimate,'mc_ci95':[max(0,center-half),min(1,center+half)],'seed':seed}
