'use client';
import Link from 'next/link';
export default function ErrorPage({reset}: {error:Error & {digest?:string};reset:()=>void}) {
  return <section className="connection-state" role="alert"><h1>This page couldn’t open.</h1><p>Try opening it again. You can also return to your saved conversations.</p><div className="settings-actions"><button className="primary" onClick={reset}>Try again</button><Link className="secondary" href="/history">Open history</Link><Link href="/help">Get help</Link></div></section>;
}
