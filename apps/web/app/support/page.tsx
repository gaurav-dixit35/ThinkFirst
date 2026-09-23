import ProblemReport from '@/components/ProblemReport';
import SupportContact from '@/components/SupportContact';
export const metadata={title:'Report a problem — ThinkFirst',robots:{index:false,follow:false}};
export default function Page(){return <section className="learning-page"><header><h1>Help us fix what gets in your way.</h1><p>Prepare a short report, then check its status here. No AI requests are used.</p></header><ProblemReport/><SupportContact/></section>;}
