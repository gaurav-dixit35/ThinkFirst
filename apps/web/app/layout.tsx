import type {Metadata} from 'next';
import Providers from '@/components/Providers';
import Shell from '@/components/Shell';
import './globals.css';
import 'katex/dist/katex.min.css';
export const metadata: Metadata = {title: 'ThinkFirst — Ask, think, understand', description: 'Get AI help, try your own ideas, and keep your thinking together.'};
export default function RootLayout({children}: {children: React.ReactNode}) {return <html lang="en"><body><Providers><Shell>{children}</Shell></Providers></body></html>;}
