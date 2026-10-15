"""A fixed experiment runner; never executes LLM-generated Python."""
import math
import random


def validate(config):
    required = {'seed', 'context', 'horizon', 'ridge'}
    if set(config) != required:
        raise ValueError(f'Config keys must be {sorted(required)}')
    for key, low, high in [('seed', 0, 2**32-1), ('context', 2, 48), ('horizon', 1, 24)]:
        if type(config[key]) is not int or not low <= config[key] <= high:
            raise ValueError(f'{key} must be an integer in [{low}, {high}]')
    if type(config['ridge']) not in (float, int) or not math.isfinite(config['ridge']) or not .001 <= config['ridge'] <= 100:
        raise ValueError('ridge must be finite and in [.001, 100]')


def solve(a, b):
    """Gaussian elimination with partial pivoting, for small ridge systems."""
    rows = [list(row)+[value] for row, value in zip(a, b)]
    n = len(rows)
    for i in range(n):
        pivot = max(range(i,n),key=lambda k: abs(rows[k][i]))
        rows[i],rows[pivot] = rows[pivot],rows[i]
        if abs(rows[i][i]) < 1e-12: raise ValueError('Singular system')
        scale = rows[i][i]
        rows[i] = [v/scale for v in rows[i]]
        for j in range(n):
            if j != i:
                factor = rows[j][i]
                rows[j] = [x-factor*y for x,y in zip(rows[j],rows[i])]
    return [row[-1] for row in rows]


def run(config):
    validate(config)
    rng = random.Random(config['seed'])
    signal = [math.sin(2*math.pi*t/48)+.3*math.sin(2*math.pi*t/13)+rng.gauss(0,.08) for t in range(1800)]
    # Split raw timeline BEFORE constructing windows; no boundary crossing.
    parts = {'train':signal[:1080], 'val':signal[1080:1440], 'test':signal[1440:]}
    mean = sum(parts['train'])/len(parts['train'])
    std = math.sqrt(sum((v-mean)**2 for v in parts['train'])/len(parts['train']))
    c,h = config['context'], config['horizon']
    windows = {}
    for split, values in parts.items():
        a = [(v-mean)/std for v in values]
        windows[split] = [(a[i:i+c],a[i+c:i+c+h]) for i in range(0,len(a)-c-h+1,h)]
    d = c+1
    gram = [[0.0]*d for _ in range(d)]
    cross = [[0.0]*h for _ in range(d)]
    for x,y in windows['train']:
        x = x+[1.0]
        for i in range(d):
            for j in range(d): gram[i][j] += x[i]*x[j]
            for k in range(h): cross[i][k] += x[i]*y[k]
    for i in range(c): gram[i][i] += config['ridge']
    weights = [solve(gram,[cross[i][k] for i in range(d)]) for k in range(h)]
    scores = {}
    for split in ('val','test'):
        scores[split] = {}
        for model in ('persistence','ridge_ar'):
            errors = []
            for x,y in windows[split]:
                pred = [x[-1]]*h if model=='persistence' else [sum(a*b for a,b in zip(x+[1.0],w)) for w in weights]
                errors.extend(p-t for p,t in zip(pred,y))
            scores[split][model] = {'mse':sum(e*e for e in errors)/len(errors),
                                   'mae':sum(abs(e) for e in errors)/len(errors)}
    selected = min(scores['val'],key=lambda model: scores['val'][model]['mse'])
    return {'dataset':'synthetic_periodic_v1','config':config,'normalization':{'mean':mean,'std':std},
            'split_samples':{k:len(v) for k,v in parts.items()},
            'windows':{k:len(v) for k,v in windows.items()},
            'validation':scores['val'],'test':scores['test'],'selected_on_validation':selected,
            'limitations':['Synthetic data only; not a paper reproduction.',
                           'Single seed; no statistical significance claim.',
                           'Ridge autoregression is not PatchTST or another foundation model.']}
