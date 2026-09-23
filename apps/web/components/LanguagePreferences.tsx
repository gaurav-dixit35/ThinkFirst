'use client';
import {useEffect,useState} from 'react';
import {api} from '@/lib/api';
import {useIdentity} from './Providers';
type Language='auto'|'english'|'hindi'|'hinglish';
export default function LanguagePreferences(){
 const [language,setLanguage]=useState<Language|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const blocked=useIdentity()?.privacy?.deletion_request?.status==='pending';
 async function load(){try{setLanguage((await api<{answer_language:Language}>('/preferences/language')).answer_language);setError('');}catch(e){setError((e as Error).message);}}
 useEffect(()=>{void load();},[]);
 return <div><h3>AI answer language</h3><p>Choose a default for new answers, hints and reviews. Existing answers, cached reviews and the app menus stay as they are. You can ask for another language in a message.</p><label htmlFor="answer-language">Preferred language</label><select id="answer-language" disabled={busy||language===null||blocked} value={language||'auto'} onChange={async e=>{const previous=language;const next=e.target.value as Language;setLanguage(next);setBusy(true);setError('');setNotice('');try{await api('/preferences/language',{answer_language:next});setNotice('Language saved. It applies to your next new AI request.');}catch(e){setLanguage(previous);setError((e as Error).message);}finally{setBusy(false);}}}><option value="auto">Match my question</option><option value="english">English</option><option value="hindi">हिन्दी · Hindi</option><option value="hinglish">Hinglish · Hindi in Latin script</option></select>{notice&&<p role="status">{notice}</p>}{error&&<p role="alert">{error}{language===null&&<button className="text-button" onClick={()=>void load()}>Retry language preference</button>}</p>}</div>;
}
