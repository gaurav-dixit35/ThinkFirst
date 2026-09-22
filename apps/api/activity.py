"""Owner-scoped history and factual activity summaries; no provider calls."""
import hashlib
import json
from collections import defaultdict
from datetime import timedelta
from sqlalchemy import select, exists, or_, func
from sqlalchemy.orm import aliased
from analytics.etl import effective, timestamp, reconstruct, summarize
from .db import Session, Event, ConversationMetadata, ConversationState, ConversationDeletion, now

LABELS = {'open':'In progress','solved_with_ai':'Completed with AI',
          'solved_independently':'Completed independently',
          'solved_without_ai_response':'Completed without an AI reply','abandoned':'Left unfinished','closed':'Closed'}
SOURCE_TYPES = {'session_started','attempt_submitted','ai_hint_requested','ai_hint_delivered','ai_hint_failed'}


def title(question):
    text = ' '.join(question.split())
    return text if len(text) <= 80 else text[:77].rstrip()+'…'


def overview(events):
    by = lambda kind:[e for e in events if e['event_type']==kind]
    start=by('session_started')[0]
    closes=by('session_closed')
    outcome=closes[-1]['payload']['final_status'] if closes else 'open'
    source=[e for e in events if e['event_type'] in SOURCE_TYPES]
    fingerprint=hashlib.sha256(json.dumps(source,sort_keys=True,default=str).encode()).hexdigest()
    attempts,answers=by('attempt_submitted'),by('ai_hint_delivered')
    return dict(own_attempts=len(attempts),ai_questions=len(by('ai_hint_requested')),ai_answers=len(answers),
                failed_requests=len(by('ai_hint_failed')),ai_reviews=len(by('ai_analysis_delivered')),
                initial_mode=start['payload'].get('initial_mode','ask_ai'),
                outcome=outcome,status_label=LABELS.get(outcome,'Closed'),
                fingerprint=fingerprint,can_review=bool(attempts or answers))


def history(db,user_id,q='',status='all',experience='all',limit=25,offset=0,folder='active'):
    start,close,entry,correction=aliased(Event),aliased(Event),aliased(Event),aliased(Event)
    protocol=func.coalesce(start.payload['experience'].as_string(),'guided')
    query=(select(Session,start,close,ConversationMetadata)
           .join(start,(start.session_id==Session.id)&(start.event_type=='session_started'))
           .outerjoin(close,(close.session_id==Session.id)&(close.event_type=='session_closed'))
           .outerjoin(ConversationMetadata,ConversationMetadata.session_id==Session.id)
           .where(Session.user_id==user_id))
    archived=exists(select(ConversationState.session_id).where(ConversationState.session_id==Session.id,ConversationState.archived.is_(True)))
    deleting=exists(select(ConversationDeletion.id).where(ConversationDeletion.session_id==Session.id,ConversationDeletion.status=='pending'))
    query=query.where(deleting if folder=='deletion' else ~deleting)
    if folder=='active':query=query.where(~archived)
    if folder=='archived':query=query.where(archived)
    if experience!='all':query=query.where(protocol==experience)
    if status=='open':query=query.where(Session.status=='open')
    if status=='abandoned':query=query.where(close.payload['final_status'].as_string()=='abandoned')
    if status=='completed':query=query.where(Session.status=='closed',close.payload['final_status'].as_string()!='abandoned')
    if q.strip():
        term='%'+q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        valid=~exists(select(correction.id).where(correction.session_id==entry.session_id,
            correction.event_type=='event_invalidated',correction.payload['target_event_id'].as_string()==entry.id))
        matches=exists(select(entry.id).where(entry.session_id==Session.id,valid,or_(
            (entry.event_type=='session_started')&entry.payload['problem_text'].as_string().ilike(term,escape='\\'),
            (entry.event_type=='attempt_submitted')&entry.payload['attempt_text'].as_string().ilike(term,escape='\\'),
            (entry.event_type=='ai_hint_requested')&entry.payload['followup_text'].as_string().ilike(term,escape='\\'),
            (entry.event_type=='ai_hint_delivered')&entry.payload['hint_text'].as_string().ilike(term,escape='\\'))))
        query=query.where(or_(ConversationMetadata.title.ilike(term,escape='\\'),matches))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rows=db.execute(query.order_by(Session.started_at.desc(),Session.id.desc()).offset(offset).limit(limit)).all()
    result=[]
    for session,first,last,metadata in rows:
        outcome=last.payload['final_status'] if last else session.status
        result.append(dict(id=session.id,title=metadata.title if metadata and metadata.title else title(first.payload['problem_text']),
            custom_title=bool(metadata and metadata.title),problem_text=first.payload['problem_text'],domain=session.problem_domain,
            status=session.status,outcome=outcome,status_label=LABELS.get(outcome,'Closed'),
            experience=first.payload.get('experience','guided'),started_at=timestamp(session.started_at).isoformat()))
    return dict(items=result,total=total,offset=offset,limit=limit,has_more=offset+len(result)<total)


def progress(events,experience='chat'):
    grouped=defaultdict(list)
    for e in effective(events):grouped[e['session_id']].append(e)
    selected=[es for es in grouped.values() if any(e['event_type']=='session_started' and e['payload'].get('experience','guided')==experience for e in es)]
    counts=[overview(es) for es in selected]
    totals=dict(conversations=len(counts),in_progress=sum(c['outcome']=='open' for c in counts),
        completed=sum(c['outcome'].startswith('solved_') for c in counts),unfinished=sum(c['outcome']=='abandoned' for c in counts),
        own_attempts=sum(c['own_attempts'] for c in counts),ai_questions=sum(c['ai_questions'] for c in counts),
        ai_answers=sum(c['ai_answers'] for c in counts),failed_requests=sum(c['failed_requests'] for c in counts),
        ai_reviews=sum(c['ai_reviews'] for c in counts),started_myself=sum(c['initial_mode']=='try_myself' for c in counts))
    modes=dict(own_only=sum(c['own_attempts']>0 and c['ai_answers']==0 for c in counts),
               ai_only=sum(c['own_attempts']==0 and c['ai_answers']>0 for c in counts),
               both=sum(c['own_attempts']>0 and c['ai_answers']>0 for c in counts),
               no_saved_work=sum(c['own_attempts']==0 and c['ai_answers']==0 for c in counts))
    current=now()
    monday=(current-timedelta(days=current.weekday())).replace(hour=0,minute=0,second=0,microsecond=0)
    weeks=[]
    for n in range(3,-1,-1):
        begin=monday-timedelta(weeks=n)
        es=[e for group in selected for e in group if begin<=timestamp(e['created_at'])<begin+timedelta(weeks=1) and timestamp(e['created_at'])<=current]
        weeks.append(dict(week=begin.date().isoformat(),own_attempts=sum(e['event_type']=='attempt_submitted' for e in es),
                          ai_answers=sum(e['event_type']=='ai_hint_delivered' for e in es)))
    scoped = [e for group in selected for e in group]
    trend = summarize(reconstruct(scoped), scoped, current)['trend']
    return dict(experience=experience,totals=totals,modes=modes,weeks=weeks,trend=trend,updated_at=current.isoformat())


def analysis_context(events):
    summary=overview(events)
    excerpts=[]
    for e in events:
        p=e['payload']
        text={'session_started':p.get('problem_text'),'attempt_submitted':p.get('attempt_text'),
              'ai_hint_requested':p.get('followup_text'),'ai_hint_delivered':p.get('hint_text')}.get(e['event_type'])
        if text:excerpts.append({'kind':e['event_type'],'text':text})
    selected=[]
    remaining=16000
    for item in reversed(excerpts[-24:]):
        text=item['text'][-remaining:]
        selected.insert(0,{**item,'text':text})
        remaining-=len(text)
        if not remaining:break
    truncated=len(selected)!=len(excerpts) or sum(len(e['text']) for e in selected)!=sum(len(e['text']) for e in excerpts)
    context=dict(recorded_counts={k:summary[k] for k in ('own_attempts','ai_questions','ai_answers','failed_requests')},
                 excerpts=selected,excerpts_truncated=truncated)
    if not any(item['kind']=='session_started' for item in selected):
        question=next(e['payload']['problem_text'] for e in events if e['event_type']=='session_started')
        context['original_question']=question[:2000]
        context['question_truncated']=len(question)>2000
    return json.dumps(context),summary['fingerprint'],truncated
