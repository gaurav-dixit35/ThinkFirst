'use client';
import {ClerkProvider, SignedIn, SignedOut, useAuth, UserButton} from '@clerk/nextjs';
import {createContext, useContext, useEffect, useState} from 'react';
import Link from 'next/link';
import {isAccountPage} from '@/lib/publicPages';
import {usePathname} from 'next/navigation';
import {api, ApiError, setTokenProvider} from '@/lib/api';
import {flushQueue, queueStatus, setQueueOwner} from '@/lib/eventClient';
import {setStorageOwner} from '@/lib/browserStorage';
import {PrivacyWelcome, PrivacyState} from './DataControls';

type Identity = {id: string; display_name: string; admin: boolean; development: boolean; privacy?:PrivacyState};
const IdentityContext = createContext<Identity | null>(null);
export const useIdentity = () => useContext(IdentityContext);

function Connection({children}: {children: React.ReactNode}) {
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [error, setError] = useState('');
  const [authError, setAuthError] = useState(false);
  const [queue, setQueue] = useState({count: 0, error: ''});
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    api<Identity>('/me').then(value => { if (active) { if (process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && value.development) throw new Error('Account sign-in and the API are using different configurations. Set AUTH_MODE=clerk on the API and restart it.'); setStorageOwner(value.id,value.development,value.privacy?.last_erased_at,value.privacy?.erased_session_ids); setQueueOwner(value.id); setIdentity(value); if ((value.development||value.privacy?.acknowledged)&&value.privacy?.deletion_request?.status!=='pending') return flushQueue(); } })
      .catch(e => { if (active) { setError(e.message); setAuthError(e instanceof ApiError && e.status === 401); } });
    const sync = () => { flushQueue().catch(e => setError(e.message)); };
    const changed = () => setQueue(queueStatus());
    window.addEventListener('online', sync);
    window.addEventListener('thinkfirst:queue', changed);
    window.addEventListener('storage', changed);
    return () => { active = false; setQueueOwner(null); setStorageOwner(null); window.removeEventListener('online', sync); window.removeEventListener('thinkfirst:queue', changed); window.removeEventListener('storage', changed); };
  }, [retry]);
  return <IdentityContext.Provider value={identity}>
    {(queue.count > 0 || queue.error) && <div className="sync-banner" role="status">{queue.count} event{queue.count === 1 ? '' : 's'} waiting to sync. {queue.error}<button onClick={() => flushQueue().catch(e => setError(e.message))}>Retry sync</button></div>}
    {!identity ? <div className="connection-state"><span className="eyebrow">THINKFIRST</span><h1>{error ? 'Let’s reconnect.' : 'Opening your workspace…'}</h1><p>{error || 'Connecting to your saved sessions.'}</p>{authError && <Link className="secondary" href="/login">Sign in again</Link>}{error && <button className="primary" onClick={() => {setError(''); setAuthError(false); setRetry(v => v + 1);}}>Try again</button>}</div> : !identity.development&&identity.privacy&&!identity.privacy.acknowledged ? <PrivacyWelcome onDone={privacy=>{setIdentity({...identity,privacy});void flushQueue().catch(e=>setError(e.message));}}/> : children}
  </IdentityContext.Provider>;
}
function ClerkConnection({children}: {children: React.ReactNode}) {
  const {getToken, isLoaded, userId} = useAuth();
  const path = usePathname();
  const returnTo = encodeURIComponent(path);
  const [ready, setReady] = useState(false);
  useEffect(() => {setTokenProvider(getToken); setReady(true); return () => setTokenProvider(null);}, [getToken]);
  if (!isLoaded || !ready) return <div className="connection-state">Loading sign-in…</div>;
  return <><SignedIn><Connection key={userId}>{children}</Connection><div className="user-control"><UserButton afterSignOutUrl="/login" /></div></SignedIn><SignedOut><div className="connection-state"><span className="eyebrow">A LITTLE SPACE TO THINK</span><h1>Your thinking comes first.</h1><p>Sign in to keep your attempts, hints, and reflections together.</p><div className="settings-actions"><Link className="primary" href={`/login?redirect_url=${returnTo}`}>Sign in to ThinkFirst</Link><Link className="secondary" href={`/signup?redirect_url=${returnTo}`}>Create an account</Link></div><p><Link href="/help">Help</Link> · <Link href="/privacy">Privacy</Link></p></div></SignedOut></>;
}
export default function Providers({children}: {children: React.ReactNode}) {
  const path = usePathname();
  const publicPage = path === '/help' || path === '/privacy' || isAccountPage(path);
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) return publicPage ? <>{children}</> : <Connection>{children}</Connection>;
  return <ClerkProvider signInUrl="/login" signUpUrl="/signup" signInFallbackRedirectUrl="/" signUpFallbackRedirectUrl="/" afterSignOutUrl="/login">{publicPage ? children : <ClerkConnection>{children}</ClerkConnection>}</ClerkProvider>;
}
