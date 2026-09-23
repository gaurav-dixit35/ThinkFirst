export type SavedSummary = {saved:number; retried:number; attempts:number};
export type SavedItem = {answer_id:string; session_id:string; question:string; saved_at:string; deletion_pending:boolean; attempt_count:number};
export type SavedList = {items:SavedItem[]; total:number; has_more:boolean; summary:SavedSummary};
export type SavedDetail = Omit<SavedItem,'attempt_count'> & {answer:string; attempts:{id:string;text:string;created_at:string}[]};
