import {test,expect,Page} from '@playwright/test';

const sid='c415c65d-3275-40b4-bc43-6ca2c3132c2d';
async function fixture(page:Page,{lost=false,pending=false}={}){
  let title='Understanding loops',custom=false;
  const calls:{path:string;method:string;body?:any}[]=[];
  const events:any[]=[{id:'start',event_type:'session_started',payload:{problem_text:'Understanding loops'},created_at:new Date().toISOString()},
    {id:'answer',event_type:'ai_hint_delivered',payload:{tier:3,hint_text:'A loop repeats an operation.'},created_at:new Date().toISOString()}];
  const pendingId='6aa56bea-ef8a-4c51-b7f7-1ae4c6f65359';
  if(pending)events.push({id:pendingId,event_type:'ai_analysis_requested',payload:{},created_at:new Date().toISOString()});
  function deliver(id:string){const result={id:'review-result',event_type:'ai_analysis_delivered',created_at:new Date().toISOString(),payload:{request_event_id:id,source_fingerprint:'source-v1',text:'## What you explored\n\nYou explored a loop. Try tracing one iteration.'}};events.push(result);return result;}
  await page.route('http://localhost:8000/**',async route=>{
    const request=route.request(),url=new URL(request.url()),path=url.pathname;
    calls.push({path,method:request.method(),body:request.method()==='POST'?request.postDataJSON():undefined});
    let data:any;
    if(path==='/me')data={id:'history-fixture',display_name:'Fixture',admin:false,development:false};
    else if(path==='/ai/usage')data={daily_limit:30,requests_used:1,requests_remaining:29,resets_at:'2099-01-01T00:00:00Z'};
    else if(path===`/sessions/${sid}`)data={id:sid,status:'open',experience:'chat',mode:'ask_ai',title,custom_title:custom,events,summary:{},
      overview:{own_attempts:0,ai_questions:1,ai_answers:1,failed_requests:0,ai_reviews:events.filter(e=>e.event_type==='ai_analysis_delivered').length,initial_mode:'ask_ai',outcome:'open',status_label:'In progress',fingerprint:'source-v1',can_review:true}};
    else if(path===`/sessions/${sid}/title`){title=request.postDataJSON().title||'Understanding loops';custom=!!request.postDataJSON().title;data={title,custom_title:custom};}
    else if(path===`/sessions/${sid}/analysis`){
      const id=request.postDataJSON().event_id;
      events.push({id,event_type:'ai_analysis_requested',payload:{},created_at:new Date().toISOString()});
      data=deliver(id);
      if(lost){await route.abort('connectionreset');return;}
    }else if(path.startsWith('/ai/analyses/')){
      const result=events.find(e=>e.event_type==='ai_analysis_delivered')||deliver(pendingId);
      data={status:'delivered',result};
    }else if(path==='/history'){
      const items=Array.from({length:27},(_,i)=>({id:i===0?sid:`archive-${i}`,title:i===0?title:`Archive question ${i}`,custom_title:i===0&&custom,
        problem_text:i===0?'Understanding loops':`Archive question ${i}`,domain:'coding',status:'open',outcome:'open',status_label:'In progress',experience:'chat',started_at:'2026-09-16T10:00:00Z'}));
      const q=url.searchParams.get('q')||'',offset=Number(url.searchParams.get('offset')||0);
      const filtered=items.filter(item=>item.title.toLowerCase().includes(q.toLowerCase()));
      data={items:filtered.slice(offset,offset+25),total:filtered.length,offset,limit:25,has_more:offset+25<filtered.length};
    }else if(path==='/progress'){
      const guided=url.searchParams.get('experience')==='guided',n=guided?0:3;
      data={experience:guided?'guided':'chat',totals:{conversations:n,in_progress:n,completed:0,unfinished:0,own_attempts:n,ai_questions:n,ai_answers:n,failed_requests:0,ai_reviews:0,started_myself:0},
        modes:{both:n,own_only:0,ai_only:0,no_saved_work:0},weeks:[{week:'2026-09-14',own_attempts:n,ai_answers:n}],trend:guided?[]:[{week:'2026-09-14',ai_first_ratio:0.5,verification_rate:0,time_to_ai_seconds:8}],updated_at:'2026-09-16T10:00:00Z'};
    }else throw new Error(`Unexpected API request: ${path}`);
    await route.fulfill({json:data});
  });
  return calls;
}

test('history searches, paginates and opens a renamed conversation',async({page})=>{
  const calls=await fixture(page);
  await page.goto('/history');
  await expect(page.locator('.history-row')).toHaveCount(25);
  await page.getByRole('button',{name:'Next',exact:true}).click();
  await expect(page.locator('.history-row')).toHaveCount(2);
  await page.getByLabel('Search conversations',{exact:true}).fill('Understanding loops');
  await page.getByRole('button',{name:'Search',exact:true}).click();
  await expect(page.locator('.history-row')).toHaveCount(1);
  await page.locator('.history-row').click();
  await page.getByRole('button',{name:'Rename',exact:true}).click();
  await page.getByLabel('Conversation title',{exact:true}).fill('Loop practice notes');
  await page.getByRole('button',{name:'Save title',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Loop practice notes',exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByRole('heading',{name:'Loop practice notes',exact:true})).toBeVisible();
  expect(calls.filter(c=>c.path.endsWith('/analysis')||c.path==='/ai/hint')).toHaveLength(0);
});

test('review is explicit, recovers a lost response and does not regenerate on reload',async({page})=>{
  const calls=await fixture(page,{lost:true});
  await page.goto(`/session/${sid}`);
  await page.getByText('Review this conversation',{exact:true}).click();
  expect(calls.filter(c=>c.method==='POST')).toHaveLength(0);
  await page.getByRole('button',{name:'Generate AI review',exact:true}).click();
  await expect(page.locator('.saved-review')).toContainText('Try tracing one iteration.',{timeout:15000});
  await page.reload();
  await page.getByText('Review this conversation',{exact:true}).click();
  await expect(page.locator('.saved-review')).toContainText('Try tracing one iteration.');
  await expect(page.getByRole('button',{name:'Generate AI review',exact:true})).toHaveCount(0);
  expect(calls.filter(c=>c.path.endsWith('/analysis')&&c.method==='POST')).toHaveLength(1);
  expect(calls.filter(c=>c.path==='/ai/hint')).toHaveLength(0);
});

test('an already pending review resumes by polling without a new generation',async({page})=>{
  const calls=await fixture(page,{pending:true});
  await page.goto(`/session/${sid}`);
  await expect(page.locator('.saved-review')).toContainText('Try tracing one iteration.');
  expect(calls.filter(c=>c.path.startsWith('/ai/analyses/'))).toHaveLength(1);
  expect(calls.filter(c=>c.method==='POST')).toHaveLength(0);
});

test('progress separates study data, handles an empty view and fits mobile',async({page})=>{
  const calls=await fixture(page);
  await page.setViewportSize({width:390,height:844});
  await page.goto('/dashboard');
  await expect(page.locator('.progress-summary')).toContainText('3 everyday conversations');
  await expect(page.locator('.progress-charts .recharts-wrapper > svg.recharts-surface')).toHaveCount(3);
  await expect(page.locator('.progress-charts .recharts-cartesian-axis')).toHaveCount(6);
  await expect(page.locator('.progress-charts .recharts-line-dot').first()).toBeVisible();
  for(const chart of await page.locator('.progress-charts .recharts-wrapper').all())expect((await chart.boundingBox())!.width).toBeGreaterThan(200);
  await expect(page.getByRole('heading',{name:'Verification rate',exact:true})).toHaveCount(0);
  await page.screenshot({path:'test-results/progress-mobile.png',fullPage:true});
  await expect(page.getByRole('table')).toContainText('Your attempts');
  await page.getByLabel('Show activity for').selectOption('guided');
  await expect(page.locator('.progress-summary')).toContainText('no saved activity');
  await expect(page.getByRole('heading',{name:'Verification rate',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  expect(calls.filter(c=>c.method==='POST')).toHaveLength(0);
});
