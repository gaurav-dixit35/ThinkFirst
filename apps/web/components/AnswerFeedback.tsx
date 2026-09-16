'use client';
import {useRef,useState} from 'react';
import {ThumbsDown,ThumbsUp} from 'lucide-react';
import {api} from '@/lib/api';

export type Rating='helpful'|'not_helpful'|'cleared';
export default function AnswerFeedback({sessionId,answerId,rating,reload}:{sessionId:string;answerId:string;rating?:Rating;reload:()=>Promise<void>}){
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const pending=useRef<{event_id:string;session_id:string;event_type:string;payload:{answer_event_id:string;rating:Rating}}|null>(null);
  const working=useRef(false);
  async function save(next?:Rating){
    if(working.current)return;
    working.current=true;setBusy(true);setError('');
    if(next)pending.current={event_id:crypto.randomUUID(),session_id:sessionId,event_type:'answer_feedback',payload:{answer_event_id:answerId,rating:next===rating?'cleared':next}};
    try{if(pending.current)await api('/events',pending.current);pending.current=null;await reload();}
    catch{setError('Feedback did not sync. Your conversation is unaffected.');}
    finally{working.current=false;setBusy(false);}
  }
  return <div className="answer-feedback" role="group" aria-label="Answer feedback"><span>Was this helpful?</span>
    <button title="Helpful" aria-label="Helpful" aria-pressed={rating==='helpful'} disabled={busy} onClick={()=>void save('helpful')}><ThumbsUp size={14}/></button>
    <button title="Not helpful" aria-label="Not helpful" aria-pressed={rating==='not_helpful'} disabled={busy} onClick={()=>void save('not_helpful')}><ThumbsDown size={14}/></button>
    <span className="field-help" role="status">{busy?'Saving…':error|| (rating&&rating!=='cleared'?'Feedback saved':'')}{error&&<button className="text-button" disabled={busy} onClick={()=>void save()}>Retry feedback</button>}</span>
  </div>;
}
