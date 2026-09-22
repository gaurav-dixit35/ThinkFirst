'use client';
import {useEffect,useState} from 'react';
import {api} from '@/lib/api';
export default function AnswerPreferences(){
  const [style,setStyle]=useState<'concise'|'detailed'|null>(null),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  async function load(){try{const data=await api<{answer_style:'concise'|'detailed'}>('/preferences/answers');setStyle(data.answer_style);setError('');}catch(e){setError((e as Error).message);}}
  useEffect(()=>{void load();},[]);
  return <div className="answer-preferences"><h3>Default answer length</h3><p>Start with a quick answer or a fuller explanation. You can still change the length inside any conversation.</p><label htmlFor="default-answer-length">Answer length</label><select id="default-answer-length" value={style||'concise'} disabled={busy||style===null} onChange={async e=>{const previous=style;const next=e.target.value as 'concise'|'detailed';setStyle(next);setBusy(true);setError('');setMessage('');try{const saved=await api<{answer_style:'concise'|'detailed'}>('/preferences/answers',{answer_style:next});setStyle(saved.answer_style);setMessage('Default saved for conversations you open next.');}catch(e){setStyle(previous);setError((e as Error).message);}finally{setBusy(false);}}}><option value="concise">Concise · Just what I need</option><option value="detailed">Detailed · Steps and examples</option></select>{busy&&<p role="status">Saving…</p>}{message&&<p role="status">{message}</p>}{error&&<p role="alert">{error}{style===null&&<button className="text-button" onClick={load}>Retry answer preference</button>}</p>}</div>;
}
