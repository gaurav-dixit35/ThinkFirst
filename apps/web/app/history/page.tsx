'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowUpRight, Feather} from 'lucide-react';
import {api,SessionList} from '@/lib/api';
export default function Page(){
 const [sessions,setSessions]=useState<SessionList|null>(null);const[error,setError]=useState('');const[retry,setRetry]=useState(0);const [filter,setFilter]=useState('all');
 useEffect(()=>{api<SessionList>('/sessions').then(setSessions).catch(e=>setError(e.message));},[retry]);
 return <><div className="page-heading"><div><span className="eyebrow">FOLLOW YOUR THREAD</span><h1>A history of your thinking.</h1><p>Your questions, rough ideas, and moments of clarity. Latest 100 sessions.</p></div><Link href="/new" className="primary">New session <ArrowUpRight size={16}/></Link></div><div className="filter-tabs">{['all','open','closed'].map(f=><button className={filter===f?'selected':''} onClick={()=>setFilter(f)} key={f}>{f==='all'?'All sessions':f==='open'?'In progress':'Completed & unfinished'}</button>)}</div>{error&&<div className="error" role="alert">{error}<button onClick={()=>{setError('');setRetry(v=>v+1);}}>Retry</button></div>}<section className="session-list">{sessions===null?<p className="empty-text">Loading sessions…</p>:sessions.filter(s=>filter==='all'||s.status===filter).length?sessions.filter(s=>filter==='all'||s.status===filter).map(s=><Link href={`/session/${s.id}`} className="session-row" key={s.id}><span className="session-icon"><Feather size={19}/></span><div><strong>{s.problem_text}</strong><small>{s.domain.replace('_',' ')} · {new Date(s.started_at).toLocaleString()}</small></div><span className="status-chip">{s.status==='open'?'In progress':'Closed'}</span><ArrowUpRight size={16}/></Link>):<div className="empty-session"><h3>A fresh page.</h3><p>No sessions in this view yet.</p><Link href="/new">Start a thought →</Link></div>}</section></>;
}
