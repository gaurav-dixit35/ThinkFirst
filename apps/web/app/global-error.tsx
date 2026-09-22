'use client';
export default function GlobalError({reset}: {error:Error & {digest?:string};reset:()=>void}) {
  return <html lang="en"><body><main style={{maxWidth:560,margin:'10vh auto',padding:24,fontFamily:'system-ui'}}><h1>ThinkFirst couldn’t open.</h1><p>Please try again. Your previously saved conversations remain in your account.</p><button onClick={reset}>Try again</button><p><a href="/help">Get help</a></p></main></body></html>;
}
