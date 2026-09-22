'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {ArrowUpRight,Search} from 'lucide-react';
import {api,HistoryPage} from '@/lib/api';

export default function Page(){
  const [data,setData]=useState<HistoryPage|null>(null);
  const [query,setQuery]=useState(''),[search,setSearch]=useState('');
  const [status,setStatus]=useState('all'),[experience,setExperience]=useState('all');
  const [offset,setOffset]=useState(0),[retry,setRetry]=useState(0);
  const [busy,setBusy]=useState(true),[error,setError]=useState('');
  useEffect(()=>{
    let current=true;setBusy(true);setError('');
    const params=new URLSearchParams({q:search,status,experience,offset:String(offset),limit:'25'});
    void api<HistoryPage>(`/history?${params}`).then(value=>{if(current)setData(value);}).catch(e=>{if(current)setError(e.message);}).finally(()=>{if(current)setBusy(false);});
    return()=>{current=false;};
  },[search,status,experience,offset,retry]);
  return <section className="history-page"><div className="page-heading"><div><h1>Your conversations</h1><p>Find a question, an answer, or an idea you saved.</p></div><Link href="/new" className="primary">New conversation <ArrowUpRight size={16}/></Link></div>
    <form className="history-search" onSubmit={e=>{e.preventDefault();setOffset(0);setSearch(query.trim());}}><label className="sr-only" htmlFor="history-search">Search conversations</label><input id="history-search" type="search" maxLength={200} value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search titles, questions, answers, or your thinking"/><button className="secondary" type="submit"><Search size={16}/>Search</button>{search&&<button className="text-button" type="button" onClick={()=>{setQuery('');setSearch('');setOffset(0);}}>Clear search</button>}</form>
    <div className="history-filters"><label>Status <select value={status} onChange={e=>{setStatus(e.target.value);setOffset(0);}}><option value="all">All statuses</option><option value="open">In progress</option><option value="completed">Completed</option><option value="abandoned">Left unfinished</option></select></label><label>Conversation type <select value={experience} onChange={e=>{setExperience(e.target.value);setOffset(0);}}><option value="all">All conversations</option><option value="chat">Everyday chats</option><option value="guided">Guided study sessions</option></select></label></div>
    {error&&<div className="error" role="alert">{error}<button onClick={()=>setRetry(n=>n+1)}>Retry history</button></div>}
    {busy?<p role="status" className="empty-text">Finding your conversations…</p>:!error&&data&&<>
      <p className="history-count" role="status">{data.total} {data.total===1?'conversation':'conversations'}{search?` matching “${search}”`:''}</p>
      <div className="session-list">{data.items.length?data.items.map(item=><Link className="session-row history-row" key={item.id} href={`/session/${item.id}`}><div><strong>{item.title}</strong>{item.custom_title&&<p className="history-preview">{item.problem_text}</p>}<small>{item.domain.replaceAll('_',' ')} · {new Date(item.started_at).toLocaleDateString()} · {item.experience==='chat'?'Everyday chat':'Guided study'}</small></div><span className={`status-chip ${item.status==='open'?'open':''}`}>{item.status_label}</span><ArrowUpRight size={16}/></Link>) :<div className="empty-session"><h3>{search?'No matching conversations':'Nothing here yet'}</h3><p>{search?'Try a different phrase or clear your filters.':'Your saved conversations will appear here.'}</p></div>}</div>
      <nav className="history-pagination" aria-label="History pages"><button className="secondary" disabled={offset===0} onClick={()=>setOffset(Math.max(0,offset-25))}>Previous</button><span>Page {Math.floor(offset/25)+1} of {Math.max(1,Math.ceil(data.total/25))}</span><button className="secondary" disabled={!data.has_more} onClick={()=>setOffset(offset+25)}>Next</button></nav>
    </>}
  </section>;
}
