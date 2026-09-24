'use client';
import {useCallback, useEffect, useRef, useState} from 'react';
import Link from 'next/link';
import {ArrowUp, Check, Lightbulb, LoaderCircle, MessageCircle, PenLine} from 'lucide-react';
import {api, ApiError, AIUsage, ConversationMode, SessionData} from '@/lib/api';
import {completeHint, HintRequest, requestKey} from '@/lib/aiRequest';
import {emitEvent, flushQueue} from '@/lib/eventClient';
import {useAttemptDraft} from '@/lib/useAttemptDraft';
import GuidedSessionFlow from './GuidedSessionFlow';
import AnswerContent from './AnswerContent';
import AnswerFeedback,{Rating} from './AnswerFeedback';
import PracticeSupport from './PracticeSupport';
import ConversationTitle from './ConversationTitle';
import ConversationReview from './ConversationReview';
import ConversationTools,{EditQuestion} from './ConversationTools';
import AnswerVerification from './AnswerVerification';
import ThinkingActivity from './ThinkingActivity';

export default function SessionFlow({id}:{id:string}) {
  const [data,setData]=useState<SessionData|null>(null);
  const [error,setError]=useState('');
  const reload=useCallback(async()=>{const value=await api<SessionData>(`/sessions/${id}`);setData(value);setError('');},[id]);
  useEffect(()=>{void reload().catch(e=>setError(e.message));},[reload]);
  useEffect(()=>{const refresh=()=>{void reload().catch(()=>{});};window.addEventListener('focus',refresh);return()=>window.removeEventListener('focus',refresh);},[reload]);
  if(!data)return <div className="conversation-page"><h1>Your conversation</h1>{error?<div role="alert" className="error">{error}<button onClick={()=>void reload().catch(e=>setError(e.message))}>Retry</button></div>:<p role="status">Loading your saved conversation…</p>}</div>;
  if(data.experience!=='chat')return <GuidedSessionFlow id={id}/>;
  return <Conversation key={id} data={data} reload={reload}/>;
}

function Conversation({data,reload}:{data:SessionData;reload:()=>Promise<void>}) {
  const id=data.id;
  const [preview,setPreview]=useState(''),[notice,setNotice]=useState(''),[stopping,setStopping]=useState(false);
  const [matches,setMatches]=useState<string[]>([]);
  const mode=data.mode || 'ask_ai';
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [activeRequest,setActiveRequest]=useState<HintRequest|null>(null);
  const [answerStyle,setAnswerStyle]=useState<'concise'|'detailed'>(data.answer_style || 'concise');
  const [allowance,setAllowance]=useState<AIUsage|null>(null);
  const working=useRef(false);
  const recovered=useRef(false);
  const requestRef=useRef<HintRequest|null>(null);
  const closeRef=useRef<{event_id:string;final_status:string}|null>(null);
  const {attempt,setAttempt,storageError}=useAttemptDraft(id);
  const {attempt:message,setAttempt:setMessage,storageError:messageStorageError}=useAttemptDraft(`message.${id}`);
  const messageRef=useRef(message);
  messageRef.current=message;
  const events=data.events;
  const replies=events.filter(e=>e.event_type==='ai_hint_delivered');
  const requests=events.filter(e=>e.event_type==='ai_hint_requested');
  const unfinished=requests.find(e=>!events.some(r=>['ai_hint_delivered','ai_hint_failed'].includes(r.event_type)&&r.payload.request_event_id===e.id));
  const closed=data.status==='closed'||Boolean(data.deletion_pending);
  const attemptInput=useRef<HTMLTextAreaElement>(null);
  useEffect(()=>{if(data.practice?.active&&mode==='try_myself')attemptInput.current?.focus();},[data.practice?.active,mode]);
  const savedAnswers=new Map<string,boolean>();
  events.filter(e=>e.event_type==='answer_saved').forEach(e=>savedAnswers.set(e.payload.answer_event_id,e.payload.saved));
  const feedback=new Map<string,Rating>();
  events.filter(e=>e.event_type==='answer_feedback').forEach(e=>feedback.set(e.payload.answer_event_id,e.payload.rating));
  const verification=new Map(events.filter(e=>e.event_type==='answer_verification_reported').map(e=>[e.payload.answer_event_id,e]));
  const questionId=data.question_tracking?.current_question_event_id;
  const hasCurrentAttempt=events.some(e=>e.event_type==='attempt_submitted'&&questionId&&data.question_tracking?.event_questions[e.id]===questionId);
  useEffect(()=>{
    let current=true;
    void api<AIUsage>('/ai/usage').then(value=>{if(current)setAllowance(value);}).catch(()=>{if(current)setAllowance(null);});
    return ()=>{current=false;};
  },[events.length,busy]);

  function savedRequest():HintRequest|null {
    const stored=localStorage.getItem(requestKey(id));
    if(!stored)return null;
    const value=JSON.parse(stored) as HintRequest;
    return value.session_id===id ? {...value,answer_style:value.answer_style || data.answer_style || 'concise'} : null;
  }
  async function run(work:()=>Promise<unknown>) {
    if(working.current)return;
    working.current=true;setBusy(true);setError('');setNotice('');
    try {await work();await reload();}
    catch(e) {
      if(e instanceof ApiError&&e.status===499)setNotice(e.message);
      else setError(e instanceof ApiError && e.status===502 ? 'AI could not reply right now. Your conversation is saved. Please try again shortly.' : (e as Error).message);
      try {await reload();} catch { /* Keep the action error and local drafts. */ }
    } finally {working.current=false;setBusy(false);}
  }
  async function deliver(request:HintRequest,resume=false) {
    await flushQueue(id);
    request={...request,stream:true};
    requestRef.current=request;setActiveRequest(request);setPreview('');setStopping(false);
    try {
      await completeHint(request,resume,setPreview);
      if(request.followup_text===messageRef.current)setMessage('');
    } finally {
      if(!localStorage.getItem(requestKey(id))) {requestRef.current=null;setActiveRequest(null);}
    }
  }
  useEffect(()=>{
    if(recovered.current || closed)return;
    recovered.current=true;
    try {
      const request:HintRequest|null=unfinished?{event_id:unfinished.id,session_id:id,tier:unfinished.payload.tier_requested,provider:unfinished.payload.selected_provider || undefined,followup_text:unfinished.payload.followup_text || undefined,help_action:unfinished.payload.help_action || undefined,regenerate_of:unfinished.payload.regenerate_of||undefined,stream:true,answer_style:unfinished.payload.answer_style || 'concise'}:savedRequest();
      if(request)void run(()=>deliver(request,Boolean(unfinished)));
    } catch {setError('Your browser could not restore the pending request. Your saved conversation is still available.');}
  },[]);
  useEffect(()=>{
    const reconnect=()=>{
      if(closed || working.current)return;
      void run(async()=>{await flushQueue(id);const request=savedRequest();if(request)await deliver(request,true);});
    };
    window.addEventListener('online',reconnect);
    return ()=>window.removeEventListener('online',reconnect);
  },[closed,id]);
  const transcriptEnd=useRef<HTMLDivElement>(null);
  useEffect(()=>{transcriptEnd.current?.scrollIntoView({block:'nearest'});},[events.length,activeRequest?.event_id]);

  async function saveAttempt() {
    const text=attempt.trim();
    if(!text)return;
    await emitEvent(id,'attempt_submitted',{attempt_text:text,is_partial:true,...(questionId?{question_event_id:questionId}:{})});
    setAttempt('');
  }
  async function ask(tier:number,text?:string) {
    const previous=requestRef.current || savedRequest();
    if(previous) {await deliver(previous,true);return;}
    if(mode==='try_myself')await saveAttempt();
    const action=!text ? (tier===2?'hint':'answer') as 'hint'|'answer' : undefined;
    const followup=text || (tier===2?'Give me a hint for the current question.':'Show an answer to the current question.');
    await deliver({event_id:crypto.randomUUID(),session_id:id,tier,provider:'auto',answer_style:answerStyle,followup_text:followup,...(action?{help_action:action}:{})});
  }
  async function relatedExercise(){
    const previous=requestRef.current||savedRequest();
    if(previous){await deliver(previous,true);return;}
    await saveAttempt();
    await deliver({event_id:crypto.randomUUID(),session_id:id,tier:3,provider:'auto',answer_style:'concise',help_action:'exercise',followup_text:'Give me one related practice question without the answer.'});
  }
  async function checkThinking(){
    const previous=requestRef.current||savedRequest();
    if(previous){await deliver(previous,true);return;}
    await saveAttempt();
    await deliver({event_id:crypto.randomUUID(),session_id:id,tier:3,provider:'auto',answer_style:'concise',help_action:'check_thinking',followup_text:'Check my thinking for the current question without a worked solution.'});
  }
  async function stop() {
    if(!activeRequest||stopping)return;setStopping(true);setError('');
    try {for(let i=0;i<6;i++){try{await api(`/ai/requests/${activeRequest.event_id}/cancel`,{});setPreview('');return;}catch(e){if(!(e instanceof ApiError)||e.status!==404||i===5)throw e;await new Promise(resolve=>setTimeout(resolve,350));}}}
    catch(e){setError((e as Error).message);setStopping(false);}
  }
  async function regenerate(answerId:string) {
    const answer=events.find(e=>e.id===answerId)!;
    const original=events.find(e=>e.id===answer.payload.request_event_id)!;
    await deliver({event_id:crypto.randomUUID(),session_id:id,tier:original.payload.tier_requested,provider:'auto',answer_style:answerStyle,followup_text:original.payload.followup_text||undefined,help_action:original.payload.help_action||undefined,regenerate_of:answerId,stream:true});
  }
  async function changeMode(next:ConversationMode) {
    if(next!==mode)await emitEvent(id,'conversation_mode_changed',{mode:next});
  }
  async function complete() {
    await flushQueue(id);
    if(requestRef.current || savedRequest())throw new Error('Please let the pending reply finish before completing this conversation.');
    const final_status=replies.length?'solved_with_ai':requests.length?'solved_without_ai_response':'solved_independently';
    if(!closeRef.current)closeRef.current={event_id:crypto.randomUUID(),final_status};
    await api(`/sessions/${id}/close`,closeRef.current);
  }
  const pendingQuestion=!activeRequest?.regenerate_of&&activeRequest?.followup_text && !events.some(e=>e.id===activeRequest.event_id)?activeRequest.followup_text:null;
  const transcript=events.filter(e=>e.event_type==='session_started'||e.event_type==='attempt_submitted'||e.event_type==='ai_hint_delivered'||e.event_type==='ai_hint_failed'&&e.payload.cancelled||e.event_type==='ai_hint_requested'&&e.payload.followup_text&&!e.payload.regenerate_of);
  return <section className="conversation-page">
    <header className="conversation-heading"><div><ConversationTitle id={id} title={data.title} custom={data.custom_title} reload={reload}/><p>{closed?`${data.overview?.status_label||'Completed'} · saved in history`:'Saved as you go. Come back whenever you like.'}</p></div>{!closed&&<button className="text-button" disabled={busy||!!unfinished||!!activeRequest} onClick={()=>void run(complete)}>Complete conversation <Check size={14}/></button>}</header>
    <ConversationTools data={data} busy={busy||!!activeRequest} reload={reload} onMatches={setMatches}/>
    {notice&&<p role="status">{notice}</p>}
    {data.deletion_pending&&<p role="status">This conversation is awaiting operator deletion. You can still read and export it.</p>}
    {(error||storageError||messageStorageError)&&<div className="error" role="alert">{error||storageError||messageStorageError}<button disabled={busy} onClick={()=>void run(async()=>{await flushQueue(id);const request=requestRef.current||savedRequest();if(request)await deliver(request,true);})}>Retry sync / refresh</button></div>}
    <div className="conversation-messages" aria-label="Conversation messages">
      {transcript.map(event=>{
        if(event.event_type==='ai_hint_failed')return <p key={event.id} className="field-help">Generation stopped. You can ask again whenever you like.</p>;
        const assistant=event.event_type==='ai_hint_delivered';
        const own=event.event_type==='attempt_submitted';
        return <article id={`message-${event.id}`} tabIndex={-1} key={event.id} className={`${matches.includes(event.id)?'message-search-match':''} chat-message ${assistant?'assistant-message':'user-message'} ${own?'own-attempt':''}`}>
          <div className="message-label">{assistant?<><img src="/logo.png" alt="" width={24} height={24}/>ThinkFirst{event.payload.regenerate_of&&<span>New version</span>}{event.payload.tier<3&&<span>Hint</span>}{event.payload.help_action==='exercise'&&<span>Practice question</span>}{event.payload.help_action==='check_thinking'&&<span>Thinking feedback</span>}</>:own?<><PenLine size={14}/>Your thinking</>:'You'}</div>
          {assistant?<AnswerContent text={event.payload.hint_text}/>:<div className="message-content">{event.payload.problem_text || event.payload.attempt_text || event.payload.followup_text}</div>}
          {!assistant&&!own&&!event.payload.help_action&&<EditQuestion sessionId={id} event={event} disabled={busy||!!activeRequest||Boolean(data.deletion_pending)}/>}
          {assistant&&event.id===replies.at(-1)?.id&&!closed&&<button className="text-button" disabled={busy||!!activeRequest||events.slice(events.indexOf(event)+1).some(e=>['attempt_submitted','ai_hint_requested'].includes(e.event_type))} onClick={()=>void run(()=>regenerate(event.id))}>Regenerate answer</button>}
          {assistant&&event.payload.help_action!=='exercise'&&!data.deletion_pending&&<div className="saved-answer-actions"><button className="text-button" aria-pressed={savedAnswers.get(event.id)||false} disabled={busy} onClick={()=>void run(()=>emitEvent(id,'answer_saved',{answer_event_id:event.id,saved:!savedAnswers.get(event.id)}))}>{savedAnswers.get(event.id)?'Remove from Saved':'Save for later'}</button>{savedAnswers.get(event.id)&&<Link className="text-button" href={`/practice/${event.id}`}>Try this question again</Link>}</div>}
          {assistant&&!data.deletion_pending&&<AnswerFeedback sessionId={id} answerId={event.id} rating={feedback.get(event.id)} reload={reload}/>}
          {assistant&&event.payload.help_action!=='exercise'&&!data.deletion_pending&&<AnswerVerification sessionId={id} answerId={event.id} saved={verification.get(event.id)} reload={reload}/>}
        </article>;
      })}
      {pendingQuestion&&<article className="chat-message user-message"><div className="message-label">You</div><div className="message-content">{pendingQuestion}</div></article>}
      {preview&&!stopping&&<article className="chat-message assistant-message streaming-preview"><div className="message-label">ThinkFirst · Writing</div><AnswerContent text={preview}/><p className="field-help">Live preview. The final answer is saved when complete.</p></article>}
      {activeRequest&&<div className="thinking-state" role="status"><LoaderCircle size={17} className="spin"/>{stopping?'Stopping…':busy?(preview?'Writing…':'Thinking…'):'Your reply is pending. Reconnect to continue.'}<button className="secondary" disabled={stopping} onClick={()=>void stop()}>Stop generating</button></div>}
      <div ref={transcriptEnd}/>
    </div>
    {!closed&&<PracticeSupport id={id} practice={data.practice} paused={busy||!!activeRequest||!!unfinished} reload={reload}/>}
    {closed?<div className="conversation-complete"><p>Your conversation and your own attempts are saved together.</p><Link className="primary" href="/new">Ask another question</Link></div>:<div className="conversation-composer">
      <div className="mode-switch" aria-label="Conversation mode"><button type="button" aria-pressed={mode==='ask_ai'} disabled={busy||!!activeRequest} onClick={()=>void run(()=>changeMode('ask_ai'))}><MessageCircle size={16}/>Ask AI</button><button type="button" aria-pressed={mode==='try_myself'} disabled={busy||!!activeRequest} onClick={()=>void run(()=>changeMode('try_myself'))}><PenLine size={16}/>Try myself</button></div>
      {mode==='ask_ai'?<form onSubmit={e=>{e.preventDefault();if(message.trim())void run(()=>ask(3,message.trim()));}}>
        <label className="sr-only" htmlFor="chat-message">Your message</label><textarea id="chat-message" rows={3} maxLength={5000} value={message} onKeyDown={e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'&&!e.nativeEvent.isComposing){e.preventDefault();e.currentTarget.form?.requestSubmit();}}} disabled={busy||!!activeRequest} onChange={e=>setMessage(e.target.value)} placeholder={replies.length?'Ask a follow-up, or explore another idea…':'Add a detail or ask a follow-up…'}/>
        <div className="composer-actions"><span className="field-help">AI can make mistakes. Check important details.</span>{!replies.length&&!message.trim()?<button className="primary" type="button" disabled={busy||!!activeRequest} onClick={()=>void run(()=>ask(3))}>Get an answer <ArrowUp size={16}/></button>:<button className="primary" disabled={busy||!!activeRequest||!message.trim()}>Send <ArrowUp size={16}/></button>}</div>
      </form>:<form onSubmit={e=>{e.preventDefault();void run(saveAttempt);}}>
        <label className="field-label" htmlFor="own-attempt">What would you try?</label><textarea ref={attemptInput} id="own-attempt" rows={4} maxLength={20000} value={attempt} disabled={busy||!!activeRequest} onChange={e=>setAttempt(e.target.value)} placeholder="Write a rough idea, a first step, or your own answer…"/>
        <div className="composer-actions"><button className="primary" disabled={busy||!!activeRequest||!attempt.trim()}>Save my thinking <Check size={15}/></button><div className="button-row"><button className="text-button" type="button" disabled={busy||!!activeRequest} onClick={()=>void run(()=>ask(2))}><Lightbulb size={15}/>Get a hint</button><button className="text-button" type="button" disabled={busy||!!activeRequest} onClick={()=>void run(()=>ask(3))}>Show an answer</button></div></div>
        <p className="field-help">When you ask for help, your current attempt is saved with it.</p>
        <button className="text-button" type="button" disabled={busy||!!activeRequest||(!attempt.trim()&&!hasCurrentAttempt)||allowance?.requests_remaining===0} onClick={()=>void run(checkThinking)}>Check my thinking · 1 AI request</button>
      </form>}
    </div>}
    {!closed&&<div className="conversation-options"><label>Answer length <select value={answerStyle} disabled={busy||!!activeRequest} onChange={e=>setAnswerStyle(e.target.value as 'concise'|'detailed')}><option value="concise">Concise</option><option value="detailed">Detailed</option></select></label>
      {allowance&&<span className="field-help" title={`Resets ${new Date(allowance.resets_at).toLocaleString()}. Shared service limits also apply.`}>{allowance.requests_remaining} of {allowance.daily_limit} AI requests left today · resets at {new Date(allowance.resets_at).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'})}. {allowance.requests_remaining===0?'Try myself is still available.':'Shared limits apply.'}</span>}
    </div>}
    {!closed&&<details className="related-exercise"><summary>Practise a related question</summary><p>Get one new question to try yourself. Your current attempt is saved first. This uses one AI request and may use fallback services within the existing limits.</p><button className="secondary" disabled={busy||!!activeRequest||!!unfinished||allowance?.requests_remaining===0} onClick={()=>void run(relatedExercise)}>Create a practice question · 1 AI request</button></details>}
    {!data.deletion_pending&&<ConversationReview data={data} reload={reload}/> }
    <ThinkingActivity data={data.question_tracking}/>
  </section>;
}
