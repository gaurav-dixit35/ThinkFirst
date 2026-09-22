import {test,expect} from '@playwright/test';

test('help and data notice stay public when the account API is unavailable',async({page})=>{
  const paths:string[]=[];
  await page.route('http://localhost:8000/**',async route=>{
    const path=new URL(route.request().url()).pathname;
    paths.push(path);
    if(path==='/service-info')await route.fulfill({json:{operator:'Pilot support',support_email:'help@example.com'}});
    else await route.fulfill({status:503,json:{detail:'Account service unavailable.'}});
  });
  await page.goto('/help');
  await expect(page.getByRole('heading',{name:'A little help getting started.'})).toBeVisible();
  await expect(page.getByRole('link',{name:'help@example.com'})).toHaveAttribute('href','mailto:help@example.com');
  await page.getByRole('link',{name:'Privacy and your data'}).click();
  await expect(page.getByRole('heading',{name:'Privacy at ThinkFirst'})).toBeVisible();
  expect(paths.every(path=>path==='/service-info')).toBe(true);
});

test('connection failures give a safe support reference',async({page})=>{
  const reference='b3a186e3-c507-4394-9a08-b765592f4c09';
  await page.route('http://localhost:8000/**',route=>route.fulfill({status:503,headers:{'X-Request-ID':reference,'Access-Control-Expose-Headers':'X-Request-ID'},json:{detail:'Temporarily unavailable.'}}));
  await page.goto('/settings');
  await expect(page.getByText(`Temporarily unavailable. Reference: ${reference}`)).toBeVisible();
  await expect(page.getByRole('button',{name:'Try again'})).toBeVisible();
});
