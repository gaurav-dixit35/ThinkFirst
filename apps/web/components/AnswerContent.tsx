'use client';
import {useState, type ComponentPropsWithoutRef} from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

function CodeBlock({children,...props}:ComponentPropsWithoutRef<'pre'>) {
  const [notice,setNotice]=useState('');
  return <div className="answer-code"><button type="button" className="copy-answer" onClick={async event=>{
    const text=event.currentTarget.parentElement?.querySelector('pre')?.textContent || '';
    try {await navigator.clipboard.writeText(text);setNotice('Code copied');}
    catch {setNotice('Could not copy. Select the code to copy it.');}
  }}>Copy code</button><span role="status" className="copy-notice">{notice}</span><pre {...props}>{children}</pre></div>;
}

export default function AnswerContent({text}:{text:string}) {
  const [notice,setNotice]=useState('');
  return <div className="answer-content">
    <div className="answer-markdown"><Markdown remarkPlugins={[remarkGfm,remarkMath]}
      rehypePlugins={[[rehypeKatex,{trust:false,strict:'ignore',throwOnError:false,maxExpand:1000,maxSize:20}]]}
      skipHtml components={{
        // Remote model-supplied images must not initiate tracking requests.
        img:({alt})=><span>{alt ? `[Image: ${alt}]` : '[Image omitted]'}</span>,
        a:({href,children})=><a href={href} target="_blank" rel="noopener noreferrer nofollow">{children}</a>,
        pre:({node,...props})=><CodeBlock {...props}/>,
      }}>{text}</Markdown></div>
    <button className="copy-answer" type="button" onClick={async()=>{
      try {await navigator.clipboard.writeText(text);setNotice('Answer copied');}
      catch {setNotice('Could not copy. Select the answer to copy it.');}
    }}>Copy answer</button><span className="copy-notice" role="status">{notice}</span>
  </div>;
}
