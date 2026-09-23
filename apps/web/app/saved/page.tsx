'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {api} from '@/lib/api';
import {emitEvent,flushQueue} from '@/lib/eventClient';
import {SavedList,SavedItem} from '@/lib/learning';

export default function Page(){
 const [data,setData]=useState<SavedList|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const [search,setSearch]=useState(''),[query,setQuery]=useState(''),[unpractised,setUnpractised]=useState(false),[offset,setOffset]=useState(0),[refresh,setRefresh]=useState(0);
 useEffect(()=>{let active=true;setData(null);setError('');void api<SavedList>(`/saved?q=${encodeURIComponent(query)}&unpractised=${unpractised}&offset=${offset}`).then(value=>{if(active)setData(value);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[query,unpractised,offset,refresh]);
 async function remove(item:SavedItem){setBusy(true);setError('');try{await emitEvent(item.session_id,'answer_saved',{answer_event_id:item.answer_id,saved:false});setOffset(0);setRefresh(v=>v+1);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 async function sync(){setBusy(true);try{await flushQueue();setRefresh(v=>v+1);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
 return <section className="learning-page"><header><span className="eyebrow">KEEP WHAT HELPS</span><h1>Saved for another look.</h1><p>Return to a useful answer, or try its question yourself before looking back. No new AI request is needed.</p></header>
 <form className="history-search" onSubmit={e=>{e.preventDefault();setQuery(search.trim());setOffset(0);}}><label className="sr-only" htmlFor="saved-search">Search saved questions and answers</label><input id="saved-search" value={search} onChange={e=>setSearch(e.target.value)} maxLength={200} placeholder="Search saved questions and answers"/><button className="secondary">Search</button>{query&&<button type="button" className="text-button" onClick={()=>{setSearch('');setQuery('');setOffset(0);}}>Clear search</button>}</form>
 <label className="preference-toggle"><input type="checkbox" checked={unpractised} onChange={e=>{setUnpractised(e.target.checked);setOffset(0);}}/>Only questions I haven’t retried</label>
 {error&&<div role="alert" className="error">{error}<button disabled={busy} onClick={()=>void sync()}>Retry sync / refresh</button></div>}
 {!data&&!error&&<p role="status">Loading saved answers…</p>}
 {data&&<><p className="learning-count" role="status">{data.total} matching saved {data.total===1?'answer':'answers'} · {data.summary.retried} saved questions retried · {data.summary.attempts} saved retry attempts</p>
 {!data.items.length?<div className="learning-empty"><h2>{query||unpractised?'Nothing matches this view.':'Keep an answer you want to revisit.'}</h2><p>{query||unpractised?'Try another search or turn off the filter.':'Use Save for later below an AI response in a conversation. It will appear here with its question.'}</p><Link className="secondary" href="/history">Open conversations</Link></div>:<div className="saved-list">{data.items.map(item=><article className="saved-card" key={item.answer_id}><h2><Link href={`/practice/${item.answer_id}`}>{item.question}</Link></h2><p className="field-help">Saved {new Date(item.saved_at).toLocaleDateString()} · {item.attempt_count} retry {item.attempt_count===1?'attempt':'attempts'}</p>{item.deletion_pending&&<p role="status">Conversation awaiting deletion. Read-only until processed.</p>}<div className="button-row"><Link className="primary" href={`/practice/${item.answer_id}`}>{item.deletion_pending?'View saved work':'Retry or view answer'}</Link><Link className="text-button" href={`/session/${item.session_id}#message-${item.answer_id}`}>Open conversation</Link><button className="text-button" disabled={busy||item.deletion_pending} onClick={()=>void remove(item)}>Remove from Saved</button></div></article>)}</div>}
 {(offset>0||data.has_more)&&<nav className="history-pagination" aria-label="Saved answer pages"><button className="secondary" disabled={offset===0||busy} onClick={()=>setOffset(n=>Math.max(0,n-20))}>Previous</button><span>Page {Math.floor(offset/20)+1}</span><button className="secondary" disabled={!data.has_more||busy} onClick={()=>setOffset(n=>n+20)}>Next</button></nav>}
 <p className="field-help">Removing a bookmark keeps the conversation and previous attempts. Conversation deletion also removes its saved answers and retries.</p></>}
 </section>;
}
