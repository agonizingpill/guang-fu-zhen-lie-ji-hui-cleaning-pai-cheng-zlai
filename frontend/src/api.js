export const identity=()=>JSON.parse(localStorage.getItem('solar-identity')||'null');
export async function request(path,method='GET',body){const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json',...(identity()?{Authorization:'Bearer '+identity().token}:{})},body:body?JSON.stringify(body):undefined});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));return data;}
export const saveIdentity=data=>localStorage.setItem('solar-identity',JSON.stringify(data));
