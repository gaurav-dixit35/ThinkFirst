'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {api} from '@/lib/api';
import {SavedList,SavedSummary} from '@/lib/learning';
export default function SavedProgress(){
 const [data,setData]=useState<SavedSummary|null>(null),[error,setError]=useState(false),[retry,setRetry]=useState(0);
 useEffect(()=>{let active=true;setError(false);void api<SavedList>('/saved?limit=1').then(value=>{if(active)setData(value.summary);}).catch(()=>{if(active)setError(true);});return()=>{active=false;};},[retry]);
 return <section className="saved-progress"><h2>Questions you came back to</h2>{data?<p>{data.retried} of {data.saved} currently saved questions retried · {data.attempts} saved retry attempts.</p>:error?<p role="alert">Retry activity could not be loaded. <button className="text-button" onClick={()=>setRetry(n=>n+1)}>Retry</button></p>:<p role="status">Loading retry activity…</p>}<p className="field-help">These retries are separate from first attempts in chat. Counts show activity, not correctness or mastery.</p><Link className="secondary" href="/saved">Choose a saved question</Link></section>;
}
