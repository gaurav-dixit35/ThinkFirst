import {test,expect,Page} from '@playwright/test';

// Missing-provider and independent flows use the isolated QA API.
test.beforeEach(async({page})=>{
  await page.route('http://localhost:8000/**',route=>route.continue({url:route.request().url().replace(':8000',':8001')}));
});
async function ownConversation(page:Page,question:string) {
  await page.goto('/');
  await page.getByLabel('Your question',{exact:true}).fill(question);
  await page.locator('.question-composer').getByRole('button',{name:'Try myself',exact:true}).click();
  await page.getByRole('button',{name:'Start thinking',exact:true}).click();
  await expect(page.locator('.conversation-heading h1')).toBeVisible();
}

test('question-first home uses the supplied logo and has no provider controls',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'What would you like help with?'})).toBeVisible();
  await expect(page.getByLabel('Your question',{exact:true})).toBeVisible();
  await expect(page.locator('.home-logo')).toHaveAttribute('src','/logo.png');
  await expect(page.getByRole('region',{name:'AI connection'})).toHaveCount(0);
  await expect(page.locator('.metric-grid')).toHaveCount(0);
});

test('independent completion needs no AI or reflection form',async({page})=>{
  await ownConversation(page,'QA: plan a focused study session');
  await page.getByLabel('What would you try?').fill('Pick one topic, work for 25 minutes, and summarise it.');
  await page.getByRole('button',{name:'Save my thinking'}).click();
  await expect(page.locator('.own-attempt')).toHaveCount(1);
  await page.getByRole('button',{name:'Complete conversation'}).click();
  await expect(page.getByText(/Completed.*saved in history/)).toBeVisible();
});

test('offline attempts sync once and other navigation preserves the conversation',async({page,context,request})=>{
  await ownConversation(page,'QA: offline recovery and navigation');
  const sid=page.url().split('/').at(-1);
  await context.setOffline(true);
  await page.getByLabel('What would you try?').fill('An offline thought that must survive.');
  await page.getByRole('button',{name:'Save my thinking'}).click();
  await expect(page.getByRole('status')).toContainText('1 event waiting to sync');
  await expect(page.getByRole('button',{name:'Save my thinking'})).toBeEnabled({timeout:30000});
  await context.setOffline(false);
  await expect(page.locator('.own-attempt')).toHaveCount(1,{timeout:30000});
  await page.getByRole('link',{name:'History',exact:true}).click();
  const data=await (await request.get(`http://localhost:8001/sessions/${sid}`)).json();
  expect(data.status).toBe('open');
  expect(data.events.filter((e:any)=>e.event_type==='attempt_submitted')).toHaveLength(1);
  await page.goto(`/session/${sid}`);
  await expect(page.locator('.own-attempt')).toHaveCount(1);
});

test('draft and selected mode survive reload without an AI request',async({page,request})=>{
  await ownConversation(page,'QA: keep my unfinished idea');
  await page.getByLabel('What would you try?').fill('My unfinished approach.');
  await page.reload();
  await expect(page.getByLabel('What would you try?')).toHaveValue('My unfinished approach.');
  const sid=page.url().split('/').at(-1);
  const data=await (await request.get(`http://localhost:8001/sessions/${sid}`)).json();
  expect(data.mode).toBe('try_myself');
  expect(data.summary.ai_requests).toBe(0);
});

test('direct AI failure is recoverable without showing infrastructure controls',async({page})=>{
  await page.goto('/new');
  await page.getByLabel('Your question',{exact:true}).fill('QA: direct answer with no configured provider');
  await page.locator('.composer-actions').getByRole('button',{name:'Ask AI',exact:true}).click();
  await expect(page.locator('main [role="alert"]')).toContainText('AI could not reply right now');
  await expect(page.getByRole('region',{name:'AI connection'})).toHaveCount(0);
  await page.getByRole('button',{name:'Complete conversation'}).click();
  await expect(page.getByText(/Completed.*saved in history/)).toBeVisible();
});

test('mobile home fits and historical guided sessions still open',async({page,request})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await expect(page.getByLabel('Your question',{exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  const result=await request.post('http://localhost:8001/sessions',{data:{event_id:crypto.randomUUID(),problem_domain:'math',problem_text:'QA: historical guided session'}});
  const {id}=await result.json();
  await page.goto(`/session/${id}`);
  await expect(page.getByRole('heading',{name:'One thought at a time.'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Skip, ask AI now'})).toBeVisible();
});
