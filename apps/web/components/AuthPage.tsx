'use client';
import Link from 'next/link';
import {SignIn, SignUp, SignedIn, SignedOut, ClerkLoaded, ClerkLoading, useClerk} from '@clerk/nextjs';
import {useState} from 'react';

function ExistingAccount() {
  const clerk = useClerk();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  return <div className="auth-notice"><h2>You’re signed in.</h2><p>Continue to your workspace, or sign out to use another account.</p><Link className="primary" href="/">Open ThinkFirst</Link><button className="text-button" disabled={busy} onClick={async()=>{setBusy(true);setError('');try{await clerk.signOut({redirectUrl:'/login'});}catch{setError('Could not sign out. Please try again.');setBusy(false);}}}>{busy?'Signing out…':'Sign out'}</button>{error&&<p role="alert">{error}</p>}</div>;
}
export default function AuthPage({mode}:{mode:'login'|'signup'}) {
  const configured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);
  return <div className="auth-page"><Link className="brand auth-brand" href="/"><img src="/logo.png" alt="" width={44} height={44}/>ThinkFirst</Link><header className="auth-heading"><h1>{mode==='login'?'Welcome back.':'A little space to think.'}</h1><p>{mode==='login'?'Pick up your conversations and keep exploring.':'Ask for help, try your own ideas, and keep your progress together.'}</p></header>
    {configured ? <><ClerkLoading><p role="status">Loading secure sign-in…</p></ClerkLoading><ClerkLoaded><SignedIn><ExistingAccount/></SignedIn><SignedOut><div className="auth-form">{mode==='login'?<SignIn routing="path" path="/login" signUpUrl="/signup" fallbackRedirectUrl="/"/>:<SignUp routing="path" path="/signup" signInUrl="/login" fallbackRedirectUrl="/"/>}</div></SignedOut></ClerkLoaded></> : <div className="auth-notice"><h2>Accounts aren’t connected yet.</h2><p>This installation is using a shared local workspace. Personal sign-in will be available once the operator finishes account setup.</p><Link className="primary" href="/">Return to ThinkFirst</Link><Link className="text-button" href="/help">Get help</Link></div>}
    <footer className="auth-footer"><p>Your conversations belong to your signed-in account. Research sharing is optional.</p><nav aria-label="Account help"><Link href="/help">Help</Link><Link href="/privacy">Privacy</Link></nav></footer>
  </div>;
}
