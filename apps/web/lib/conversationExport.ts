import {SessionData} from './api';
export function conversationMarkdown(data:SessionData){
 const lines=[`# ${data.title||'ThinkFirst conversation'}`, '', `Conversation: ${data.id}`, '', 'Exported saved work. AI responses may contain mistakes.', ''];
 for(const event of data.events){
  const p=event.payload;
  let label='',text='';
  if(event.event_type==='session_started'){label='You';text=p.problem_text;}
  else if(event.event_type==='ai_hint_requested'&&p.followup_text&&!p.regenerate_of){label='You';text=p.followup_text;}
  else if(event.event_type==='attempt_submitted'){label='Your thinking';text=p.attempt_text;}
  else if(event.event_type==='ai_hint_delivered'){label=p.tier<3?'ThinkFirst hint':'ThinkFirst';text=p.hint_text;}
  else if(event.event_type==='learning_attempt_submitted'){label=`Your later retry (answer ${p.answer_event_id})`;text=p.attempt_text;}
  else if(event.event_type==='ai_hint_failed'){label='Request status';text=p.reason;}
  if(text)lines.push(`## ${label}`, '', String(text), '');
 }
 return lines.join('\n');
}
export function downloadConversation(data:SessionData){
 const url=URL.createObjectURL(new Blob([conversationMarkdown(data)],{type:'text/markdown;charset=utf-8'}));
 try{const link=document.createElement('a');link.href=url;link.download=`thinkfirst-${data.id}.md`;document.body.appendChild(link);link.click();link.remove();}finally{setTimeout(()=>URL.revokeObjectURL(url),10000);}
}
