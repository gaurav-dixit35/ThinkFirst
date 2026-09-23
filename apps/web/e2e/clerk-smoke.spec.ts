import {test,expect} from '@playwright/test';
// Run only against the real Clerk-enabled local build, not synthetic QA.
test.skip(process.env.CLERK_SMOKE!=='1','Requires the separately running Clerk-enabled website.');
test('real Clerk login and signup render without server errors',async({page,request})=>{
 for(const path of ['/','/login','/signup','/help','/privacy','/settings']){
  const response=await request.get(path);expect(response.status(),path).toBe(200);
 }
 await page.goto('/login');await expect(page.locator('.cl-signIn-root')).toBeVisible({timeout:45000});
 await expect(page.locator('.cl-signIn-root input:not([type=hidden])').first()).toBeVisible();
 await page.goto('/signup');await expect(page.locator('.cl-signUp-root')).toBeVisible({timeout:45000});
 await expect(page.locator('.cl-signUp-root input:not([type=hidden])').first()).toBeVisible();
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.screenshot({path:'../../artifacts/screenshots/clerk-signup.png',fullPage:true});
});
