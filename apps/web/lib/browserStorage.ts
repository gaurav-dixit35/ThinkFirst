// Account scoping prevents one signed-in workspace from reopening another's drafts.
// Browser storage is not encrypted: use a private browser profile on shared devices.
let owner: string | null = null;
let development = false;
export const storageOwner = () => owner;

export function setStorageOwner(id: string | null, local = false, erasedAt?: string | null, erasedSessions:string[] = []) {
  owner = id;
  development = local;
  if(id&&erasedSessions.length){
    const erased=new Set(erasedSessions);
    for(const key of Object.keys(localStorage)){
      if(['draft','ai-request','ai-review','practice'].some(kind=>key.startsWith(`thinkfirst.${kind}.${id}.`))&&erasedSessions.some(sid=>key.endsWith(`.${sid}`)))localStorage.removeItem(key);
      else if(key.startsWith(`thinkfirst.event.${id}.`)){
        try{if(erased.has(JSON.parse(localStorage.getItem(key)!).event?.session_id))localStorage.removeItem(key);}catch{/* Existing queue validation reports corrupt entries. */}
      }
      if(local&&/^thinkfirst\.(draft|ai-request|ai-review)\./.test(key)&&erasedSessions.some(sid=>key===`thinkfirst.draft.${sid}`||key===`thinkfirst.draft.message.${sid}`||key===`thinkfirst.ai-request.${sid}`||key===`thinkfirst.ai-review.${sid}`))localStorage.removeItem(key);
    }
    const pending=`thinkfirst.pending.${id}`;
    try{const items=JSON.parse(localStorage.getItem(pending)||'[]');if(Array.isArray(items))localStorage.setItem(pending,JSON.stringify(items.filter(e=>!erased.has(e.session_id))));}catch{/* Preserve corrupt entries for recovery. */}
  }
  if (!id || !erasedAt) return;
  const marker = `thinkfirst.erased.${id}`;
  if (localStorage.getItem(marker) === erasedAt) return;
  const prefixes = ['draft', 'ai-request', 'ai-review', 'event', 'practice', 'report'].map(kind => `thinkfirst.${kind}.${id}.`);
  const legacy = /^thinkfirst\.(draft|ai-request|ai-review)\.(message\.)?[0-9a-f-]{36}$/i;
  for (const key of Object.keys(localStorage)) {
    if (prefixes.some(prefix => key.startsWith(prefix)) || key === `thinkfirst.pending.${id}` || (local && legacy.test(key))) localStorage.removeItem(key);
  }
  localStorage.setItem(marker, erasedAt);
}

export function scopedKey(kind: string, id: string) {
  if (!owner) throw new Error('Sign in before accessing your saved drafts.');
  const key = `thinkfirst.${kind}.${owner}.${id}`;
  // Only the original shared development account may adopt old unscoped drafts.
  if (development && typeof window !== 'undefined') {
    const legacy = `thinkfirst.${kind}.${id}`;
    const old = localStorage.getItem(legacy);
    if (old !== null) {
      if (localStorage.getItem(key) === null) localStorage.setItem(key, old);
      localStorage.removeItem(legacy);
    }
  }
  return key;
}
