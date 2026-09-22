import Link from 'next/link';
import {DataNotice} from '@/components/DataControls';
import SupportContact from '@/components/SupportContact';
export const metadata = {title: 'Privacy — ThinkFirst'};
export default function PrivacyPage() {
  return <article className="settings-page prose"><span className="eyebrow">YOUR DATA</span><h1>Privacy at ThinkFirst</h1><DataNotice/>
    <h2>Your choices</h2><p>In Settings you can download your data, change optional research sharing, or request conversation deletion. Deletion pauses new saves until the operator processes your request. Signing out or deleting a Clerk login does not by itself delete your ThinkFirst conversations.</p>
    <h2>Services involved</h2><p>Clerk handles sign-in for hosted accounts. The website and API hosts process connection information. Depending on the operator’s configuration, AI requests may use Google Gemini, Groq, OpenRouter, Mistral AI, Cloudflare Workers AI, or Claude. Each service handles requests under its own terms; some routing services use additional model providers.</p>
    <h2>Retention and recovery</h2><p>Usage and account records are retained for allowance enforcement and operation after conversation deletion. Backups and previously exported research copies need separate handling by the operator. Contact support for the retention schedule and questions about copies of your data.</p>
    <SupportContact/><p><Link href="/settings#privacy">Manage my data</Link> · <Link href="/help">Help</Link></p>
  </article>;
}
