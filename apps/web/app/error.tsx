'use client';
export default function ErrorPage({reset}:{reset:()=>void}){return <div className="connection-state"><h1>This page needs another try.</h1><p>Your saved sessions are still there. Reload this view to continue.</p><button className="primary" onClick={reset}>Try again</button></div>;}
