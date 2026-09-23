import type {Metadata} from 'next';
import AuthPage from '@/components/AuthPage';
export const metadata: Metadata = {title: 'Sign in | ThinkFirst', robots: {index: false, follow: false}};
export default function Page() {return <AuthPage mode="login"/>;}
