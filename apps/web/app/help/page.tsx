import Link from 'next/link';
import SupportContact from '@/components/SupportContact';
export const metadata = {title: 'Help — ThinkFirst'};
export default function HelpPage() {
  return <article className="settings-page prose"><span className="eyebrow">HELP</span><h1>A little help getting started.</h1>
    <h2>Ask, or try an idea first</h2><p>Ask AI gives you a direct answer. Try myself lets you save your own attempt, request a small hint, or see an explanation. You can change modes during a conversation.</p>
    <h2>Find your saved work</h2><p>History keeps your conversations. Reopen one to continue. Progress shows your saved activity; it is not a grade or a measure of intelligence.</p>
    <h2>Save and revisit a question</h2><p>Choose Save for later below a chat answer. In <Link href="/saved">Saved</Link>, search your bookmarks and retry a question with the earlier answer hidden. Save your attempt, then compare. Reading and retrying saved work do not use AI requests. Removing a bookmark keeps your conversation and retries; deleting the conversation removes both.</p>
    <h2>If an answer stops</h2><p>Keep your browser profile, reconnect, and reopen the conversation. ThinkFirst checks the saved request before starting another generation. Settings also has a Sync saved work button.</p>
    <h2>Limits and reliability</h2><p>AI requests have daily and shared limits. If you reach a limit, you can keep writing your own thoughts. AI can make mistakes; check important answers against reliable sources. Automatic fallback helps when a service fails, but cannot guarantee an answer during an outage.</p>
    <p><Link href="/support">Report a problem and check its status</Link>. Settings also lets you choose an AI answer language. Progress includes an optional weekly practice goal.</p><SupportContact/><p><Link href="/privacy">Privacy and your data</Link> · <Link href="/">Back to ThinkFirst</Link></p>
  </article>;
}
