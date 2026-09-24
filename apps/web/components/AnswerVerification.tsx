'use client';
import {useEffect,useId,useRef,useState} from 'react';
import {api,LogEvent} from '@/lib/api';

type Status='checked'|'found_issue'|'not_checked';
type Method='calculation'|'example'|'source'|'reasoning'|'other';
const labels:Record<Status,string>={checked:'I checked it',found_issue:'I found a problem',not_checked:'Not checked'};

export default function AnswerVerification({sessionId,answerId,saved,reload}:{sessionId:string;answerId:string;saved?:LogEvent;reload:()=>Promise<void>}){
 const id=useId();
 const [status,setStatus]=useState<Status>(saved?.payload.status||'not_checked');
 const [method,setMethod]=useState<Method|''>(saved?.payload.method||'');
 const [note,setNote]=useState(saved?.payload.note||''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const working=useRef(false),pending=useRef<{event_id:string;session_id:string;event_type:string;payload:object}|null>(null);
 useEffect(()=>{setStatus(saved?.payload.status||'not_checked');setMethod(saved?.payload.method||'');setNote(saved?.payload.note||'');},[saved?.id]);
 async function save(){
  if(working.current)return;working.current=true;setBusy(true);setError('');setNotice('');
  const payload={answer_event_id:answerId,status,method:status==='not_checked'?null:method,note:note.trim()};
  if(!pending.current||JSON.stringify(pending.current.payload)!==JSON.stringify(payload))pending.current={event_id:crypto.randomUUID(),session_id:sessionId,event_type:'answer_verification_reported',payload};
  try{await api('/events',pending.current);pending.current=null;await reload();setNotice('Verification note saved.');}
  catch(e){setError(`${(e as Error).message} Your note is still here; save again to retry.`);}
  finally{working.current=false;setBusy(false);}
 }
 return <details className="answer-verification"><summary>{saved?`Your verification: ${labels[saved.payload.status as Status]}`:'Check this answer (optional)'}</summary>
  <form onSubmit={e=>{e.preventDefault();void save();}}>
   <p className="field-help">Record your own check. This does not ask AI or certify that the answer is correct.</p>
   <label htmlFor={`${id}-status`}>Did you check this answer?</label><select id={`${id}-status`} value={status} disabled={busy} onChange={e=>{setStatus(e.target.value as Status);setNotice('');}}>{Object.entries(labels).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select>
   {status!=='not_checked'&&<><label htmlFor={`${id}-method`}>How did you check?</label><select id={`${id}-method`} value={method} disabled={busy} required onChange={e=>setMethod(e.target.value as Method)}><option value="">Choose a method</option><option value="calculation">Worked through a calculation</option><option value="example">Tried an example or test</option><option value="source">Compared with a source</option><option value="reasoning">Checked the reasoning</option><option value="other">Another method</option></select></>}
   <label htmlFor={`${id}-note`}>Your verification note (optional)</label><textarea id={`${id}-note`} rows={2} maxLength={2000} disabled={busy} value={note} onChange={e=>setNote(e.target.value)} placeholder="What did you check or notice?"/>
   <button className="secondary" disabled={busy||(status!=='not_checked'&&!method)}>{busy?'Saving…':'Save verification'}</button>
   {notice&&<p role="status">{notice}</p>}{error&&<p role="alert">{error}</p>}
  </form>
 </details>;
}
