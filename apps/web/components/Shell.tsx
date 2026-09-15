'use client';
import Link from 'next/link';
import {usePathname, useRouter} from 'next/navigation';
import {useState} from 'react';
import {beforeNavigation} from '@/lib/navigation';
import {ArrowUpRight, BookOpen, ChartNoAxesCombined, Feather, History, Plus, Settings2} from 'lucide-react';
import {useIdentity} from './Providers';

export default function Shell({children}: {children: React.ReactNode}) {
  const path = usePathname();
  const router = useRouter();
  const [navigationError,setNavigationError] = useState('');
  const identity = useIdentity();
  return <div className="app-shell" onClickCapture={e=>{const anchor=(e.target as HTMLElement).closest('a');const href=anchor?.getAttribute('href');if(path.startsWith('/session/')&&href?.startsWith('/')&&href!==path&&!e.ctrlKey&&!e.metaKey){e.preventDefault();e.stopPropagation();beforeNavigation().then(()=>router.push(href)).catch(error=>setNavigationError(error.message));}}}><aside className="sidebar">
    <Link className="brand" href="/"><span className="brand-symbol"><Feather size={21}/></span>thinkfirst<span className="brand-dot">.</span></Link>
    <div className="workspace-label">YOUR WORKSPACE</div>
    <nav aria-label="Main navigation">{[
      {href: '/', label: 'Overview', Icon: ChartNoAxesCombined},
      {href: '/new', label: 'Thinking space', Icon: BookOpen},
      {href: '/history', label: 'Session history', Icon: History},
      {href: '/dashboard', label: 'Your patterns', Icon: ChartNoAxesCombined},
    ].map(({href, label, Icon}) => <Link key={href} href={href} className={(path === href || href === '/new' && path.startsWith('/session')) ? 'nav-link active' : 'nav-link'}><Icon size={18}/>{label}{path === href && <span className="nav-dot"/>}</Link>)}</nav>
    <div className="sidebar-note"><div className="note-mark">“</div><p>A little pause.<br/>A different perspective.</p><span>Make room for your own thinking.</span></div>
    <div className="sidebar-bottom"><Link href="/settings" className="nav-link"><Settings2 size={18}/> Settings & about</Link><div className="profile"><span className="avatar">{identity?.development ? 'LP' : 'TF'}</span><div><strong>{identity?.development ? 'Local participant' : 'Your workspace'}</strong><small>{identity?.development ? 'Development workspace' : 'Research participant'}</small></div></div></div>
  </aside><div className="main-shell"><header className="topbar"><div className="breadcrumb">Your workspace <span>/</span> <strong>{path === '/' ? 'Overview' : path.startsWith('/session') ? 'Thinking space' : path.slice(1).replace('new', 'Thinking space')}</strong></div><span className="research-tag"><span/> A space for thoughtful progress</span><Link href="/settings" className="mobile-settings" aria-label="Settings and about"><Settings2 size={17}/></Link></header><main>{navigationError&&<div className="error" role="alert">{navigationError}<button onClick={()=>setNavigationError('')}>Dismiss</button></div>}{children}</main><footer><span>Think independently. Explore with AI. Reflect on both.</span><span>THINKFIRST <ArrowUpRight size={12}/></span></footer></div></div>;
}
