'use client';
import Link from 'next/link';
import {usePathname} from 'next/navigation';
import {ChartNoAxesCombined, History, Plus, Settings2} from 'lucide-react';

export default function Shell({children}:{children:React.ReactNode}) {
  const path=usePathname();
  const isNew=path==='/'||path==='/new';
  const title=path.startsWith('/session')?'Conversation':path==='/history'?'History':path==='/dashboard'?'Progress':path==='/settings'?'Settings':path==='/research'?'Research':'New conversation';
  return <div className="app-shell"><aside className="sidebar simple-sidebar">
    <Link className="brand" href="/"><img className="brand-logo" src="/logo.png" alt="" width={38} height={38}/>ThinkFirst</Link>
    <nav aria-label="Main navigation">{[
      {href:'/',label:'New conversation',Icon:Plus,active:isNew},
      {href:'/history',label:'History',Icon:History,active:path==='/history'},
      {href:'/dashboard',label:'Progress',Icon:ChartNoAxesCombined,active:path==='/dashboard'},
    ].map(({href,label,Icon,active})=><Link key={href} href={href} aria-current={active?'page':undefined} className={active?'nav-link active':'nav-link'}><Icon size={18}/>{label}</Link>)}</nav>
    <div className="sidebar-bottom"><Link href="/settings" className="nav-link"><Settings2 size={18}/>Settings</Link></div>
  </aside><div className="main-shell"><header className="topbar"><span>{title}</span><Link href="/settings" className="mobile-settings" aria-label="Settings"><Settings2 size={18}/></Link></header><main>{children}</main></div></div>;
}
