'use client';
import {useState} from 'react';
import {useRouter} from 'next/navigation';
import {ArrowRight, Code2, Hash, PenLine, Shapes} from 'lucide-react';
import {api, ApiError} from '@/lib/api';
export default function ProblemIntake() {
  const [domain, setDomain] = useState('general_reasoning');
  const [problem, setProblem] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [request, setRequest] = useState<{event_id:string; problem_domain:string; problem_text:string} | null>(null);
  const router = useRouter();
  async function start() {
    setBusy(true);setError('');
    const body = request || {event_id: crypto.randomUUID(), problem_domain: domain, problem_text: problem};
    setRequest(body);
    try {const result = await api<{id:string}>('/sessions',body);router.push(`/session/${result.id}`);}
    catch(e) {setError((e as Error).message);if(e instanceof ApiError && e.status>=400 && e.status<500 && e.status!==409)setRequest(null);setBusy(false);}
  }
  return <div className="narrow-page"><div className="eyebrow">01 / MAKE A LITTLE ROOM</div><h1>What’s on your mind?</h1><p className="lead">A tricky problem, an idea to untangle, a question worth exploring.</p><form className="form-card" onSubmit={e=>{e.preventDefault();void start();}}><label className="field-label">Choose a space</label><div className="domain-grid">{[{id:'coding',name:'Coding',Icon:Code2},{id:'math',name:'Math',Icon:Hash},{id:'writing',name:'Writing',Icon:PenLine},{id:'general_reasoning',name:'Everyday reasoning',Icon:Shapes}].map(({id,name,Icon})=><button disabled={busy || !!request} className={`domain-button ${domain===id?'selected':''}`} type="button" key={id} onClick={()=>setDomain(id)}><Icon size={20}/>{name}</button>)}</div><label htmlFor="problem" className="field-label">The problem or question</label><textarea id="problem" required maxLength={20000} rows={7} value={problem} disabled={busy || !!request} onChange={e=>setProblem(e.target.value)} placeholder="What would you like to work through? Include any details or constraints that matter."/><p className="field-help">Your problem, attempts, and reflections are saved for behavioral research. Avoid including sensitive personal information.</p>{error && <div role="alert" className="error">{error}</div>}<div className="form-actions"><span>You set the pace.</span><button className="primary" disabled={busy || !problem.trim()}>{busy?'Opening your space…':request?'Retry opening session':'Start thinking'}<ArrowRight size={16}/></button></div></form></div>;
}
