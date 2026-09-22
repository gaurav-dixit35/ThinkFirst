'use client';
import {useEffect, useState} from 'react';
import {api} from '@/lib/api';

export default function SupportContact() {
  const [info, setInfo] = useState<{operator:string|null; support_email:string|null}|null>(null);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    api<{operator:string|null; support_email:string|null}>('/service-info')
      .then(value => {if(active) setInfo(value);})
      .catch(() => {if(active) setFailed(true);});
    return () => {active = false;};
  }, [retry]);
  return <section><h2>Contact support</h2>{info?.support_email ? <p>{info.operator && `${info.operator} · `}<a href={`mailto:${info.support_email}`}>{info.support_email}</a></p> : failed ? <p>Contact details could not be loaded. <button className="text-button" onClick={()=>{setFailed(false);setRetry(n=>n+1);}}>Try again</button></p> : info ? <p>A support contact has not been configured for this workspace yet.</p> : <p>Loading contact details…</p>}<p>Include the approximate time and the error reference, if shown. Never send passwords, API keys, or your full private conversation.</p></section>;
}
