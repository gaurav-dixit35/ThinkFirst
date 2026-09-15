import {test,expect,Page} from '@playwright/test';

test.beforeEach(async({page})=>{
  await page.route('http://localhost:8000/**',route=>route.continue({url:route.request().url().replace(':8000',':8002')}));
  page.on('dialog',dialog=>dialog.accept());
});

async function start(page:Page) {
  await page.goto('/new');
  await page.getByLabel('The problem or question').fill('Synthetic QA: solve 2x + 3 = 11');
  await page.getByRole('button',{name:'Start thinking',exact:true}).click();
  await page.getByRole('button',{name:'Skip, ask AI now'}).click();
}

test('fallback continues through all levels and follow-up chat',async({page,request})=>{
  await start(page);
  for(let tier=1;tier<=3;tier++) {
    await page.getByRole('button',{name:tier===1?'Ask for a clarifying hint':'Show a bigger hint'}).click();
    await expect(page.locator('.hint-response')).toHaveCount(tier);
    await expect(page.locator('main [role="alert"]')).toHaveCount(0);
    await page.getByRole('button',{name:'Skip this check'}).click();
  }
  await page.getByLabel('Keep the conversation going').fill('Why do we subtract the same amount?');
  await page.getByRole('button',{name:'Send follow-up'}).click();
  await expect(page.locator('.hint-response')).toHaveCount(4);
  await expect(page.locator('.hint-response').last()).toContainText('Why do we subtract the same amount?');
  await expect(page.locator('.hint-response').last()).toContainText('preserves equality');
  const sid=page.url().split('/').at(-1);
  const data=await (await request.get(`http://localhost:8002/sessions/${sid}`)).json();
  expect(data.summary.ai_requests).toBe(4);
  expect(data.events.filter((e:any)=>e.event_type==='ai_hint_delivered').every((e:any)=>e.payload.provider==='gemini')).toBe(true);
  expect(data.events.some((e:any)=>e.event_type==='ai_provider_attempted'&&e.payload.provider==='groq'&&['failed','skipped'].includes(e.payload.outcome))).toBe(true);
  await page.getByRole('button',{name:'Skip this check'}).click();
  await page.getByRole('button',{name:'Finish session'}).click();
  await page.getByRole('button',{name:'Skip reflection'}).click();
  await page.getByRole('button',{name:'Finish session'}).click();
  await expect(page.getByText('solved with ai',{exact:true})).toBeVisible();
  await expect(page.locator('.timeline')).toContainText('Why do we subtract the same amount?');
});

test('lost response recovers automatically without a duplicate request',async({page,request})=>{
  await start(page);
  let dropped=false;
  await page.route('http://localhost:8000/ai/hint',async route=>{
    await route.fetch({url:route.request().url().replace(':8000',':8002')});
    dropped=true;
    await route.abort('connectionreset');
  });
  await page.getByRole('button',{name:'Ask for a clarifying hint'}).click();
  await expect(page.locator('.hint-response')).toHaveCount(1,{timeout:20000});
  expect(dropped).toBe(true);
  await expect(page.locator('main [role="alert"]')).toHaveCount(0);
  const sid=page.url().split('/').at(-1);
  const data=await (await request.get(`http://localhost:8002/sessions/${sid}`)).json();
  expect(data.summary.ai_requests).toBe(1);
  expect(data.summary.ai_responses).toBe(1);
});

test('refresh restores a pending AI request and preserves its single result',async({page,request})=>{
  await start(page);
  const sid=page.url().split('/').at(-1);
  await page.getByRole('button',{name:'Ask for a clarifying hint'}).click();
  await expect.poll(async()=>{
    const data=await (await request.get(`http://localhost:8002/sessions/${sid}`)).json();
    return data.summary.ai_requests;
  }).toBe(1);
  await page.reload();
  await expect(page.locator('.hint-response')).toHaveCount(1,{timeout:20000});
  await expect(page.locator('main [role="alert"]')).toHaveCount(0);
  const data=await (await request.get(`http://localhost:8002/sessions/${sid}`)).json();
  expect(data.summary.ai_requests).toBe(1);
  expect(data.summary.ai_responses).toBe(1);
});

test('multiple tabs preserve queued events and another session can sync past a rejected event',async({page,context,request})=>{
  await page.goto('/');
  const me=await (await request.get('http://localhost:8002/me')).json();
  const create=async()=> (await (await request.post('http://localhost:8002/sessions',{data:{event_id:crypto.randomUUID(),problem_domain:'math',problem_text:'Synthetic queue concurrency QA'}})).json()).id as string;
  const sid1=await create(),sid2=await create();
  const page2=await context.newPage();
  await page2.route('http://localhost:8000/**',route=>route.continue({url:route.request().url().replace(':8000',':8002')}));
  await page.goto(`/session/${sid1}`);
  await page2.goto(`/session/${sid2}`);
  await page.getByLabel('What have you tried, or what might work?').fill('First tab thought');
  await page2.getByLabel('What have you tried, or what might work?').fill('Second tab thought');
  await context.setOffline(true);
  await Promise.all([page.getByRole('button',{name:'Save my thinking'}).click(),page2.getByRole('button',{name:'Save my thinking'}).click()]);
  await expect(page.getByRole('status')).toContainText('2 events waiting to sync');
  await expect(page.getByRole('button',{name:'Save my thinking'})).toBeEnabled({timeout:30000});
  await expect(page2.getByRole('button',{name:'Save my thinking'})).toBeEnabled({timeout:30000});
  // An invalid event stays stored; it must not block unrelated sessions.
  await page.evaluate(({owner,badSession})=>{
    const event={event_id:crypto.randomUUID(),session_id:badSession,event_type:'attempt_submitted',payload:{attempt_text:'queued for nonexistent session',is_partial:true}};
    localStorage.setItem(`thinkfirst.event.${owner}.${event.event_id}`,JSON.stringify({event,queued_at:0}));
  },{owner:me.id,badSession:crypto.randomUUID()});
  await context.setOffline(false);
  await expect.poll(async()=> (await (await request.get(`http://localhost:8002/sessions/${sid1}`)).json()).events.filter((e:any)=>e.event_type==='attempt_submitted').length).toBe(1);
  await expect.poll(async()=> (await (await request.get(`http://localhost:8002/sessions/${sid2}`)).json()).events.filter((e:any)=>e.event_type==='attempt_submitted').length).toBe(1);
  await page.getByRole('button',{name:'Retry sync / refresh'}).click();
  await page.getByRole('button',{name:'Finish session'}).click();
  await expect(page.getByText('solved independently',{exact:true})).toBeVisible();
  await expect(page.getByRole('status')).toContainText('1 event waiting to sync');
});
