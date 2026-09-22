// Account scoping prevents one signed-in workspace from reopening another's drafts.
// Browser storage is not encrypted: use a private browser profile on shared devices.
let owner: string | null = null;
let development = false;
export const storageOwner = () => owner;

export function setStorageOwner(id: string | null, local = false, erasedAt?: string | null) {
  owner = id;
  development = local;
  if (!id || !erasedAt) return;
  const marker = `thinkfirst.erased.${id}`;
  if (localStorage.getItem(marker) === erasedAt) return;
  const prefixes = ['draft', 'ai-request', 'ai-review', 'event', 'practice'].map(kind => `thinkfirst.${kind}.${id}.`);
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
