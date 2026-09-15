import SessionFlow from '@/components/SessionFlow';
export default async function Page({params}:{params:Promise<{id:string}>}){const {id}=await params;return <SessionFlow key={id} id={id}/>;}
