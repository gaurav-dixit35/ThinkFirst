'use client';
import {CartesianGrid,Legend,Line,LineChart,ResponsiveContainer,Tooltip,XAxis,YAxis} from 'recharts';
import {ProgressData} from '@/lib/api';
import Patterns from './dashboard/Patterns';

export default function ProgressCharts({data}:{data:ProgressData}){
  return <section className="progress-charts" aria-label="Progress graphs">
    <section className="chart-card activity-chart"><h2>Your thinking and AI, over time</h2><p>Saved attempts and delivered answers each week. The current week is incomplete.</p>
      {data.weeks.some(w=>w.own_attempts||w.ai_answers)?<div role="img" aria-label="Line chart of weekly saved attempts and AI answers; exact values are in the Recent activity table below."><ResponsiveContainer width="100%" height={260}><LineChart data={data.weeks} margin={{top:16,right:20,left:-15,bottom:5}}><CartesianGrid strokeDasharray="3 5" vertical={false}/><XAxis dataKey="week" tick={{fontSize:11}}/><YAxis allowDecimals={false} tick={{fontSize:11}}/><Tooltip/><Legend/><Line type="linear" dataKey="own_attempts" name="Your attempts" stroke="#60784c" strokeWidth={3} dot={{r:4}} isAnimationActive={false}/><Line type="linear" dataKey="ai_answers" name="AI answers" stroke="#9c6d47" strokeWidth={2} strokeDasharray="5 3" dot={{r:4}} isAnimationActive={false}/></LineChart></ResponsiveContainer></div>:<div className="chart-empty">Your saved attempts and AI replies will appear here. No activity is invented.</div>}
    </section>
    <Patterns data={{trend:data.trend||[]}} guided={data.experience==='guided'}/>
    <p className="field-help">The smaller charts group conversations by their starting week. AI-first means AI was requested before a saved attempt. Time before asking AI measures elapsed time, not attention or ability.{data.experience==='guided'?' Verification counts explicit checks in guided sessions.':''}</p>
    {!!data.trend?.length&&<details className="chart-data"><summary>View exact trend values</summary><div className="table-scroll"><table className="activity-table"><thead><tr><th scope="col">Starting week</th><th scope="col">AI first</th>{data.experience==='guided'&&<th scope="col">Verified answers</th>}<th scope="col">Seconds before AI</th></tr></thead><tbody>{data.trend.map(row=><tr key={row.week}><th scope="row">{row.week}</th><td>{row.ai_first_ratio==null?'—':`${Math.round(row.ai_first_ratio*100)}%`}</td>{data.experience==='guided'&&<td>{row.verification_rate==null?'—':`${Math.round(row.verification_rate*100)}%`}</td>}<td>{row.time_to_ai_seconds==null?'—':row.time_to_ai_seconds.toFixed(1)}</td></tr>)}</tbody></table></div></details>}
  </section>;
}
