import {QuestionTracking} from '@/lib/api';

export default function ThinkingActivity({data}:{data?:QuestionTracking|null}){
 if(!data)return null;
 return <details className="thinking-activity"><summary>Thinking activity in this conversation</summary>
  <p className="field-help">Each typed follow-up is a question turn, even if it continues the same topic. These are saved actions and your verification reports, not grades or a measure of ability.</p>
  <ol>{data.questions.map(q=><li key={q.id}><a href={`#message-${q.id}`}>{q.text.length>160?q.text.slice(0,160)+'…':q.text}</a>
   <p>{q.attempt_before_first_request==null?'No AI request recorded for this turn.':q.attempt_before_first_request?'You saved an attempt before the first AI request.':'No saved attempt preceded the first AI request.'}</p>
   <p>{q.attempts} saved attempts · {q.requests.answer} answer requests · {q.requests.hint} hint requests · {q.requests.check_thinking} thinking checks · {q.requests.exercise} exercise requests</p>
   <p className="field-help">Reported checks: {q.verification.checked} checked · {q.verification.found_issue} problems found · {q.verification.not_checked} marked not checked. Responses without a report are unreported.</p>
  </li>)}</ol>
 </details>;
}
