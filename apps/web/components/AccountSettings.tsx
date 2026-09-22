'use client';
import {useClerk,useUser} from '@clerk/nextjs';
import {useState} from 'react';
import {useIdentity} from './Providers';

function HostedAccount(){
  const {user}=useUser(),clerk=useClerk();
  const [error,setError]=useState(''),[busy,setBusy]=useState(false);
  return <><p className="account-name">{user?.fullName||user?.username||'Your account'}</p><p>{user?.primaryEmailAddress?.emailAddress}</p><div className="settings-actions"><button className="secondary" onClick={()=>clerk.openUserProfile()}>Manage account</button><button className="text-button" disabled={busy} onClick={async()=>{setBusy(true);try{await clerk.signOut();}catch{setError('Could not sign out. Please try again.');setBusy(false);}}}>{busy?'Signing out…':'Sign out'}</button></div><p className="field-help">Manage your sign-in methods and active sessions in your account. Unsent drafts stay on this browser.</p>{error&&<p role="alert">{error}</p>}</>;
}
export default function AccountSettings(){
  const identity=useIdentity();
  if(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY&&!identity?.development)return <HostedAccount/>;
  return <><span className="settings-badge">Local workspace</span><p>This device is using the shared development account. Your work is saved on this ThinkFirst installation; this is not a private online account.</p><details><summary>Enable sign-in and separate accounts</summary><p>Account sign-in is built in, but Clerk is not configured for this installation. The operator needs to configure the Clerk issuer, publishable key, secret key and website/API origins, then rebuild the website and restart the API.</p><p className="field-help">Setup steps are in docs/operations.md. Existing local conversations stay with the development account; they are not automatically assigned to a new login.</p></details></>;
}
