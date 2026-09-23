import {api, ApiError, LogEvent, ProviderName} from './api';
import {scopedKey, storageOwner} from './browserStorage';

export type HintRequest = {event_id:string; session_id:string; tier:number; provider?:ProviderName; followup_text?:string; answer_style?:'concise'|'detailed';help_action?:'hint'|'answer'|'exercise';stream?:boolean;regenerate_of?:string};
export const requestKey = (id:string) => scopedKey('ai-request', id);
export type ReviewRequest = {event_id:string;session_id:string};
export const reviewKey = (id:string) => scopedKey('ai-review', id);

// Keep the same id across transport retries. The server alone chooses providers.
export async function completeHint(request:HintRequest, resume=false, onProgress?:(text:string)=>void):Promise<LogEvent> {
  return completeRequest(request,resume,requestKey(request.session_id),'/ai/hint',`/ai/requests/${request.event_id}`,onProgress);
}
export async function completeReview(request:ReviewRequest,resume=false):Promise<LogEvent>{
  return completeRequest(request,resume,reviewKey(request.session_id),`/sessions/${request.session_id}/analysis`,`/ai/analyses/${request.event_id}`);
}
async function completeRequest(request:ReviewRequest,resume:boolean,key:string,submitPath:string,pollPath:string,onProgress?:(text:string)=>void):Promise<LogEvent>{
  const initialOwner = storageOwner();
  localStorage.setItem(key, JSON.stringify(request));
  const started = Date.now();
  let active=true, polling=false;
  const timer=onProgress ? setInterval(async()=>{
    if(!active || polling || storageOwner()!==initialOwner)return;
    polling=true;
    try {const state=await api<{preview?:string}>(pollPath);if(active&&storageOwner()===initialOwner)onProgress(state.preview||'');} catch { /* Submission/recovery owns errors. */ }
    finally {polling=false;}
  },700):null;
  let submissions = 0;
  let submit = !resume;
  let conflict:ApiError|null = null;
  function done(result:LogEvent) {localStorage.removeItem(key);return result;}
  try {
    while (Date.now()-started < 120000) {
      if (!initialOwner || storageOwner() !== initialOwner) throw new Error('The signed-in account changed. Reopen this conversation in its original account.');
      try {
        if (submit) {
          submissions++;
          submit = false;
          return done(await api<LogEvent>(submitPath, request));
        }
        const state = await api<{status:string; result:LogEvent|null}>(pollPath);
        if (state.status==='delivered' && state.result) return done(state.result);
        if (state.status==='cancelled') throw new ApiError('Generation stopped. Usage already incurred still counts.',499);
        if (state.status==='failed') throw new ApiError(state.result?.payload.reason || 'AI could not answer. Your work is saved; please retry.', 502);
      } catch (error) {
        if (!(error instanceof ApiError)) throw error;
        if (error.status===409) conflict=error;
        if (error.status===404 && conflict) throw conflict;
        if (error.status===404 && submissions<3) submit=true;
        else if (![0,409,500,503,504].includes(error.status)) throw error;
      }
      await new Promise(resolve=>setTimeout(resolve,1500));
    }
    throw new ApiError('Your request is saved. Reconnect and retry to check for its response.', 0);
  } catch (error) {
    if (error instanceof ApiError && ((error.status>0 && error.status<500) || error.status===502)) {
      localStorage.removeItem(key);
    }
    throw error;
  } finally {active=false;if(timer)clearInterval(timer);onProgress?.('');}
}
