import warnings
import numpy as np
from scipy.stats import mannwhitneyu, spearmanr
import statsmodels.api as sm

METRICS = ['attempt_effort_score', 'verification_rate', 'unnecessary_ai_use_flag',
           'no_ai_completion_rate', 'evaluation_completion_rate']


def analyze(frame):
    result = {'unit': 'user', 'participants': len(frame), 'mann_whitney': [], 'spearman': [],
              'logistic': {'status': 'insufficient_data'},
              'reference': {'source': 'User-provided specification, not independently verified paper',
                            'ai_first_percent': 68.97, 'logistic_odds_ratio': 2.114, 'logistic_p': '<0.001',
                            'table_5': None},
              'limitations': ['Behavioral proxies are not Likert scales; coefficients are not directly interchangeable.',
                              'Observational associations do not establish causality.',
                              'Missing correctness observations remain missing, not zero.',
                              'Inference uses closed sessions aggregated to one row per user.']}
    if frame.empty:
        return result
    for metric in METRICS:
        a = frame.loc[frame.is_ai_first == 1, metric].dropna().astype(float)
        b = frame.loc[frame.is_ai_first == 0, metric].dropna().astype(float)
        row = {'metric': metric, 'n_ai_first': len(a), 'n_other': len(b), 'status': 'insufficient_data'}
        if len(a) >= 2 and len(b) >= 2:
            test = mannwhitneyu(a, b, alternative='two-sided', method='auto')
            row.update(status='ok', u=float(test.statistic), p=float(test.pvalue),
                       rank_biserial=float(2*test.statistic/(len(a)*len(b))-1))
        result['mann_whitney'].append(row)
    columns = ['is_ai_first', 'ai_usage_frequency'] + METRICS
    for i, x in enumerate(columns):
        for y in columns[i+1:]:
            pair = frame[[x, y]].dropna().astype(float)
            row = {'x': x, 'y': y, 'n': len(pair), 'status': 'insufficient_or_constant_data'}
            if len(pair) >= 3 and pair[x].nunique() > 1 and pair[y].nunique() > 1:
                test = spearmanr(pair[x], pair[y])
                row.update(status='ok', rho=float(test.statistic), p=float(test.pvalue))
            result['spearman'].append(row)
    data = frame[['is_ai_first', 'ai_usage_frequency']].dropna().astype(float)
    if len(data) >= 20 and data.is_ai_first.nunique() == 2 and data.ai_usage_frequency.nunique() > 1:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error')
                fit = sm.Logit(data.is_ai_first, sm.add_constant(data.ai_usage_frequency)).fit(disp=False)
                beta = fit.params['ai_usage_frequency']
                ci = np.exp(fit.conf_int().loc['ai_usage_frequency'].to_numpy())
                odds = float(np.exp(beta))
                if not fit.mle_retvals['converged'] or not np.isfinite([odds, *ci]).all():
                    raise ValueError('Unstable fit')
                result['logistic'] = dict(status='ok', n=len(data), odds_ratio=odds,
                                          ci_low=float(ci[0]), ci_high=float(ci[1]),
                                          p=float(fit.pvalues['ai_usage_frequency']))
        except Exception as exc:
            result['logistic'] = {'status': 'unstable_fit', 'reason': type(exc).__name__}
    return result
