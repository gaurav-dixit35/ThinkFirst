import {test,expect,Page} from '@playwright/test';

test.beforeEach(async({page})=>{
  await page.route('http://localhost:8000/**',route=>route.continue({url:route.request().url().replace(':8000',':8002')}));
});
async function start(page:Page) {
  await page.goto('/new');
  await page.getByLabel('Your question',{exact:true}).fill('Synthetic QA: solve 2x + 3 = 11');
  await page.locator('.composer-actions').getByRole('button',{name:'Ask AI',exact:true}).click();
}

test('direct answer, follow-up and optional thinking share one conversation',async({page,request})=>{
  await start(page);
  await expect(page.locator('.assistant-message')).toHaveCount(1);
  await page.getByLabel('Your message',{exact:true}).fill('Why subtract from both sides?');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.locator('.assistant-message')).toHaveCount(2);
  await page.getByRole('button',{name:'Try myself',exact:true}).click();
  await page.getByLabel('What would you try?').fill('I would check by substituting x = 4.');
  await page.getByRole('button',{name:'Get a hint',exact:true}).click();
  await expect(page.locator('.assistant-message')).toHaveCount(3);
  await expect(page.locator('.own-attempt')).toHaveCount(1);
  await page.getByRole('button',{name:'Show an answer',exact:true}).click();
  await expect(page.locator('.assistant-message')).toHaveCount(4);
  await expect(page.locator('main [role="alert"]')).toHaveCount(0);
  const sid=page.url().split('/').at(-1);
  const data=await (await request.get(`http://localhost:8002/sessions/${sid}`)).json();
  expect(data.summary.ai_requests).toBe(4);
  expect(data.events.filter((e:any)=>e.event_type==='ai_hint_delivered').every((e:any)=>e.payload.provider==='gemini')).toBe(true);
  expect(data.events.some((e:any)=>e.event_type==='ai_provider_attempted'&&e.payload.provider==='groq'&&['failed','skipped'].includes(e.payload.outcome))).toBe(true);
  expect(data.events.some((e:any)=>e.event_type==='verification_skipped')).toBe(false);
  await page.getByRole('button',{name:'Complete conversation'}).click();
  await expect(page.getByText(/Completed.*saved in history/)).toBeVisible();
  await expect(page.locator('.conversation-messages')).toContainText('Why subtract from both sides?');
});

test('lost HTTP response recovers without duplicate generation',async({page,request})=>{
  let dropped=false;
  await page.route('http://localhost:8000/ai/hint',async route=>{
    await route.fetch({url:route.request().url().replace(':8000',':8002')});
    dropped=true;
    await route.abort('connectionreset');
  });
  await start(page);
  await expect(page.locator('.assistant-message')).toHaveCount(1,{timeout:20000});
  expect(dropped).toBe(true);
  await expect(page.locator('main [role="alert"]')).toHaveCount(0);
  const sid=page.url().split('/').at(-1);
  const data=await (await request.get(`http://localhost:8002/sessions/${sid}`)).json();
  expect(data.summary.ai_requests).toBe(1);
  expect(data.summary.ai_responses).toBe(1);
});

test('refresh recovers a pending answer without a second request',async({page,request})=>{
  await start(page);
  await expect(page.locator('.conversation-heading h1')).toBeVisible();
  const sid=page.url().split('/').at(-1);
  await expect.poll(async()=> (await (await request.get(`http://localhost:8002/sessions/${sid}`)).json()).summary.ai_requests).toBe(1);
  await page.reload();
  await expect(page.locator('.assistant-message')).toHaveCount(1,{timeout:20000});
  const data=await (await request.get(`http://localhost:8002/sessions/${sid}`)).json();
  expect(data.summary.ai_requests).toBe(1);
  await expect(page.locator('main [role="alert"]')).toHaveCount(0);
});

test('visiting a saved conversation does not request AI again',async({page,request})=>{
  await start(page);
  await expect(page.locator('.assistant-message')).toHaveCount(1);
  const url=page.url();
  const sid=url.split('/').at(-1);
  await page.getByRole('link',{name:'History',exact:true}).click();
  await page.goto(url);
  await expect(page.locator('.assistant-message')).toHaveCount(1);
  const data=await (await request.get(`http://localhost:8002/sessions/${sid}`)).json();
  expect(data.status).toBe('open');
  expect(data.summary.ai_requests).toBe(1);
});
