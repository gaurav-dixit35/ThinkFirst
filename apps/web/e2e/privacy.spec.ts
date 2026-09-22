import {test,expect,Page} from '@playwright/test';

const sid='932aa3ac-3ed8-43ee-a7ee-2793c3a1c7ba';
async function fixture(page:Page,{welcome=false,erased=false,failConsent=false}={}){
  let state={notice_version:'2026-09-16',acknowledged:!welcome,research_opt_in:false,last_erased_at:erased?'2026-09-16T12:00:00Z':null,deletion_request:null as any};
  let answerStyle='concise';
  const calls:any[]=[];
  await page.route('http://localhost:8000/**',async route=>{
    const req=route.request(),path=new URL(req.url()).pathname;
    if(req.method()==='POST')calls.push({path,body:req.postDataJSON()});
    let data:any;
    if(path==='/me')data={id:'privacy-user',display_name:'Fixture',admin:false,development:false,privacy:state};
    else if(path==='/preferences/answers'){if(req.method()==='POST')answerStyle=req.postDataJSON().answer_style;data={answer_style:answerStyle};}
    else if(path==='/health')data={status:'ok',database:'connected'};
    else if(path==='/ai/hint')data={id:'new-answer',event_type:'ai_hint_delivered',payload:{tier:req.postDataJSON().tier,hint_text:'Synthetic reply.'},created_at:new Date().toISOString()};
    else if(path==='/privacy'){
      if(req.method()==='POST'&&failConsent){await route.fulfill({status:503,json:{detail:'Your choice could not be saved.'}});return;}
      if(req.method()==='POST'){const body=req.postDataJSON();state={...state,research_opt_in:body.research_opt_in,acknowledged:state.acknowledged||!!body.acknowledge_notice};}
      data=state;
    }else if(path==='/preferences')data={practice_reminders:true};
    else if(path==='/privacy/export')data={schema_version:1,account:{id:'privacy-user'},sessions:[]};
    else if(path==='/privacy/deletion'){state={...state,research_opt_in:false,deletion_request:{id:'deletion-reference',status:'pending'}};data=state;}
    else if(path==='/ai/usage')data={daily_limit:30,requests_used:0,requests_remaining:30,resets_at:'2099-01-01T00:00:00Z'};
    else if(path===`/sessions/${sid}`)data={id:sid,answer_style:answerStyle,status:'open',experience:'chat',mode:'try_myself',title:'A question',custom_title:false,events:[{id:'start',event_type:'session_started',payload:{problem_text:'A question'},created_at:new Date().toISOString()}],summary:{},practice:{eligible:false,active:false,reminders_enabled:true}};
    else throw new Error(`Unexpected API call: ${path}`);
    await route.fulfill({json:data});
  });
  return calls;
}

test('hosted notice continues without research consent; export and deletion have clear controls',async({page})=>{
  const calls=await fixture(page,{welcome:true});
  await page.goto('/settings');
  await expect(page.getByRole('heading',{name:'Before you begin'})).toBeVisible();
  await page.getByRole('button',{name:'I understand · Continue'}).click();
  const consent=page.getByRole('checkbox',{name:'Include my conversations in research'});
  await expect(consent).not.toBeChecked();
  expect(calls[0].body.research_opt_in).toBe(false);
  await consent.check();
  await expect(page.getByText('Research sharing enabled.',{exact:true})).toBeVisible();
  const download=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download my data'}).click();
  expect((await download).suggestedFilename()).toBe('thinkfirst-my-data.json');
  await page.getByText('Delete my conversations',{exact:true}).click();
  const request=page.getByRole('button',{name:'Request conversation deletion'});
  await expect(request).toBeDisabled();
  await page.getByLabel('Type DELETE MY CONVERSATIONS to confirm').fill('DELETE MY CONVERSATIONS');
  await request.click();
  await expect(page.getByText('Deletion requested. Your conversations have not been deleted yet.')).toBeVisible();
  await expect(consent).not.toBeChecked();
  await expect(consent).toBeDisabled();
  expect(calls.filter(c=>c.path==='/privacy/deletion')).toHaveLength(1);
  expect(calls.some(c=>c.path.startsWith('/ai/'))).toBe(false);
});

test('hosted drafts ignore unscoped and other-account text while recovering the owner draft',async({page})=>{
  await fixture(page);
  await page.addInitScript(({sid})=>{
    localStorage.setItem(`thinkfirst.draft.${sid}`,JSON.stringify({attempt:'Legacy private text',partial:true}));
    localStorage.setItem(`thinkfirst.draft.another-user.${sid}`,JSON.stringify({attempt:'Another account private text',partial:true}));
    localStorage.setItem(`thinkfirst.draft.privacy-user.${sid}`,JSON.stringify({attempt:'My own draft',partial:true}));
  },{sid});
  await page.goto(`/session/${sid}`);
  await expect(page.getByRole('textbox',{name:'What would you try?'})).toHaveValue('My own draft');
  await expect(page.getByText('Legacy private text')).toHaveCount(0);
  await expect(page.getByText('Another account private text')).toHaveCount(0);
});

test('completed erasure clears only this account local work before syncing',async({page})=>{
  const calls=await fixture(page,{erased:true});
  await page.addInitScript(({sid})=>{
    localStorage.setItem(`thinkfirst.draft.privacy-user.${sid}`,JSON.stringify({attempt:'Erased draft',partial:true}));
    localStorage.setItem(`thinkfirst.draft.another-user.${sid}`,JSON.stringify({attempt:'Keep other account',partial:true}));
    localStorage.setItem('thinkfirst.pending.privacy-user',JSON.stringify([{event_id:'erased-event',session_id:sid,event_type:'attempt_submitted',payload:{attempt_text:'Erased text',is_partial:true}}]));
  },{sid});
  await page.goto('/settings');
  await expect(page.getByRole('heading',{name:'Your space. Your pace.'})).toBeVisible();
  const keys=await page.evaluate(()=>Object.keys(localStorage));
  expect(keys).not.toContain(`thinkfirst.draft.privacy-user.${sid}`);
  expect(keys).not.toContain('thinkfirst.pending.privacy-user');
  expect(keys).toContain(`thinkfirst.draft.another-user.${sid}`);
  expect(calls).toHaveLength(0);
});


test('failed research consent saves revert the visible choice',async({page})=>{
  await fixture(page,{failConsent:true});
  await page.goto('/settings');
  const consent=page.getByRole('checkbox',{name:'Include my conversations in research'});
  await consent.click();
  await expect(page.getByRole('region',{name:'Your data'}).getByRole('alert')).toHaveText('Your choice could not be saved.');
  await expect(consent).not.toBeChecked();
});


test('settings saves answer defaults, syncs work and help buttons send current-question intent',async({page})=>{
  const calls=await fixture(page);
  await page.goto('/settings');
  await page.getByRole('combobox',{name:'Answer length',exact:true}).selectOption('detailed');
  await expect(page.getByText('Default saved for conversations you open next.')).toBeVisible();
  await page.reload();
  await expect(page.getByRole('combobox',{name:'Answer length',exact:true})).toHaveValue('detailed');
  await page.getByRole('button',{name:'Sync saved work',exact:true}).click();
  await expect(page.getByText('Database connected. All queued work on this device is synced.')).toBeVisible();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'test-results/settings-mobile.png',fullPage:true});
  await page.goto(`/session/${sid}`);
  await expect(page.getByRole('combobox',{name:'Answer length',exact:true})).toHaveValue('detailed');
  await page.getByRole('button',{name:'Get a hint',exact:true}).click();
  await expect.poll(()=>calls.filter(c=>c.path==='/ai/hint').length).toBe(1);
  const request=calls.find(c=>c.path==='/ai/hint').body;
  expect(request.help_action).toBe('hint');
  expect(request.answer_style).toBe('detailed');
  expect(request.followup_text).toBe('Give me a hint for the current question.');
});
