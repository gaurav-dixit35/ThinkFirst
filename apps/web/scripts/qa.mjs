// Separate synthetic browser QA from the user's real Clerk-enabled website.
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const command=process.argv[2];
if(!['build','start'].includes(command))throw new Error('Use qa.mjs build or start.');
if(process.env.NETLIFY==='true'||process.env.THINKFIRST_HOSTED==='1')throw new Error('QA must run locally, never as a hosted deployment.');
const root=fileURLToPath(new URL('../',import.meta.url));
const next=fileURLToPath(new URL('../node_modules/next/dist/bin/next',import.meta.url));
const env={...process.env,THINKFIRST_QA:'1',NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:'',CLERK_SECRET_KEY:'',NEXT_PUBLIC_API_URL:'http://localhost:8000',NEXT_TELEMETRY_DISABLED:'1'};
const child=spawn(process.execPath,[next,command,...(command==='start'?['--hostname','localhost','--port','3100']:[])],{cwd:root,env,stdio:'inherit'});
child.on('error',error=>{console.error(error.message);process.exitCode=1;});
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal));
child.on('exit',code=>{process.exitCode=code??1;});
