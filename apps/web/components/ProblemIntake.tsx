'use client';
import {useState} from 'react';
import {useRouter} from 'next/navigation';
import {ArrowUp, MessageCircle, PenLine} from 'lucide-react';
import {api, ApiError, ConversationMode} from '@/lib/api';
import {requestKey} from '@/lib/aiRequest';

type StartRequest={event_id:string;problem_domain:string;problem_text:string;experience:'chat';initial_mode:ConversationMode};
export default function ProblemIntake() {
  const [mode,setMode]=useState<ConversationMode>('ask_ai');
  const [problem,setProblem]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [request,setRequest]=useState<StartRequest|null>(null);
  const router=useRouter();
  async function start() {
    if(busy)return;
    setBusy(true);setError('');
    const body:StartRequest=request || {event_id:crypto.randomUUID(),problem_domain:'general_reasoning',problem_text:problem.trim(),experience:'chat',initial_mode:mode};
    setRequest(body);
    try {
      const result=await api<{id:string}>('/sessions',body);
      if(body.initial_mode==='ask_ai') {
        // This saved intent comes only from the user's Ask AI action, never a page visit.
        try {if(!localStorage.getItem(requestKey(result.id)))localStorage.setItem(requestKey(result.id),JSON.stringify({event_id:crypto.randomUUID(),session_id:result.id,tier:3,provider:'auto'}));}
        catch { /* The saved conversation offers a manual Get an answer action. */ }
      }
      router.push(`/session/${result.id}`);
    } catch(e) {
      setError((e as Error).message);
      if(e instanceof ApiError&&e.status>=400&&e.status<500&&e.status!==409)setRequest(null);
      setBusy(false);
    }
  }
  return <section className="question-home">
    <img className="home-logo" src="/logo.png" alt="ThinkFirst" width={76} height={76}/>
    <h1>What would you like help with?</h1><p>Ask a question. Try an idea. Find your next step.</p>
    <form className="question-composer" onSubmit={e=>{e.preventDefault();void start();}}>
      <div className="mode-switch" aria-label="How to begin"><button type="button" aria-pressed={mode==='ask_ai'} disabled={busy||!!request} onClick={()=>setMode('ask_ai')}><MessageCircle size={16}/>Ask AI</button><button type="button" aria-pressed={mode==='try_myself'} disabled={busy||!!request} onClick={()=>setMode('try_myself')}><PenLine size={16}/>Try myself</button></div>
      <label className="sr-only" htmlFor="problem">Your question</label><textarea id="problem" required maxLength={20000} rows={5} value={problem} disabled={busy||!!request} onChange={e=>setProblem(e.target.value)} placeholder="Ask anything you want to understand…"/>
      {error&&<div role="alert" className="error">{error}</div>}
      <div className="composer-actions"><span>{mode==='ask_ai'?'Get an answer, then keep the conversation going.':'Start with your own thinking. Help is always available.'}</span><button className="primary" disabled={busy||!problem.trim()}>{busy?'Opening…':request?'Retry':mode==='ask_ai'?'Ask AI':'Start thinking'}<ArrowUp size={16}/></button></div>
    </form>
    <p className="question-privacy">Your conversations are saved. <a href="/settings">About your data</a></p>
  </section>;
}
