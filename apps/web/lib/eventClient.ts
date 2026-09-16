import {api, ApiError} from './api';

type Payloads = {
  conversation_mode_changed: {mode: 'ask_ai' | 'try_myself'};
  attempt_submitted: {attempt_text: string; is_partial: boolean};
  attempt_skipped: {skip_reason: string | null};
  verification_submitted: {hint_event_id: string; matches_own_attempt: boolean | null; justification: string};
  verification_skipped: {hint_event_id: string};
  evaluation_submitted: {makes_sense: boolean; reasoning: string};
  evaluation_skipped: Record<string, never>;
  attempt_correctness_reported: {attempt_event_id: string; adequate: boolean};
};
type Pending = {event_id: string; session_id: string; event_type: keyof Payloads; payload: Payloads[keyof Payloads]};
let owner: string | null = null;
const running = new Map<string, Promise<void>>();
let lastError = '';
const legacyKey = (id:string) => `thinkfirst.pending.${id}`;
const prefix = (id:string) => `thinkfirst.event.${id}.`;
function read(id:string):Pending[] {
  const legacy:Pending[] = JSON.parse(localStorage.getItem(legacyKey(id)) || '[]');
  const entries:{event:Pending;queued_at:number}[] = [];
  for(let i=0;i<localStorage.length;i++) {
    const key=localStorage.key(i);
    if(key?.startsWith(prefix(id))) entries.push(JSON.parse(localStorage.getItem(key)!));
  }
  entries.sort((a,b)=>a.queued_at-b.queued_at || a.event.event_id.localeCompare(b.event.event_id));
  return [...new Map([...legacy,...entries.map(e=>e.event)].map(e=>[e.event_id,e])).values()];
}
function remove(id:string,eventId:string) {
  localStorage.removeItem(prefix(id)+eventId);
  const legacy=JSON.parse(localStorage.getItem(legacyKey(id)) || '[]') as Pending[];
  if(legacy.some(e=>e.event_id===eventId)) localStorage.setItem(legacyKey(id),JSON.stringify(legacy.filter(e=>e.event_id!==eventId)));
}
function notify() { window.dispatchEvent(new Event('thinkfirst:queue')); }
export function setQueueOwner(id: string | null) { owner = id; lastError = ''; }
export function queueStatus() {
  try { return {count: owner ? read(owner).length : 0, error: lastError}; }
  catch { return {count: 0, error: 'Local event storage is unavailable. Keep this page open and try again.'}; }
}
export async function flushQueue(sessionId?:string):Promise<void> {
  if (!owner) throw new Error('Sign in before saving your work.');
  const initialOwner = owner;
  const previous=running.get(initialOwner);
  if(previous) {
    try {await previous;} catch { /* A session-specific retry may still succeed. */ }
    if(owner!==initialOwner) throw new Error('The signed-in participant changed. Retry in your own account.');
  }
  const flush = async()=>{
    const blocked = new Set<string>();
    let firstError:unknown;
    try {
      while (owner === initialOwner) {
        const next = read(initialOwner).find(e=>(!sessionId || e.session_id===sessionId)&&!blocked.has(e.session_id));
        if (!next) break;
        try {
          for (let attempt = 0; attempt < 3; attempt++) {
            if(owner!==initialOwner) throw new Error('The signed-in participant changed.');
            try { await api('/events', next); break; }
            catch (error) {
              if (!(error instanceof ApiError) || (error.status !== 0 && error.status < 500) || attempt === 2) throw error;
              await new Promise(resolve => setTimeout(resolve, 600 * 2 ** attempt));
            }
          }
          remove(initialOwner,next.event_id);
        } catch(error) {
          // Preserve rejected events, but let unrelated sessions continue to sync.
          blocked.add(next.session_id);
          firstError ||= error;
        }
      }
      if(owner!==initialOwner) throw new Error('The signed-in participant changed. Retry in your own account.');
      if(firstError) throw firstError;
      lastError = '';
    } catch (error) {
      if(owner===initialOwner)lastError = error instanceof Error ? error.message : 'An event could not be saved.';
      throw error;
    } finally { notify(); }
  };
  // Serialize flushes across tabs. Individual storage keys prevent lost appends.
  const work=(async()=>{if(navigator.locks)await navigator.locks.request(`thinkfirst-sync-${initialOwner}`,flush);else await flush();})();
  running.set(initialOwner,work);
  try {await work;} finally {if(running.get(initialOwner)===work)running.delete(initialOwner);}
}
export async function emitEvent<K extends keyof Payloads>(session_id: string, event_type: K, payload: Payloads[K]) {
  if (!owner) throw new Error('Sign in before saving your work.');
  const event_id = crypto.randomUUID();
  try {
    const existing=read(owner).find(e=>e.session_id===session_id && e.event_type===event_type && JSON.stringify(e.payload)===JSON.stringify(payload));
    if(existing) {await flushQueue(session_id);return existing.event_id;}
    localStorage.setItem(prefix(owner)+event_id,JSON.stringify({event:{event_id,session_id,event_type,payload},queued_at:Date.now()}));
    notify();
  }
  catch { throw new Error('Your browser could not save or sync this event. Keep your text here and retry syncing.'); }
  try { await flushQueue(session_id); }
  catch { throw new Error('Your event is queued on this device. Retry syncing before continuing; you do not need to submit it again.'); }
  return event_id;
}
