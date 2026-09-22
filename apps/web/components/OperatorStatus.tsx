'use client';
import {useState} from 'react';
import {api} from '@/lib/api';

type Status = {auth_mode:string;database:string;deletion_requests:{id:string;user_id:string;created_at:string}[]};
export default function OperatorStatus(){
  const [status,setStatus]=useState<Status|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  return <details><summary>Operator support</summary><p>Review deletion requests here. Process them with the documented offline erasure command after stopping every API instance.</p><button className="secondary" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{setStatus(await api<Status>('/operator/status'));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}}>{busy?'Loading…':'Refresh operator status'}</button>{status&&<><p>Database {status.database} · Authentication {status.auth_mode}</p>{status.deletion_requests.length===0?<p>No pending deletion requests.</p>:<ul>{status.deletion_requests.map(request=><li key={request.id}><p>Requested {new Date(request.created_at).toLocaleString()}</p><p>Request: <code>{request.id}</code><br/>Account: <code>{request.user_id}</code></p></li>)}</ul>}</>}{error&&<p role="alert">{error}</p>}</details>;
}
