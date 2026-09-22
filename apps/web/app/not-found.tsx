import Link from 'next/link';
export default function NotFound() {
  return <section className="connection-state"><h1>That page isn’t here.</h1><p>The link may be incomplete or out of date.</p><Link className="primary" href="/">Back to ThinkFirst</Link></section>;
}
