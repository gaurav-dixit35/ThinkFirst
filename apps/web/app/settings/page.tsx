'use client';
import {useState} from 'react';
import Link from 'next/link';
import {UserRound,SlidersHorizontal,ShieldCheck,LifeBuoy,Sparkles} from 'lucide-react';
import {useIdentity} from '@/components/Providers';
import {api} from '@/lib/api';
import {flushQueue,queueStatus} from '@/lib/eventClient';
import AISetup from '@/components/AISetup';
import LanguagePreferences from '@/components/LanguagePreferences';
import OperatorReports from '@/components/OperatorReports';
import PracticePreferences from '@/components/PracticePreferences';
import DataControls from '@/components/DataControls';
import OperatorStatus from '@/components/OperatorStatus';
import AccountSettings from '@/components/AccountSettings';
import AnswerPreferences from '@/components/AnswerPreferences';
import UsageSettings from '@/components/UsageSettings';

export default function Page(){
  const identity=useIdentity();
  const [status,setStatus]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[advanced,setAdvanced]=useState(false);
  async function check(sync=false){
    setBusy(true);setError('');setStatus('');
    try{if(sync)await flushQueue();const h=await api<{database:string}>('/health');const queue=queueStatus();if(queue.error)throw new Error(queue.error);setStatus(`Database ${h.database}. ${queue.count?`${queue.count} unsent events on this device.`:'All queued work on this device is synced.'}`);}
    catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  return <div className="settings-page">
    <header className="settings-heading"><span className="eyebrow">MAKE THINKFIRST YOURS</span><h1>Your space. Your pace.</h1><p>Manage your account, the help you get, and what you share.</p></header>
    <nav className="settings-nav" aria-label="Settings sections"><a href="#account">Account</a><a href="#preferences">Preferences</a><a href="#allowance">AI allowance</a><a href="#privacy">Privacy</a><a href="#support">Help</a></nav>
    <div className="settings-grid">
      <section className="settings-card" id="account"><h2><UserRound size={20}/>Your account</h2><AccountSettings/></section>
      <section className="settings-card" id="preferences"><h2><SlidersHorizontal size={20}/>How AI helps you</h2><AnswerPreferences/><LanguagePreferences/><PracticePreferences/></section>
      <section className="settings-card" id="allowance"><h2><Sparkles size={20}/>Your AI allowance</h2><UsageSettings/></section>
      <section className="settings-card" id="privacy"><h2><ShieldCheck size={20}/>Privacy and saved work</h2><DataControls/></section>
      <section className="settings-card settings-wide" id="support"><h2><LifeBuoy size={20}/>Help and connection</h2>
        <p><Link href="/support">Report a problem</Link> · <Link href="/help">Help and contact support</Link> · <Link href="/privacy">Read the privacy notice</Link></p>
        <div className="settings-actions"><button className="secondary" disabled={busy} onClick={()=>void check()}>Check connection</button><button className="secondary" disabled={busy} onClick={()=>void check(true)}>Sync saved work</button><Link className="text-button" href="/history">Find a conversation</Link></div>
        {status&&<p role="status">{status}</p>}{error&&<p role="alert">{error}</p>}
        <details><summary>How do Ask AI and Try myself work?</summary><p>Ask AI gets an answer straight away. Try myself gives you space to save an idea, ask for a hint, or see an explanation. Help buttons follow your current question, even if you changed subjects earlier in the chat.</p></details>
        <details><summary>What do my progress graphs mean?</summary><p>Graphs show saved activity over time, not intelligence or a grade. Guided study sessions have additional verification measures and are kept separate from everyday chats.</p><Link href="/dashboard">See your progress</Link></details>
        <details><summary>What if an answer is wrong?</summary><p>AI can make mistakes. Use Not helpful below the answer, describe the issue in a follow-up, and check important advice against a reliable source. Feedback is saved; it does not automatically retrain a model.</p></details>
        <details><summary>What if I lose my connection?</summary><p>Keep this browser profile to preserve drafts and unsent work. Reconnect and choose Sync saved work. A pending AI request resumes with the same request ID rather than starting another paid generation.</p></details>
      </section>
    </div>
    {(identity?.development||identity?.admin)&&<details className="settings-card settings-advanced" onToggle={e=>setAdvanced(e.currentTarget.open)}><summary>Workspace administration</summary>{advanced&&<><AISetup/><OperatorStatus/><OperatorReports/>{identity?.admin&&<Link className="secondary" href="/research">Research exports</Link>}</>}</details>}
  </div>;
}
