let leave: (() => Promise<void>) | null = null;
export function setLeaveHandler(handler: (() => Promise<void>) | null) {leave = handler;}
export async function beforeNavigation() {if(leave) await leave();}
