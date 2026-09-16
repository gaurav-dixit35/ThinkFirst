'use client';
import {useCallback, useEffect, useRef, useState} from 'react';
import Link from 'next/link';
import AnswerContent from './AnswerContent';
import {ArrowRight, Check, Feather, Lightbulb} from 'lucide-react';
import {api, LogEvent, SessionData, ProviderName} from '@/lib/api';
import {emitEvent, flushQueue} from '@/lib/eventClient';
import {setLeaveHandler} from '@/lib/navigation';
import AIConnection from './AIConnection';
import {useAttemptDraft} from '@/lib/useAttemptDraft';
import {completeHint, HintRequest, requestKey} from '@/lib/aiRequest';

export default function SessionFlow({id}: {id:string}) {
  const [data, setData] = useState<SessionData | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const {attempt, setAttempt, partial, setPartial, storageError} = useAttemptDraft(id);
  const [finishing, setFinishing] = useState(false);
  const [selectedProvider,setSelectedProvider] = useState<ProviderName|null>(null);
  const hintRequest = useRef<HintRequest | null>(null);
  const [followup,setFollowup] = useState('');
  const recovered = useRef(false);
  const closeRequest = useRef<{event_id:string;final_status:string} | null>(null);
  const reload = useCallback(async () => {setData(await api<SessionData>(`/sessions/${id}`));},[id]);
  useEffect(() => {reload().catch(e=>setError(e.message));},[reload]);
  async function action(work:()=>Promise<unknown>) {
    setBusy(true);setError('');
    try {await work();await reload();}
    catch(e) {setError((e as Error).message);try {await reload();} catch {/* Original actionable error remains visible. */}}
    finally {setBusy(false);}
  }
  const events = data?.events || [];
  const attempts = events.filter(e=>e.event_type==='attempt_submitted');
  const hints = events.filter(e=>e.event_type==='ai_hint_delivered');
  const aiCount = events.filter(e=>e.event_type==='ai_hint_requested').length;
  const unfinishedRequest = events.find(e=>e.event_type==='ai_hint_requested'&&!events.some(r=>['ai_hint_delivered','ai_hint_failed'].includes(r.event_type)&&r.payload.request_event_id===e.id));
  const gatePassed = events.some(e=>['attempt_submitted','attempt_skipped'].includes(e.event_type));
  const pending = hints.filter(h=>!events.some(e=>['verification_submitted','verification_skipped'].includes(e.event_type)&&e.payload.hint_event_id===h.id));
  const decisions = events.filter(e=>['ai_hint_delivered','evaluation_submitted','evaluation_skipped'].includes(e.event_type));
  const evaluated = !!decisions.at(-1)?.event_type.startsWith('evaluation_');
  useEffect(()=>{
    if(!data || data.status!=='open' || busy || recovered.current)return;
    recovered.current=true;
    try {
      setFollowup(localStorage.getItem(`thinkfirst.followup.${id}`) || '');
      const saved=localStorage.getItem(requestKey(id));
      const request:HintRequest|null=unfinishedRequest?{event_id:unfinishedRequest.id,session_id:id,tier:unfinishedRequest.payload.tier_requested,provider:unfinishedRequest.payload.selected_provider || undefined,followup_text:unfinishedRequest.payload.followup_text || undefined}:saved?JSON.parse(saved):null;
      if(request && request.session_id===id) {
        hintRequest.current=request;
        void action(async()=>{try{await completeHint(request,true);if(request.followup_text){setFollowup('');localStorage.removeItem(`thinkfirst.followup.${id}`);}}finally{if(!localStorage.getItem(requestKey(id)))hintRequest.current=null;}});
      }
    } catch {setError('Your browser could not restore the pending AI request. Keep this page open and retry.');}
  },[data,busy,id,unfinishedRequest]);
  async function close(status:string) {
    await flushQueue(id);
    if (!closeRequest.current || closeRequest.current.final_status !== status) closeRequest.current={event_id:crypto.randomUUID(),final_status:status};
    await api(`/sessions/${id}/close`,closeRequest.current);
  }
  useEffect(()=>{
    if(data?.status==='open') setLeaveHandler(async()=>{if(busy) throw new Error('Please wait for the current action to finish.');await close('abandoned');});
    else setLeaveHandler(null);
    return ()=>setLeaveHandler(null);
  });
  useEffect(()=>{
    const warn=(e:BeforeUnloadEvent)=>{if(data?.status==='open'){e.preventDefault();}};
    window.addEventListener('beforeunload',warn);return ()=>window.removeEventListener('beforeunload',warn);
  },[data?.status]);
  if(!data) return <div className="narrow-page"><h1>Your thinking space</h1>{error?<div className="error" role="alert">{error}<button onClick={()=>action(reload)}>Retry</button></div>:<p>Loading your saved work…</p>}</div>;
  if(data.status==='closed') return <SessionSummary data={data}/>;
  async function requestHint(question?:string) {
    await flushQueue(id);
    const tier=Math.min(hints.length+1,3);
    const unfinished = events.find(e=>e.event_type==='ai_hint_requested' && e.payload.tier_requested===tier &&
      !events.some(result=>['ai_hint_delivered','ai_hint_failed'].includes(result.event_type)&&result.payload.request_event_id===e.id));
    if(!hintRequest.current || hintRequest.current.tier!==tier) hintRequest.current={event_id:unfinished?.id || crypto.randomUUID(),session_id:id,tier,provider:unfinished?.payload.selected_provider || selectedProvider || undefined,followup_text:unfinished?.payload.followup_text || question || undefined};
    const request=hintRequest.current;
    try {await completeHint(request);hintRequest.current=null;if(request.followup_text){setFollowup('');localStorage.removeItem(`thinkfirst.followup.${id}`);}}
    catch(e) {
      // A definitive provider failure is recorded; a network interruption reuses the ID.
      if(!localStorage.getItem(requestKey(id))) hintRequest.current=null;
      throw e;
    }
  }
  return <><div className="page-heading"><div><div className="eyebrow">YOUR THINKING SPACE</div><h1>One thought at a time.</h1><p>Try your approach. Explore a hint. Make sense of what you find.</p></div><span className="pill"><span/> SESSION IN PROGRESS</span></div>
  <div className="flow-steps">{['Your question','Your attempt','A little support','Reflect'].map((s,i)=><span className={i===0||i===1||i===2&&gatePassed||i===3&&finishing?'current':''} key={s}><b>{String(i+1).padStart(2,'0')}</b>{s}</span>)}</div>
  {error&&<div className="error" role="alert">{error}<button disabled={busy} onClick={()=>action(async()=>{await flushQueue(id);if(hintRequest.current){const request=hintRequest.current;try{await completeHint(request,true);if(request.followup_text){setFollowup('');localStorage.removeItem(`thinkfirst.followup.${id}`);}}finally{if(!localStorage.getItem(requestKey(id)))hintRequest.current=null;}}})}>Retry sync / refresh</button></div>}
  {storageError && <div className="error" role="alert">{storageError}</div>}
  <section className="problem-card"><span className="eyebrow">{data.summary.problem_domain.replace('_',' ')} / YOUR QUESTION</span><p className="problem-text">{events.find(e=>e.event_type==='session_started')?.payload.problem_text}</p></section>
  <div className="work-grid"><section className="form-card"><div className="card-heading"><span className="round-icon"><Feather size={19}/></span><div><h3>Your own starting point</h3><p>Even a rough idea gives you something to build on.</p></div></div>
  {attempts.map(a=><div className="saved-attempt" key={a.id}><span className="eyebrow"><Check size={12}/> SAVED ATTEMPT</span><p>{a.payload.attempt_text}</p><div className="adequacy"><span>Looking back, was this attempt adequate?</span>{events.some(e=>e.event_type==='attempt_correctness_reported'&&e.payload.attempt_event_id===a.id)?<small>Self-assessment saved</small>:<><button disabled={busy} onClick={()=>action(()=>emitEvent(id,'attempt_correctness_reported',{attempt_event_id:a.id,adequate:true}))}>Yes</button><button disabled={busy} onClick={()=>action(()=>emitEvent(id,'attempt_correctness_reported',{attempt_event_id:a.id,adequate:false}))}>Not yet</button></>}</div></div>)}
  <label className="field-label" htmlFor="attempt">{attempts.length?'Add another thought':'What have you tried, or what might work?'}</label><textarea id="attempt" rows={7} maxLength={20000} value={attempt} onChange={e=>setAttempt(e.target.value)} placeholder="I’m thinking that…" disabled={busy}/><label className="checkbox-label"><input type="checkbox" checked={partial} onChange={e=>setPartial(e.target.checked)}/> This is a partial attempt</label><button className="primary" disabled={busy||!attempt.trim()} onClick={()=>action(async()=>{await emitEvent(id,'attempt_submitted',{attempt_text:attempt,is_partial:partial});setAttempt('');})}>{busy?'Saving…':'Save my thinking'}<Check size={15}/></button></section>
  <section className="form-card hint-panel"><div className="card-heading"><span className="round-icon"><Lightbulb size={19}/></span><div><h3>A little support</h3><p>You choose how much help you need.</p></div></div>
  <AIConnection selected={unfinishedRequest ? unfinishedRequest.payload.selected_provider || 'auto' : selectedProvider} onSelect={setSelectedProvider} disabled={busy || !!unfinishedRequest || !!hintRequest.current}/>
  {!gatePassed?<AIRequestGate busy={busy} onSkip={()=>action(()=>emitEvent(id,'attempt_skipped',{skip_reason:null}))}/>:<HintLadder hints={hints} busy={busy} blocked={pending.length>0} onRequest={()=>action(()=>requestHint())}/>}
  {hints.length>=3&&<form onSubmit={e=>{e.preventDefault();void action(()=>requestHint(followup.trim()));}}><label htmlFor="followup" className="field-label">Keep the conversation going</label><textarea id="followup" maxLength={5000} rows={3} disabled={busy||!!unfinishedRequest||!!hintRequest.current} value={followup} onChange={e=>{setFollowup(e.target.value);try{localStorage.setItem(`thinkfirst.followup.${id}`,e.target.value);}catch{setError('Your browser could not save this draft. Keep this page open.');}}} placeholder="Ask about a step, try another approach, or explain what is still unclear…"/><button className="secondary" disabled={busy||pending.length>0||!followup.trim()}>{busy?'Thinking…':'Send follow-up'}</button></form>}
  {pending.map(h=><VerificationStep key={h.id} busy={busy} hasAttempt={attempts.length>0} onSave={(matches,justification)=>action(()=>emitEvent(id,'verification_submitted',{hint_event_id:h.id,matches_own_attempt:matches,justification}))} onSkip={()=>action(()=>emitEvent(id,'verification_skipped',{hint_event_id:h.id}))}/>)}</section></div>
  {finishing&&hints.length>0&&!evaluated&&<EvaluationStep busy={busy} onSave={(makes_sense,reasoning)=>action(()=>emitEvent(id,'evaluation_submitted',{makes_sense,reasoning}))} onSkip={()=>action(()=>emitEvent(id,'evaluation_skipped',{}))}/>}
  <div className="finish-bar"><div><strong>Ready to put this thought down?</strong><p>You can finish, or leave it unfinished. Both are part of the process.</p></div><div className="button-row"><button className="text-button" disabled={busy} onClick={()=>action(()=>close('abandoned'))}>Leave unfinished</button><button className="primary" disabled={busy} onClick={()=>{if(hints.length&&(!evaluated||pending.length)){setFinishing(true);if(pending.length)setError('Check or skip each hint above, then add or skip your final reflection.');}else void action(()=>close(hints.length?'solved_with_ai':aiCount?'solved_without_ai_response':'solved_independently'));}}>Finish session <ArrowRight size={15}/></button></div></div>
  <p className="field-help">Leaving through the workspace navigation records this session as unfinished. Closing the browser keeps the session open so you can resume it.</p></>;
}

function AIRequestGate({busy,onSkip}:{busy:boolean;onSkip:()=>void}) {return <div className="gate"><div className="gate-symbol">✧</div><h3>Give your idea a little room.</h3><p>Give it your own shot first — even a rough idea helps. You can skip if you’d rather not.</p><span className="field-help">Save a thought on the left to open the hint ladder.</span><button className="text-button" disabled={busy} onClick={onSkip}>Skip, ask AI now <ArrowRight size={14}/></button><small>Skipping is recorded, just like an attempt.</small></div>;}
function HintLadder({hints,busy,blocked,onRequest}:{hints:LogEvent[];busy:boolean;blocked:boolean;onRequest:()=>void}) {return <div><div className="hint-levels">{['Clarify','Partial','Full'].map((name,i)=><span className={hints.length>=i+1?'delivered':''} key={name}>{i+1} · {name}</span>)}</div>{hints.length===0&&<p className="hint-intro">Start with a question that helps you see the problem differently.</p>}{hints.map(h=><article className="hint-response" key={h.id}><>{h.payload.followup_text&&<p><strong>You:</strong> {h.payload.followup_text}</p>}</><span className="eyebrow">{h.payload.request_kind==='followup'?'FOLLOW-UP / ':'LEVEL '}{h.payload.tier} / {['CLARIFY','PARTIAL','FULL'][h.payload.tier-1]}</span><AnswerContent text={h.payload.hint_text}/></article>)}{hints.length<3&&<button className="secondary" disabled={busy||blocked} onClick={onRequest}>{busy?'Requesting support…':hints.length===0?'Ask for a clarifying hint':'Show a bigger hint'}<ArrowRight size={15}/></button>}{blocked&&<p className="field-help">Check or skip this hint before requesting the next level.</p>}</div>;}
function VerificationStep({busy,hasAttempt,onSave,onSkip}:{busy:boolean;hasAttempt:boolean;onSave:(m:boolean|null,j:string)=>void;onSkip:()=>void}) {
  const [match,setMatch]=useState(hasAttempt?'yes':'none');const [text,setText]=useState('');
  return <form className="reflection-form" onSubmit={e=>{e.preventDefault();onSave(match==='none'?null:match==='yes',text);}}><h4>How does this compare?</h4><p>Does this match what you were thinking? A quick note helps you remember your reasoning later.</p><label className="field-label" htmlFor="match">Compared with your attempt</label><select id="match" value={match} onChange={e=>setMatch(e.target.value)}><option value="yes">It matches</option><option value="no">It differs</option><option value="none">I don’t have an attempt to compare</option></select><label htmlFor="verification" className="field-label">What did you check?</label><textarea id="verification" rows={3} required maxLength={5000} value={text} onChange={e=>setText(e.target.value)} placeholder="The reasoning fits because…"/><div className="button-row"><button className="secondary" disabled={busy||!text.trim()}>Save check</button><button type="button" className="text-button" disabled={busy} onClick={onSkip}>Skip this check</button></div></form>;
}
function EvaluationStep({busy,onSave,onSkip}:{busy:boolean;onSave:(m:boolean,r:string)=>void;onSkip:()=>void}) {
  const [makesSense,setMakesSense]=useState(true);const [reason,setReason]=useState('');
  return <form className="form-card evaluation" onSubmit={e=>{e.preventDefault();onSave(makesSense,reason);}}><span className="eyebrow">ONE LAST REFLECTION</span><h3>Does the AI’s explanation make sense?</h3><label className="field-label" htmlFor="sense">Your evaluation</label><select id="sense" value={String(makesSense)} onChange={e=>setMakesSense(e.target.value==='true')}><option value="true">Yes, it makes sense</option><option value="false">No, I still see a gap</option></select><label htmlFor="reason" className="field-label">Why?</label><textarea id="reason" rows={3} required maxLength={5000} value={reason} onChange={e=>setReason(e.target.value)} placeholder="Here’s how I understand it…"/><div className="button-row"><button className="primary" disabled={busy||!reason.trim()}>Save reflection</button><button type="button" className="text-button" disabled={busy} onClick={onSkip}>Skip reflection</button></div></form>;
}
function SessionSummary({data}:{data:SessionData}) {return <div className="narrow-page"><span className="eyebrow">A THOUGHT, RECORDED</span><h1>A little more perspective.</h1><p className="lead">Your attempts, questions, and reflections are saved together.</p><section className="form-card"><div className="summary-stats"><div><strong>{data.summary.ai_requests}</strong><span>AI requests</span></div><div><strong>{data.events.filter(e=>e.event_type==='attempt_submitted').length}</strong><span>Own attempts</span></div><div><strong>{data.summary.verification_count}</strong><span>Hints verified</span></div></div><p className="status-line">{data.summary.final_status.replaceAll('_',' ')}</p><div className="timeline">{data.events.filter(e=>['session_started','attempt_submitted','ai_hint_delivered','verification_submitted','evaluation_submitted'].includes(e.event_type)).map(e=><article key={e.id}><span className="eyebrow">{e.event_type.replaceAll('_',' ')} · {new Date(e.created_at).toLocaleTimeString()}</span><>{e.payload.followup_text&&<p><strong>You:</strong> {e.payload.followup_text}</p>}</>{e.event_type==='ai_hint_delivered'?<AnswerContent text={e.payload.hint_text}/>:<p>{e.payload.problem_text||e.payload.attempt_text||e.payload.justification||e.payload.reasoning}</p>}</article>)}</div><Link href="/new" className="primary">Start another thought <ArrowRight size={15}/></Link></section></div>;}

