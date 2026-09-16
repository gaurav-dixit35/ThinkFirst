'use client';
import {useEffect,useRef,useState} from 'react';
import {api,ApiError,PracticeState} from '@/lib/api';
import {useIdentity} from './Providers';

type Decision = {event_id:string;session_id:string;event_type:'practice_invitation_responded';payload:{answer_event_id:string;decision:'try_myself'|'continue_ai'}};

export default function PracticeSupport({id,practice,paused,reload}:{id:string;practice?:PracticeState;paused:boolean;reload:()=>Promise<void>}) {
  const identity=useIdentity();
  const anchor=practice?.answer_event_id;
  const key=identity&&anchor?`thinkfirst.practice.${identity.id}.${id}.${anchor}`:null;
  const [checked,setChecked]=useState<string|null>(null);
  const [dismissed,setDismissed]=useState(false);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const pending=useRef<Decision|null>(null);
  const working=useRef(false);
  useEffect(()=>{
    pending.current=null;setError('');setDismissed(false);
    if(key){
      try {
        const saved=localStorage.getItem(key);
        if(saved){setDismissed(true);if(saved!=='dismissed'){pending.current=JSON.parse(saved);setError('Your practice choice is saved on this device. Retry to sync it.');}}
      }catch { /* In-memory dismissal still works when storage is unavailable. */ }
    }
    setChecked(key);
  },[key]);
  async function save(decision?:'try_myself'|'continue_ai') {
    if(working.current||!anchor)return;
    working.current=true;setBusy(true);setError('');setDismissed(true);
    if(decision)pending.current={event_id:crypto.randomUUID(),session_id:id,event_type:'practice_invitation_responded',payload:{answer_event_id:anchor,decision}};
    const request=pending.current;
    try {if(key&&request)localStorage.setItem(key,JSON.stringify(request));} catch { /* Keep the choice in memory. */ }
    try {
      if(request)await api('/events',request);
      pending.current=null;
      try {if(key)localStorage.setItem(key,'dismissed');}catch { /* The server decision is durable. */ }
      await reload();
    }catch(e){
      if(e instanceof ApiError && [400,404,409].includes(e.status)){
        pending.current=null;
        try {if(key)localStorage.setItem(key,'dismissed');}catch { /* No required queue is affected. */ }
        setError('That invitation has changed. You can still use Try myself anytime.');
        void reload().catch(()=>{});
      }else setError('Your choice could not sync. You can keep chatting or choose Try myself.');
    }finally{working.current=false;setBusy(false);}
  }
  async function disable() {
    if(working.current)return;
    working.current=true;setBusy(true);setError('');
    try{await api('/preferences',{practice_reminders:false});setDismissed(true);await reload();}
    catch{setError('Reminders could not be turned off. Please retry when connected.');}
    finally{working.current=false;setBusy(false);}
  }
  if(!practice)return null;
  if(practice.active)return <aside className="practice-task" aria-label="Practice step"><strong>A small step of your own</strong><p>{practice.task}</p><details><summary>Question to revisit</summary><p>{practice.question}</p></details><p className="field-help">Use the space below. A rough idea is enough; you can return to Ask AI anytime.</p></aside>;
  if(paused||!practice.eligible||!key||checked!==key)return null;
  return <>
    {!dismissed&&<aside className="practice-invitation" aria-label="Optional practice invitation"><div><strong>Want to try a little thinking of your own?</strong><p>You’ve explored a few AI answers. Try one step yourself, or keep chatting—it’s your choice.</p></div><div className="button-row"><button className="secondary" disabled={busy} onClick={()=>void save('try_myself')}>Yes, I’ll try</button><button className="text-button" disabled={busy} onClick={()=>void save('continue_ai')}>No, keep chatting</button><button className="text-button" disabled={busy} onClick={()=>void disable()}>Turn off reminders</button></div></aside>}
    {error&&<div className="optional-save-note" role="status">{error}{pending.current&&<button className="text-button" disabled={busy} onClick={()=>void save()}>Retry practice choice</button>}</div>}
  </>;
}
