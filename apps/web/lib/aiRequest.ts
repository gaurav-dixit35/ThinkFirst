import {api, ApiError, LogEvent, ProviderName} from './api';

export type HintRequest = {event_id:string; session_id:string; tier:number; provider?:ProviderName; followup_text?:string; answer_style?:'concise'|'detailed'};
export const requestKey = (id:string) => `thinkfirst.ai-request.${id}`;

// Keep the same id across transport retries. The server alone chooses providers.
export async function completeHint(request:HintRequest, resume=false):Promise<LogEvent> {
  localStorage.setItem(requestKey(request.session_id), JSON.stringify(request));
  const started = Date.now();
  let submissions = 0;
  let submit = !resume;
  let conflict:ApiError|null = null;
  function done(result:LogEvent) {localStorage.removeItem(requestKey(request.session_id));return result;}
  try {
    while (Date.now()-started < 120000) {
      try {
        if (submit) {
          submissions++;
          submit = false;
          return done(await api<LogEvent>('/ai/hint', request));
        }
        const state = await api<{status:string; result:LogEvent|null}>(`/ai/requests/${request.event_id}`);
        if (state.status==='delivered' && state.result) return done(state.result);
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
      localStorage.removeItem(requestKey(request.session_id));
    }
    throw error;
  }
}
