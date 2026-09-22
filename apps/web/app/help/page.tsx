import Link from 'next/link';
import SupportContact from '@/components/SupportContact';
export const metadata = {title: 'Help — ThinkFirst'};
export default function HelpPage() {
  return <article className="settings-page prose"><span className="eyebrow">HELP</span><h1>A little help getting started.</h1>
    <h2>Ask, or try an idea first</h2><p>Ask AI gives you a direct answer. Try myself lets you save your own attempt, request a small hint, or see an explanation. You can change modes during a conversation.</p>
    <h2>Find your saved work</h2><p>History keeps your conversations. Reopen one to continue. Progress shows your saved activity; it is not a grade or a measure of intelligence.</p>
    <h2>If an answer stops</h2><p>Keep your browser profile, reconnect, and reopen the conversation. ThinkFirst checks the saved request before starting another generation. Settings also has a Sync saved work button.</p>
    <h2>Limits and reliability</h2><p>AI requests have daily and shared limits. If you reach a limit, you can keep writing your own thoughts. AI can make mistakes; check important answers against reliable sources. Automatic fallback helps when a service fails, but cannot guarantee an answer during an outage.</p>
    <SupportContact/><p><Link href="/privacy">Privacy and your data</Link> · <Link href="/">Back to ThinkFirst</Link></p>
  </article>;
}
