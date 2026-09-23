import {test,expect,Page} from '@playwright/test';
const sid='86bd285c-302c-4bfb-a201-a39bbf2c84a9';
const startId='aa687db8-0e40-465b-9bc5-cd77cde10b22', requestId='f7d0c09c-1f37-4a96-b115-e50635ef37be', answerId='472fd86d-57b2-4e19-9d35-aa218b9b3b7c';
async function fixture(page:Page){
 const events:any[]=[{id:startId,event_type:'session_started',payload:{problem_text:'What is 5 times 9?',experience:'chat'},created_at:new Date().toISOString()},{id:requestId,event_type:'ai_hint_requested',payload:{tier_requested:3},created_at:new Date().toISOString()},{id:answerId,event_type:'ai_hint_delivered',payload:{tier:3,hint_text:'The answer is 45.',request_event_id:requestId},created_at:new Date().toISOString()}];
 const calls:any[]=[];let archived=false,deleting=false,stopped=false,release:(()=>void)|undefined;
 await page.route('http://localhost:8000/**',async route=>{
  const req=route.request(),path=new URL(req.url()).pathname,body=req.method()==='POST'?req.postDataJSON():null;
  if(body)calls.push({path,body});
  let data:any={};
  if(path==='/me')data={id:'upgrade-user',development:true,display_name:'Fixture',admin:false};
  else if(path==='/ai/usage')data={daily_limit:30,requests_remaining:29,resets_at:new Date().toISOString()};
  else if(path.endsWith('/archive')){archived=body.archived;data={archived};}
  else if(path.endsWith('/deletion')){deleting=true;data={status:'pending'};}
  else if(path.endsWith('/edit-question'))data={id:'new-edited-conversation'};
  else if(path.endsWith('/cancel')){stopped=true;release?.();data={status:'stopping'};}
  else if(path==='/ai/hint'){
    events.push({id:body.event_id,event_type:'ai_hint_requested',payload:{tier_requested:3,regenerate_of:body.regenerate_of},created_at:new Date().toISOString()});
    await new Promise<void>(resolve=>{release=resolve;});
    events.push({id:'cancelled-result',event_type:'ai_hint_failed',payload:{request_event_id:body.event_id,cancelled:true},created_at:new Date().toISOString()});
    await route.fulfill({status:499,json:{detail:'Generation stopped. Usage already incurred still counts.'}});return;
  }
  else if(path.startsWith('/ai/requests/'))data={status:stopped?'cancelled':'pending',preview:stopped?'':'Here is the live answer preview.',result:null};
  else if(path.startsWith('/sessions/'))data={id:sid,status:'open',experience:'chat',mode:'ask_ai',title:'Multiplication',events,archived,deletion_pending:deleting,overview:{can_review:false},practice:{eligible:false,active:false}};
  await route.fulfill({json:data});
 });return calls;
}

test('search, archive and individual deletion controls work on mobile',async({page})=>{
 await page.setViewportSize({width:390,height:844});const calls=await fixture(page);
 await page.goto(`/session/${sid}`);await page.getByText('Conversation tools',{exact:true}).click();
 await page.getByLabel('Search this conversation').fill('45');await expect(page.getByText('1 of 1 matches')).toBeVisible();
 await page.getByRole('button',{name:'Next match'}).click();await expect(page.locator('.message-search-match')).toBeFocused();
 await page.getByRole('button',{name:'Archive conversation',exact:true}).click();await expect(page.getByRole('button',{name:'Restore from archive'})).toBeVisible();
 await page.getByText('Delete this conversation',{exact:true}).click();await expect(page.getByRole('button',{name:'Request deletion',exact:true})).toBeDisabled();
 await page.getByLabel('Type DELETE THIS CONVERSATION').fill('DELETE THIS CONVERSATION');await page.getByRole('button',{name:'Request deletion',exact:true}).click();
 await expect(page.getByText('Deletion requested. Operator processing is still pending.')).toBeVisible();
 expect(calls.some(c=>c.path==='/ai/hint')).toBe(false);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('regeneration streams a preview and Stop sends cancellation',async({page})=>{
 const calls=await fixture(page);await page.goto(`/session/${sid}`);
 await page.getByRole('button',{name:'Regenerate answer'}).click();await expect(page.getByText('Here is the live answer preview.')).toBeVisible();
 await page.getByRole('button',{name:'Stop generating'}).click();
 await expect(page.getByText('Generation stopped. Usage already incurred still counts.',{exact:true})).toBeVisible();
 await expect(page.getByText('The answer is 45.',{exact:true})).toBeVisible();
 const request=calls.find(c=>c.path==='/ai/hint');expect(request.body.regenerate_of).toBe(answerId);expect(request.body.stream).toBe(true);
 expect(calls.filter(c=>c.path==='/ai/hint')).toHaveLength(1);
});

test('question editor supports Escape and opens an independent saved edit',async({page})=>{
 const calls=await fixture(page);await page.goto(`/session/${sid}`);
 await page.getByRole('button',{name:'Edit question'}).click();await page.getByLabel('Edit your question').press('Escape');await expect(page.getByRole('button',{name:'Edit question'})).toBeFocused();
 await page.getByRole('button',{name:'Edit question'}).click();await page.getByLabel('Edit your question').fill('What is 5 times 8?');
 await page.getByRole('button',{name:'Save edit and ask AI'}).click();await expect(page).toHaveURL(/new-edited-conversation/);
 expect(calls.find(c=>c.path.endsWith('/edit-question')).body).toMatchObject({source_event_id:startId,question:'What is 5 times 8?'});
});
