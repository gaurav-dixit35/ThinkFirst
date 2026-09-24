import {test,expect,Page} from '@playwright/test';
const sid='fe2434f3-912d-4e58-8f85-282b373e2659',qid='7222820c-70d2-4681-8805-eb38e821caec',aid='b9cc8d36-6a50-490a-a209-ff44112a0bc8';
async function fixture(page:Page,{closed=false,loseVerification=false}={}){
 const calls:{path:string;body:any}[]=[];let mode='try_myself',lost=false;
 const events:any[]=[{id:qid,event_type:'session_started',payload:{problem_text:'Solve 2x + 3 = 11'},created_at:new Date().toISOString()},
  {id:aid,event_type:'ai_hint_delivered',payload:{tier:3,hint_text:'Subtract three from both sides.'},created_at:new Date().toISOString()}];
 await page.route('http://localhost:8000/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname,body=req.method()==='POST'?req.postDataJSON():null;
  if(body)calls.push({path,body});let data:any;
  if(path==='/me')data={id:'thinking-fixture',admin:false,development:true};
  else if(path==='/ai/usage')data={requests_used:1,requests_remaining:29,daily_limit:30,resets_at:'2099-01-01T00:00:00Z'};
  else if(path===`/sessions/${sid}`){
   const reports=events.filter(e=>e.event_type==='answer_verification_reported'),status=reports.at(-1)?.payload.status;
   data={id:sid,status:closed?'closed':'open',experience:'chat',mode,events,summary:{},question_tracking:{version:'question-turn-v1',current_question_event_id:qid,event_questions:Object.fromEntries(events.map(e=>[e.id,qid])),questions:[{id:qid,text:'Solve 2x + 3 = 11',attempts:events.filter(e=>e.event_type==='attempt_submitted').length,requests:{answer:1,hint:0,check_thinking:calls.filter(c=>c.path==='/ai/hint').length,exercise:0},delivered:1,verification:{checked:status==='checked'?1:0,found_issue:status==='found_issue'?1:0,not_checked:status==='not_checked'?1:0}}]}};
  }else if(path==='/events'){
   if(body.event_type==='conversation_mode_changed')mode=body.payload.mode;
   data={id:body.event_id,event_type:body.event_type,payload:body.payload,created_at:new Date().toISOString()};
   if(!events.some(e=>e.id===body.event_id))events.push(data);
   if(loseVerification&&!lost&&body.event_type==='answer_verification_reported'){lost=true;await route.abort('connectionreset');return;}
  }else if(path==='/ai/hint'){
   data={id:'thinking-answer',event_type:'ai_hint_delivered',payload:{tier:3,hint_text:'Your subtraction is sound. Which operation leaves x by itself?',help_action:body.help_action,request_event_id:body.event_id},created_at:new Date().toISOString()};
   events.push({id:body.event_id,event_type:'ai_hint_requested',payload:{...body,tier_requested:3},created_at:new Date().toISOString()},data);
  }else throw new Error(`Unexpected API request: ${path}`);
  await route.fulfill({json:data});
 });
 return calls;
}

test('thinking check saves the attempt, keeps modes separate and shows question activity',async({page})=>{
 const calls=await fixture(page);await page.goto(`/session/${sid}`);
 const check=page.getByRole('button',{name:'Check my thinking · 1 AI request',exact:true});
 await expect(check).toBeDisabled();
 await page.getByLabel('What would you try?').fill('Subtract three: 2x = 8.');await check.click();
 await expect(page.getByText('Thinking feedback',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Try myself',exact:true})).toHaveAttribute('aria-pressed','true');
 const attempt=calls.find(c=>c.body.event_type==='attempt_submitted')!;
 expect(attempt.body.payload.question_event_id).toBe(qid);
 expect(calls.filter(c=>c.path==='/ai/hint')).toHaveLength(1);
 expect(calls.find(c=>c.path==='/ai/hint')!.body.help_action).toBe('check_thinking');
 await page.getByText('Thinking activity in this conversation',{exact:true}).click();
 await expect(page.locator('.thinking-activity')).toContainText('1 saved attempts');
 await page.getByRole('button',{name:'Ask AI',exact:true}).click();
 await expect(page.getByLabel('Your message',{exact:true})).toBeVisible();await expect(check).toHaveCount(0);
});

test('optional verification survives a lost response without another AI request',async({page})=>{
 const calls=await fixture(page,{closed:true,loseVerification:true});await page.goto(`/session/${sid}`);
 const panel=page.locator('.answer-verification').first();await panel.locator('summary').click();
 await panel.getByLabel('Did you check this answer?').selectOption('checked');
 await expect(panel.getByRole('button',{name:'Save verification'})).toBeDisabled();
 await panel.getByLabel('How did you check?').selectOption('calculation');
 await panel.getByLabel('Your verification note (optional)').fill('Substituted my result into the original equation.');
 await panel.getByRole('button',{name:'Save verification'}).click();
 await expect(panel.getByRole('alert')).toBeVisible();
 await expect(panel.getByLabel('Your verification note (optional)')).toHaveValue('Substituted my result into the original equation.');
 await panel.getByRole('button',{name:'Save verification'}).click();
 await expect(panel.getByRole('status')).toHaveText('Verification note saved.');
 const saves=calls.filter(c=>c.body.event_type==='answer_verification_reported');
 expect(saves).toHaveLength(2);expect(saves[0].body.event_id).toBe(saves[1].body.event_id);
 await page.reload();await expect(panel.locator('summary')).toContainText('I checked it');
 await panel.locator('summary').click();await expect(panel.getByLabel('How did you check?')).toHaveValue('calculation');
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'test-results/thinking-verification-mobile.png',fullPage:true});
 expect(calls.filter(c=>c.path==='/ai/hint')).toHaveLength(0);
});
