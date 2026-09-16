'use client';
import {useEffect,useRef,useState} from 'react';
import {api} from '@/lib/api';

export default function PracticePreferences(){
  const [enabled,setEnabled]=useState<boolean|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const working=useRef(false);
  const version=useRef(0);
  async function load(){
    if(working.current)return;
    const current=++version.current;
    try{const saved=await api<{practice_reminders:boolean}>('/preferences');if(current===version.current){setEnabled(saved.practice_reminders);setError('');}}
    catch{if(current===version.current)setError('Practice preferences could not load.');}
  }
  useEffect(()=>{void load();window.addEventListener('focus',load);return()=>window.removeEventListener('focus',load);},[]);
  async function toggle(){
    if(working.current||enabled===null)return;
    const previous=enabled,next=!enabled;
    version.current++;
    working.current=true;setBusy(true);setError('');
    setEnabled(next);
    try{const saved=await api<{practice_reminders:boolean}>('/preferences',{practice_reminders:next});setEnabled(saved.practice_reminders);}
    catch{setEnabled(previous);setError('Your preference could not be saved. Please try again.');}
    finally{working.current=false;setBusy(false);}
  }
  return <section className="practice-preferences"><h3>Practice reminders</h3><p>Occasionally invite me to try a step myself after several AI answers. Always optional, with no extra AI usage.</p>
    {enabled!==null?<label className="preference-toggle"><input type="checkbox" checked={enabled} disabled={busy} onChange={()=>void toggle()}/>Offer optional practice reminders</label>:<p>Loading preference…</p>}
    <p className="field-help">This preference applies to your account across conversations.</p>
    {busy&&<p className="field-help" role="status">Saving preference…</p>}
    {error&&<p role="status">{error}{enabled===null&&<button className="text-button" onClick={()=>void load()}>Retry preferences</button>}</p>}
  </section>;
}
