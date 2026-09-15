import type {Metadata} from 'next';
import Providers from '@/components/Providers';
import Shell from '@/components/Shell';
import './globals.css';
export const metadata: Metadata = {title: 'ThinkFirst — A little space to think', description: 'Your thinking, supported by AI. A reflective problem-solving research workspace.'};
export default function RootLayout({children}: {children: React.ReactNode}) {return <html lang="en"><body><Providers><Shell>{children}</Shell></Providers></body></html>;}
