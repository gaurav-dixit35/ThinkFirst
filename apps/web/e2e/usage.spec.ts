import {test,expect,Page} from '@playwright/test';

const sid='f7613d01-14ce-457c-b512-18c0a0bf9dce';
const richAnswer='## A clear answer\n\nUse **four**. Here is the check:\n\n$$\n2(4)+3=11\n$$\n\n```python\nprint(2 * 4 + 3)\n```\n\n| Step | Result |\n| --- | --- |\n| Substitute | 11 |\n\n<script>window.answerExecuted=true</script>\n\n![tracker](https://tracker.invalid/pixel)\n\n[unsafe](javascript:alert(1))';

async function fixture(page:Page,reject=false) {
  const events:any[]=[
    {id:'start',event_type:'session_started',payload:{problem_text:'Solve 2x + 3 = 11'},created_at:new Date().toISOString()},
    {id:'answer',event_type:'ai_hint_delivered',payload:{tier:3,hint_text:richAnswer},created_at:new Date().toISOString()},
  ];
  const sent:any[]=[];
  let mode='ask_ai';
  await page.route('http://localhost:8000/**',async route=>{
    const path=new URL(route.request().url()).pathname;
    let data:any;
    if(path==='/me')data={id:'ui-fixture',display_name:'UI fixture',admin:false,development:true};
    else if(path==='/ai/usage')data={daily_limit:30,requests_used:reject?30:1,requests_remaining:reject?0:29,resets_at:'2099-01-01T00:00:00Z'};
    else if(path===`/sessions/${sid}`)data={id:sid,status:'open',experience:'chat',mode,events,summary:{}};
    else if(path==='/events'){
      const body=route.request().postDataJSON();
      if(body.event_type==='conversation_mode_changed')mode=body.payload.mode;
      data={id:body.event_id,event_type:body.event_type,payload:body.payload,created_at:new Date().toISOString()};
      events.push(data);
    }else if(path==='/ai/hint'){
      const body=route.request().postDataJSON();sent.push(body);
      if(reject){await route.fulfill({status:429,json:{detail:'Your daily AI allowance is used up. You can still save your own thinking.'}});return;}
      data={id:'second-answer',event_type:'ai_hint_delivered',payload:{tier:3,hint_text:'More explanation.',request_event_id:body.event_id},created_at:new Date().toISOString()};
      events.push(data);
    }else throw new Error(`Unexpected API call: ${path}`);
    await route.fulfill({json:data});
  });
  return sent;
}

test('answers render safe math, code and tables with working copy controls on mobile',async({page,context})=>{
  await context.grantPermissions(['clipboard-read','clipboard-write']);
  await fixture(page);
  const external:string[]=[];
  page.on('request',request=>{if(request.url().includes('tracker.invalid'))external.push(request.url());});
  await page.setViewportSize({width:390,height:844});
  await page.goto(`/session/${sid}`);
  await expect(page.locator('.answer-markdown table')).toBeVisible();
  await expect(page.locator('.katex-html')).toBeVisible();
  await expect(page.locator('.answer-code pre')).toContainText('print(2 * 4 + 3)');
  await page.getByRole('button',{name:'Copy code',exact:true}).click();
  await expect.poll(()=>page.evaluate(async()=>(await navigator.clipboard.readText()).replace(/\r\n/g,'\n'))).toBe('print(2 * 4 + 3)\n');
  await page.getByRole('button',{name:'Copy answer',exact:true}).click();
  await expect.poll(()=>page.evaluate(async()=>(await navigator.clipboard.readText()).replace(/\r\n/g,'\n'))).toBe(richAnswer);
  expect(await page.evaluate(()=>Boolean((window as any).answerExecuted))).toBe(false);
  expect(await page.getByText('unsafe',{exact:true}).getAttribute('href')).not.toContain('javascript:');
  expect(external).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});

test('answer preference reaches the request and allowance failure preserves thinking',async({page})=>{
  const sent=await fixture(page,true);
  await page.goto(`/session/${sid}`);
  await expect(page.getByText(/0 of 30 AI requests left/)).toBeVisible();
  await page.getByLabel('Answer length').selectOption('detailed');
  await page.getByLabel('Your message',{exact:true}).fill('Explain the steps');
  await page.getByRole('button',{name:'Send',exact:true}).click();
  await expect(page.locator('main [role="alert"]')).toContainText('daily AI allowance');
  expect(sent).toHaveLength(1);
  expect(sent[0].answer_style).toBe('detailed');
  await expect(page.getByLabel('Your message',{exact:true})).toHaveValue('Explain the steps');
  await page.getByRole('button',{name:'Try myself',exact:true}).click();
  await page.getByLabel('What would you try?').fill('I can substitute 4 to check the result.');
  await page.getByRole('button',{name:'Save my thinking',exact:true}).click();
  await expect(page.locator('.own-attempt')).toContainText('substitute 4');
  expect(sent).toHaveLength(1);
});
