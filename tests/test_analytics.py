from datetime import datetime,timedelta,timezone
import numpy as np
import pandas as pd
import pytest
from analytics.etl import reconstruct,summarize,user_frame
from analytics.stats import analyze,METRICS

def fixture_events():
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    items=[('session_started',{'problem_domain':'math'},0),('attempt_submitted',{'attempt_text':'a'*500},300),
           ('ai_hint_requested',{},301),('ai_hint_delivered',{},302),
           ('verification_submitted',{'hint_event_id':'3'},303),
           ('attempt_correctness_reported',{'attempt_event_id':'1','adequate':True},304),
           ('evaluation_submitted',{'makes_sense':True},305),
           ('session_closed',{'final_status':'solved_with_ai','total_duration_ms':306000},306)]
    return [dict(id=str(i),session_id='s',user_id='u',event_type=k,payload=p,created_at=start+timedelta(seconds=t)) for i,(k,p,t) in enumerate(items)]

def test_golden_reconstruction():
    events=fixture_events();row=reconstruct(events)[0]
    assert row['attempt_effort_score']==1
    assert row['is_ai_first'] is False
    assert row['time_to_ai_seconds']==301
    assert row['verification_rate']==1
    assert row['unnecessary_ai_use_flag'] is True
    assert row['prior_7d_ai_requests']==0
    assert summarize([row],events,datetime(2026,1,2,tzinfo=timezone.utc))['ai_requests_7d']==1
    assert len(user_frame([row,{**row,'session_id':'s2'}]))==1

def test_invalidation_and_missingness():
    events=fixture_events()
    events.append(dict(id='99',session_id='s',user_id='u',event_type='event_invalidated',payload={'target_event_id':'1'},created_at=events[-1]['created_at']+timedelta(seconds=1)))
    row=reconstruct(events)[0]
    assert row['is_ai_first'] is True
    assert row['attempt_effort_score']==0
    assert row['unnecessary_ai_use_flag'] is None
    events[7]['payload']['total_duration_ms']=-1
    assert reconstruct(events)[0]['excluded'] is True

def test_stats_known_direction_and_constants():
    frame=pd.DataFrame([dict(is_ai_first=g,ai_usage_frequency=i,**{m:i for m in METRICS}) for g,nums in [(0,[1,2,3]),(1,[4,5,6])] for i in nums])
    output=analyze(frame)
    assert output['mann_whitney'][0]['u']==9
    assert output['mann_whitney'][0]['rank_biserial']==1
    assert output['spearman'][-1]['rho']==pytest.approx(1)
    assert output['logistic']['status']=='insufficient_data'
    assert analyze(pd.DataFrame())['participants']==0

def test_logistic_finite_or_and_ci():
    rng=np.random.default_rng(42);x=rng.uniform(0,10,250);y=rng.binomial(1,1/(1+np.exp(-(-1+.25*x))))
    frame=pd.DataFrame(dict(is_ai_first=y,ai_usage_frequency=x,**{m:rng.random(250) for m in METRICS}))
    model=analyze(frame)['logistic']
    assert model['status']=='ok'
    assert model['ci_low']<model['odds_ratio']<model['ci_high']
    assert model['odds_ratio']>1
