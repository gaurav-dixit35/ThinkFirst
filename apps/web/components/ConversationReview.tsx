'use client';
import {useEffect,useRef,useState} from 'react';
import {SessionData} from '@/lib/api';
import {completeReview,reviewKey,ReviewRequest} from '@/lib/aiRequest';
import {flushQueue} from '@/lib/eventClient';
import AnswerContent from './AnswerContent';

export default function ConversationReview({data,reload}:{data:SessionData;reload:()=>Promise<void>}){
  const summary=data.overview;
  const reviews=data.events.filter(e=>e.event_type==='ai_analysis_delivered');
  const latest=reviews.at(-1);
  const unfinished=data.events.find(e=>e.event_type==='ai_analysis_requested'&&!data.events.some(r=>['ai_analysis_delivered','ai_analysis_failed'].includes(r.event_type)&&r.payload.request_event_id===e.id));
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[opened,setOpened]=useState(false);
  const working=useRef(false),restored=useRef(false);
  function saved():ReviewRequest|null{const value=localStorage.getItem(reviewKey(data.id));if(!value)return null;const request=JSON.parse(value);return request.session_id===data.id?request:null;}
  async function run(request?:ReviewRequest,resume=false){
    if(working.current)return;
    working.current=true;setBusy(true);setError('');setOpened(true);
    try{
      // Include already queued participant work before taking a review snapshot.
      if(!resume&&data.status==='open')await flushQueue(data.id);
      const prior=request||saved()||(unfinished?{event_id:unfinished.id,session_id:data.id}:null);
      await completeReview(prior||{event_id:crypto.randomUUID(),session_id:data.id},resume||!!prior);
      await reload();
    }catch(e){setError((e as Error).message);try{await reload();}catch{/* Keep the recoverable request ID. */}}
    finally{working.current=false;setBusy(false);}
  }
  useEffect(()=>{
    if(restored.current||!summary)return;
    restored.current=true;
    try{const request=unfinished?{event_id:unfinished.id,session_id:data.id}:saved();if(request)void run(request,true);}
    catch{setError('Your pending review could not be restored. Your conversation is saved.');}
  },[]);
  useEffect(()=>{const online=()=>{try{const request=saved();if(request)void run(request,true);}catch{/* Manual retry is available. */}};window.addEventListener('online',online);return()=>window.removeEventListener('online',online);},[data.id]);
  if(!summary)return null;
  const stale=latest&&latest.payload.source_fingerprint!==summary.fingerprint;
  return <details className="conversation-review" open={opened} onToggle={e=>setOpened(e.currentTarget.open)}><summary>Review this conversation</summary>
    <div className="review-body"><h2>Your saved activity</h2><p>{summary.own_attempts} own attempts · {summary.ai_answers} AI answers · {summary.failed_requests} unsuccessful requests</p><p className="field-help">{summary.status_label}. These are saved actions, not a measure of ability or correctness.</p>
      <h2>Optional AI review</h2><p className="field-help">Get a short review of what you explored, your contribution, and a possible next step. Generating a review uses one AI request. It can miss details or make mistakes.</p>
      {latest&&<div className="saved-review"><p className="field-help">Saved {new Date(latest.created_at).toLocaleString()}{latest.payload.excerpts_truncated?' · Based on limited excerpts':''}</p><AnswerContent text={latest.payload.text}/>{stale&&<p className="review-stale">There is newer activity since this review.</p>}</div>}
      {busy&&<p role="status">Preparing your review… You can keep using your conversation.</p>}
      {error&&<p className="error" role="alert">{error}</p>}
      {(!latest||stale||error||unfinished)&&<button className="secondary" disabled={busy||!summary.can_review} onClick={()=>void run()}>{error?'Retry review':unfinished?'Check pending review':latest?'Review new activity':'Generate AI review'}</button>}
      {!summary.can_review&&<p className="field-help">Save an attempt or get an answer first.</p>}
    </div>
  </details>;
}
