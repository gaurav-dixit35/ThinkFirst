import {test,expect,Page} from '@playwright/test';

const sid='a5217d51-3034-483f-adbb-4a4c6b3deeb5';
async function fixture(page:Page,failDecision=false){
  let reminders=true,mode='ask_ai',decided=false,active=false;
  const calls:any[]=[];
  const events:any[]=[{id:'start',event_type:'session_started',payload:{problem_text:'How do loops work?'},created_at:new Date().toISOString()},
    ...[1,2,3].map(n=>({id:`answer-${n}`,event_type:'ai_hint_delivered',payload:{tier:3,hint_text:`Loop example ${n}.`},created_at:new Date().toISOString()}))];
  await page.route('http://localhost:8000/**',async route=>{
    const request=route.request(),path=new URL(request.url()).pathname;
    let data:any;
    if(path==='/me')data={id:'practice-user',display_name:'Fixture',admin:false,development:false};
    else if(path==='/preferences/answers')data={answer_style:'concise'};
    else if(path==='/privacy')data={acknowledged:true,research_opt_in:false,notice_version:'fixture',last_erased_at:null,deletion_request:null};
    else if(path==='/ai/usage')data={daily_limit:30,requests_used:3,requests_remaining:27,resets_at:'2099-01-01T00:00:00Z'};
    else if(path==='/preferences'){
      if(request.method()==='POST')reminders=request.postDataJSON().practice_reminders;
      data={practice_reminders:reminders};
    }else if(path===`/sessions/${sid}`)data={id:sid,status:'open',experience:'chat',mode,events,summary:{},practice:{
      eligible:reminders&&!decided&&mode==='ask_ai',answer_event_id:reminders&&!decided&&mode==='ask_ai'?'answer-3':null,
      reminders_enabled:reminders,active:active&&mode==='try_myself',question:'How do loops work?',task:'Trace a small example. What output do you expect, and why?'}};
    else if(path==='/events'){
      const body=request.postDataJSON();calls.push(body);
      if(body.event_type==='practice_invitation_responded'){
        if(failDecision){await route.fulfill({status:503,json:{detail:'Synthetic offline decision'}});return;}
        decided=true;
        if(body.payload.decision==='try_myself'){mode='try_myself';active=true;}
      }
      if(body.event_type==='conversation_mode_changed')mode=body.payload.mode;
      if(body.event_type==='attempt_submitted')active=false;
      data={id:body.event_id,event_type:body.event_type,payload:body.payload,created_at:new Date().toISOString()};events.push(data);
    }else if(path==='/ai/hint'){
      const body=request.postDataJSON();calls.push({ai:true,...body});
      data={id:'next-answer',event_type:'ai_hint_delivered',payload:{tier:3,hint_text:'A follow-up answer.',request_event_id:body.event_id},created_at:new Date().toISOString()};events.push(data);
    }else throw new Error(`Unexpected API call: ${path}`);
    await route.fulfill({json:data});
  });
  return calls;
}

test('No stays dismissed after reload; even a failed optional save never blocks chat',async({page})=>{
  const calls=await fixture(page,true);
  await page.goto(`/session/${sid}`);
  await page.getByRole('button',{name:'No, keep chatting',exact:true}).click();
  await expect(page.getByLabel('Optional practice invitation')).toHaveCount(0);
  await expect(page.getByText('Your choice could not sync.',{exact:false})).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading',{name:'Your conversation',exact:true})).toBeVisible();
  await expect(page.getByLabel('Optional practice invitation')).toHaveCount(0);
  await page.getByLabel('Your message',{exact:true}).fill('Continue explaining');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.locator('.assistant-message')).toHaveCount(4);
  expect(calls.filter(c=>c.ai)).toHaveLength(1);
  expect(calls.filter(c=>c.event_type==='practice_invitation_responded')).toHaveLength(1);
});

test('Yes preserves the draft, opens useful practice and does not call AI',async({page})=>{
  const calls=await fixture(page);
  await page.addInitScript(({sid})=>localStorage.setItem(`thinkfirst.draft.practice-user.${sid}`,JSON.stringify({attempt:'My existing idea: trace one iteration.',partial:true})),{sid});
  await page.goto(`/session/${sid}`);
  await page.getByRole('button',{name:'Yes, I’ll try',exact:true}).click();
  await expect(page.getByLabel('Practice step')).toContainText('What output do you expect');
  await expect(page.getByLabel('What would you try?')).toBeFocused();
  await expect(page.getByLabel('What would you try?')).toHaveValue('My existing idea: trace one iteration.');
  await page.getByRole('button',{name:'Save my thinking',exact:true}).click();
  await expect(page.locator('.own-attempt')).toContainText('trace one iteration');
  await expect(page.getByLabel('Practice step')).toHaveCount(0);
  expect(calls.filter(c=>c.ai)).toHaveLength(0);
  expect(calls.filter(c=>c.event_type==='attempt_submitted')).toHaveLength(1);
});

test('reminders can be turned off and restored in Settings; answer feedback persists',async({page})=>{
  const calls=await fixture(page);
  await page.goto(`/session/${sid}`);
  await page.getByRole('button',{name:'Turn off reminders',exact:true}).click();
  await expect(page.getByLabel('Optional practice invitation')).toHaveCount(0);
  await page.goto('/settings');
  const toggle=page.getByLabel('Offer optional practice reminders');
  await expect(toggle).not.toBeChecked();
  await toggle.check();
  await expect(toggle).toBeChecked();
  await expect(toggle).toBeEnabled();
  await page.goto(`/session/${sid}`);
  await expect(page.getByLabel('Optional practice invitation')).toBeVisible();
  const helpful=page.locator('.assistant-message').first().getByRole('button',{name:'Helpful',exact:true});
  await helpful.click();
  await expect(helpful).toHaveAttribute('aria-pressed','true');
  await page.reload();
  await expect(helpful).toHaveAttribute('aria-pressed','true');
  await helpful.click();
  await expect(helpful).toHaveAttribute('aria-pressed','false');
  await page.goto('/settings');
  await expect(toggle).toBeChecked();
  await page.route('http://localhost:8000/preferences',async route=>{
    if(route.request().method()==='POST')await route.fulfill({status:503,json:{detail:'Synthetic save failure'}});
    else await route.fallback();
  });
  await toggle.click();
  await expect(page.getByText('Your preference could not be saved.',{exact:false})).toBeVisible();
  await expect(toggle).toBeChecked();
  expect(calls.filter(c=>c.event_type==='answer_feedback').map(c=>c.payload.rating)).toEqual(['helpful','cleared']);
  expect(calls.filter(c=>c.ai)).toHaveLength(0);
});
