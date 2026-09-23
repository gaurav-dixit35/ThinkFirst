import {test,expect,Page} from '@playwright/test';
import {readFile} from 'node:fs/promises';
const sid='c27e3fd1-837c-438c-981a-8b374cce2814', aid='4c8efa3f-b882-4661-b223-9c7e52766118';
async function fixture(page:Page){
 const calls:{path:string;body:any}[]=[];
 let language='auto',goal={goal:'',weekly_target:0,questions_retried:0,attempts:0,week_start:'2026-09-21T00:00:00Z',resets_at:'2026-09-28T00:00:00Z'};
 const reports:any[]=[],attempts:any[]=[];
 const events:any[]=[{id:'start',event_type:'session_started',payload:{problem_text:'What is 5 times 9?',experience:'chat'},created_at:'2026-09-22T00:00:00Z'},{id:'request',event_type:'ai_hint_requested',payload:{tier_requested:3},created_at:'2026-09-22T00:00:01Z'},{id:aid,event_type:'ai_hint_delivered',payload:{tier:3,hint_text:'Five times nine equals forty-five.',request_event_id:'request'},created_at:'2026-09-22T00:00:02Z'}];
 await page.route('http://localhost:8000/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname,body=req.method()==='POST'?req.postDataJSON():null;
  if(body)calls.push({path,body});
  let data:any={};
  if(path==='/me')data={id:'functional-fixture',development:true,admin:false};
  else if(path==='/privacy')data={research_opt_in:false,acknowledged:true,deletion_request:null};
  else if(path==='/preferences')data={practice_reminders:true};
  else if(path==='/preferences/answers')data={answer_style:'concise'};
  else if(path==='/preferences/language'){if(body)language=body.answer_language;data={answer_language:language};}
  else if(path==='/learning-goal'){if(body)goal={...goal,...body};data=goal;}
  else if(path==='/ai/usage')data={daily_limit:30,requests_used:0,requests_remaining:30,resets_at:'2026-09-23T00:00:00Z'};
  else if(path==='/service-info')data={operator:null,support_email:null};
  else if(path==='/support/reports'){if(body){const saved={...body,user_id:'functional-fixture',status:'open',created_at:new Date().toISOString()};reports.unshift(saved);data=saved;}else data=reports;}
  else if(path==='/progress')data={experience:'chat',totals:{conversations:0,in_progress:0,completed:0,unfinished:0,own_attempts:0,ai_questions:0,ai_answers:0,failed_requests:0,ai_reviews:0,started_myself:0},modes:{own_only:0,ai_only:0,both:0,no_saved_work:0},weeks:[],updated_at:'2026-09-22T00:00:00Z'};
  else if(path==='/saved')data={items:[{answer_id:aid,session_id:sid,question:'What is 5 times 9?',saved_at:'2026-09-22T00:00:00Z',deletion_pending:false,attempt_count:attempts.length}],total:1,has_more:false,summary:{saved:1,retried:attempts.length?1:0,attempts:attempts.length}};
  else if(path==='/saved/'+aid)data={answer_id:aid,session_id:sid,question:'What is 5 times 9?',answer:'Five times nine equals forty-five.',attempts,deletion_pending:false};
  else if(path==='/events'){if(body.event_type==='learning_attempt_submitted')attempts.push({id:body.event_id,text:body.payload.attempt_text,created_at:new Date().toISOString()});data={id:body.event_id};}
  else if(path==='/sessions/'+sid)data={id:sid,title:'Multiplication',events,status:'open',experience:'chat',mode:'ask_ai',overview:{can_review:false},practice:{eligible:false,active:false}};
  await route.fulfill({json:data});
 });
 return calls;
}

test('language preference and weekly goal save without AI calls',async({page})=>{
 const calls=await fixture(page);
 await page.goto('/settings');await page.getByLabel('Preferred language',{exact:true}).selectOption('hinglish');
 await expect(page.getByText('Language saved. It applies to your next new AI request.')).toBeVisible();
 await page.goto('/dashboard');await page.getByRole('button',{name:'Set a weekly goal',exact:true}).click();
 await page.getByLabel('What would you like to work on?').fill('Explain my reasoning');await page.getByLabel('Different questions to retry per week').fill('4');
 await page.getByRole('button',{name:'Save goal',exact:true}).click();await expect(page.getByRole('heading',{name:'Explain my reasoning'})).toBeVisible();
 expect(calls.find(c=>c.path==='/learning-goal')?.body.weekly_target).toBe(4);
 expect(calls.some(c=>c.path.startsWith('/ai/'))).toBe(false);
});

test('mobile retries hide the response until saved and preserve previous attempts',async({page})=>{
 await page.setViewportSize({width:390,height:844});const calls=await fixture(page);
 await page.goto('/saved');await page.getByRole('link',{name:'Retry or view answer'}).click();
 await expect(page.getByText('Five times nine equals forty-five.',{exact:true})).not.toBeVisible();
 await page.getByLabel('Your own attempt',{exact:true}).fill('Half of ninety is forty-five.');await page.getByRole('button',{name:'Save attempt and compare'}).click();
 await expect(page.getByText('Five times nine equals forty-five.',{exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'Your latest saved retry'})).toBeVisible();
 await page.getByRole('button',{name:'Try again with the answer hidden'}).click();await expect(page.getByText('Five times nine equals forty-five.',{exact:true})).not.toBeVisible();
 await expect(page.getByLabel('Your own attempt',{exact:true})).toBeFocused();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 expect(calls.filter(c=>c.path==='/events')).toHaveLength(1);expect(calls.some(c=>c.path.startsWith('/ai/'))).toBe(false);
});

test('support reports and readable export are real user actions without AI calls',async({page})=>{
 const calls=await fixture(page);await page.goto('/support');
 await page.getByLabel('What happened, and what did you expect?').fill('The save button is difficult to find on mobile.');await page.getByRole('button',{name:'Save report for review'}).click();
 await expect(page.getByText(/Report saved for operator review/)).toBeVisible();await expect(page.getByText('Awaiting review',{exact:true})).toBeVisible();
 await page.goto('/session/'+sid);await page.getByText('Conversation tools',{exact:true}).click();
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'Download conversation (.md)'}).click();const download=await downloadPromise;
 const file=await download.path();expect(file).not.toBeNull();const text=await readFile(file!,'utf8');expect(text).toContain('What is 5 times 9?');expect(text).toContain('Five times nine equals forty-five.');
 expect(calls.filter(c=>c.path==='/support/reports')).toHaveLength(1);expect(calls.some(c=>c.path.startsWith('/ai/'))).toBe(false);
});
