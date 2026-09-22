'use client';
import {useState} from 'react';
import {api} from '@/lib/api';

export default function ConversationTitle({id,title,custom,reload}:{id:string;title?:string;custom?:boolean;reload:()=>Promise<void>}){
  const [editing,setEditing]=useState(false),[busy,setBusy]=useState(false);
  const [draft,setDraft]=useState(''),[error,setError]=useState('');
  async function save(value:string|null){setBusy(true);setError('');try{await api(`/sessions/${id}/title`,{title:value});await reload();setEditing(false);}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  return <div className="conversation-title">{editing?<form onSubmit={e=>{e.preventDefault();if(draft.trim())void save(draft.trim());}}><label htmlFor="conversation-title">Conversation title</label><input id="conversation-title" autoFocus maxLength={100} value={draft} disabled={busy} onChange={e=>setDraft(e.target.value)}/><div className="button-row"><button className="secondary" disabled={busy||!draft.trim()}>Save title</button><button type="button" className="text-button" disabled={busy} onClick={()=>setEditing(false)}>Cancel</button>{custom&&<button type="button" className="text-button" disabled={busy} onClick={()=>void save(null)}>Use original title</button>}</div></form>:<><h1>{title||'Your conversation'}</h1><button type="button" className="text-button rename-button" onClick={()=>{setDraft(title||'');setError('');setEditing(true);}}>Rename</button></>}{error&&<p role="alert">{error}</p>}</div>;
}
