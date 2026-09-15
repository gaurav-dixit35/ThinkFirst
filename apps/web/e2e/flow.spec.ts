import {test,expect} from '@playwright/test';

// Exercise real HTTP/database behavior in the isolated QA database.
test.beforeEach(async({page})=>{
  await page.route('http://localhost:8000/**',route=>route.continue({url:route.request().url().replace(':8000',':8001')}));
});

test('independent completion persists a real timeline',async({page})=>{
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Good things start with a pause.'})).toBeVisible();
  await expect(page.locator('.refresh-note')).toBeVisible();
  await page.screenshot({path:'../../artifacts/overview-desktop.png',fullPage:true});
  await page.getByRole('link',{name:'Start a new session'}).click();
  await page.getByLabel('The problem or question').fill('Browser verification: how can I organize a focused study session?');
  await page.getByRole('button',{name:'Start thinking',exact:true}).click();
  await expect(page.getByRole('heading',{name:'One thought at a time.'})).toBeVisible();
  await page.getByLabel('What have you tried, or what might work?').fill('I will pick one topic, work for 25 minutes, and summarize what I learned.');
  await page.getByRole('button',{name:'Save my thinking'}).click();
  await expect(page.getByText('SAVED ATTEMPT',{exact:true})).toBeVisible();
  await page.screenshot({path:'../../artifacts/session-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Finish session'}).click();
  await expect(page.getByText('solved independently',{exact:true})).toBeVisible();
});

test('offline attempt queues visibly and reconnect sends it exactly once',async({page,context})=>{
  await page.goto('/new');
  await page.getByLabel('The problem or question').fill('Browser verification: offline recovery');
  await page.getByRole('button',{name:'Start thinking',exact:true}).click();
  await expect(page.getByRole('heading',{name:'One thought at a time.'})).toBeVisible();
  await context.setOffline(true);
  await page.getByLabel('What have you tried, or what might work?').fill('An offline thought that must survive reconnect.');
  await page.getByRole('button',{name:'Save my thinking'}).click();
  await expect(page.getByRole('status')).toContainText('1 event waiting to sync');
  await expect(page.getByRole('button',{name:'Save my thinking'})).toBeEnabled({timeout:30000});
  await context.setOffline(false);
  await expect(page.getByRole('status')).toHaveCount(0,{timeout:30000});
  await page.getByRole('button',{name:'Retry sync / refresh'}).click();
  await expect(page.getByText('SAVED ATTEMPT',{exact:true})).toHaveCount(1);
  await page.getByRole('button',{name:'Finish session'}).click();
  await expect(page.getByText('solved independently',{exact:true})).toBeVisible();
});

test('skip is immediate and missing provider is visible',async({page})=>{
  await page.goto('/new');
  await page.getByLabel('The problem or question').fill('Browser verification: an optional attempt');
  await page.getByRole('button',{name:'Start thinking',exact:true}).click();
  await page.getByRole('button',{name:'Skip, ask AI now'}).click();
  await page.getByRole('button',{name:'Ask for a clarifying hint'}).click();
  await expect(page.locator('main [role="alert"]')).toContainText('AI assistance is not configured');
  await page.getByRole('button',{name:'Leave unfinished'}).click();
  await expect(page.getByText('abandoned',{exact:true})).toBeVisible();
});

test('mobile overview fits viewport and navigation works',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Good things start with a pause.'})).toBeVisible();
  await expect(page.locator('.refresh-note')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.screenshot({path:'../../artifacts/overview-mobile.png',fullPage:true});
  await page.getByRole('link',{name:'Session history',exact:true}).click();
  await expect(page.getByRole('heading',{name:'A history of your thinking.'})).toBeVisible();
});

test('AI setup is visible before requesting and unsaved drafts survive reload',async({page})=>{
  page.on('dialog', dialog=>dialog.accept());
  await page.goto('/new');
  await page.getByLabel('The problem or question').fill('Browser verification: draft recovery');
  await page.getByRole('button',{name:'Start thinking',exact:true}).click();
  await expect(page.getByRole('region',{name:'AI connection'})).toContainText('AI is not connected yet');
  await page.getByLabel('What have you tried, or what might work?').fill('I want this unfinished thought to survive a refresh.');
  await page.reload();
  await expect(page.getByLabel('What have you tried, or what might work?')).toHaveValue('I want this unfinished thought to survive a refresh.');
  await page.getByRole('button',{name:'Save my thinking'}).click();
  await expect(page.getByText('SAVED ATTEMPT',{exact:true})).toHaveCount(1);
  await page.reload();
  await expect(page.getByLabel('Add another thought')).toHaveValue('');
  await page.getByRole('button',{name:'Finish session'}).click();
  await expect(page.getByText('solved independently',{exact:true})).toBeVisible();
});

test('provider choice is sent to the API and failed AI does not prevent completion',async({page})=>{
  await page.goto('/new');
  await page.getByLabel('The problem or question').fill('Browser verification: choose providers and finish after failure');
  await page.getByRole('button',{name:'Start thinking',exact:true}).click();
  await page.getByText('AI setup details',{exact:true}).click();
  const selector=page.getByLabel('Preferred AI provider');
  for(const value of ['gemini','groq','mistral','cloudflare','openrouter']) {
    await selector.selectOption(value);
    await expect(selector).toHaveValue(value);
  }
  await page.getByRole('button',{name:'Skip, ask AI now'}).click();
  const requestPromise=page.waitForRequest(r=>r.url().endsWith('/ai/hint')&&r.method()==='POST');
  await page.getByRole('button',{name:'Ask for a clarifying hint'}).click();
  expect((await requestPromise).postDataJSON().provider).toBe('openrouter');
  await expect(page.locator('main [role="alert"]')).toContainText('AI assistance is not configured');
  await page.getByRole('button',{name:'Finish session'}).click();
  await expect(page.getByText('solved without ai response',{exact:true})).toBeVisible();
});
