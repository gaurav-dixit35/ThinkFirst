'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {api,ProgressData} from '@/lib/api';
import ProgressCharts from './ProgressCharts';
import SavedProgress from './SavedProgress';
import LearningGoal from './LearningGoal';

export default function Progress(){
  const [experience,setExperience]=useState<'chat'|'guided'>('chat');
  const [data,setData]=useState<ProgressData|null>(null),[error,setError]=useState('');
  const [retry,setRetry]=useState(0);
  useEffect(()=>{let current=true;setData(null);setError('');void api<ProgressData>(`/progress?experience=${experience}`).then(value=>{if(current)setData(value);}).catch(e=>{if(current)setError(e.message);});return()=>{current=false;};},[experience,retry]);
  return <section className="progress-page"><div className="page-heading"><div><h1>Your activity, in perspective</h1><p>A record of what you saved and explored. These counts are not a score of your ability.</p></div></div>
    <label className="progress-selector">Show activity for <select value={experience} onChange={e=>setExperience(e.target.value as 'chat'|'guided')}><option value="chat">Everyday chats</option><option value="guided">Guided study sessions</option></select></label>
    {error&&<div className="error" role="alert">{error}<button onClick={()=>setRetry(n=>n+1)}>Retry progress</button></div>}
    {!data&&!error&&<p role="status">Loading your activity…</p>}
    {data&&<><p className="progress-summary">{data.totals.conversations?`Across ${data.totals.conversations} ${experience==='chat'?'everyday conversations':'guided study sessions'}, you saved ${data.totals.own_attempts} independent attempts and received ${data.totals.ai_answers} AI answers.`:'There is no saved activity in this view yet. Start with a question or an idea of your own.'}</p>
      <div className="metric-grid">{[['Conversations',data.totals.conversations],['Your saved attempts',data.totals.own_attempts],['AI answers received',data.totals.ai_answers],['Completed by you',data.totals.completed]].map(([label,value])=><article className="metric-card" key={label}><span className="metric-label">{label}</span><strong>{value}</strong><small>All time · {experience==='chat'?'everyday chats':'guided study'}</small></article>)}</div>
      <p className="field-help progress-caption">{data.totals.in_progress} in progress · {data.totals.unfinished} left unfinished · {data.totals.failed_requests} unsuccessful AI requests. Completion is self-reported, not a correctness check.</p>
      <ProgressCharts data={data}/>
      {experience==='chat'&&<><LearningGoal/><SavedProgress/></>}
      <div className="progress-sections"><section className="form-card"><h2>How you worked</h2><p className="field-help">Conversations grouped by saved attempts and delivered answers.</p><dl className="activity-breakdown">{[['Your attempts and AI answers',data.modes.both],['Your attempts only',data.modes.own_only],['AI answers only',data.modes.ai_only],['No attempt or answer saved yet',data.modes.no_saved_work]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section>
      <section className="form-card"><h2>Recent activity</h2><p className="field-help">This week and the previous three weeks, in UTC. The current week is still in progress.</p><table className="activity-table"><caption className="sr-only">Weekly saved attempts and delivered AI answers</caption><thead><tr><th scope="col">Week starting</th><th scope="col">Your attempts</th><th scope="col">AI answers</th></tr></thead><tbody>{data.weeks.map(week=><tr key={week.week}><th scope="row">{week.week}</th><td>{week.own_attempts}</td><td>{week.ai_answers}</td></tr>)}</tbody></table></section></div>
      <section className="progress-review-note"><h2>Look back at one conversation</h2><p>Each chat includes a factual activity summary. You can also request an optional AI review there; it uses your AI allowance. Nothing is generated automatically.</p><Link className="secondary" href="/history">Open history</Link></section>
      <p className="field-help">{data.totals.ai_reviews} saved AI reviews are counted separately from answers. Updated {new Date(data.updated_at).toLocaleString()}.</p>
    </>}
  </section>;
}
