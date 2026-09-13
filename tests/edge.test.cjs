const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
test('edge creates, authenticates, updates with server timestamps and rejects stale writes',async()=>{
  let rows=[];
  const ctx=vm.createContext({Response,TextEncoder,URLSearchParams,crypto:require('node:crypto').webcrypto,btoa,
    Deno:{env:{get:k=>k==='SUPABASE_URL'?'https://example.test':'server-only'},serve(){}},
    fetch:async(url,opts)=>{
      if(opts.method==='POST'){rows.push(JSON.parse(opts.body));return Response.json(rows);}
      if(opts.method==='PATCH'){const filter=new URL(url).searchParams.get('updated_at').slice(3);if(filter!==rows[0].updated_at)return Response.json([]);Object.assign(rows[0],JSON.parse(opts.body));return Response.json(rows);}
      return Response.json(rows);
    }
  });
  vm.runInContext(fs.readFileSync('supabase/functions/tracker-sync/index.ts','utf8').replace('export async function','async function'),ctx);
  const call=body=>ctx.handler(new Request('https://test/',{method:'POST',body:JSON.stringify(body)}));
  const progress={achievements:[1],collectedItems:[],completedChallenges:[],completionMarks:{}};
  const c=await (await call({action:'create',progress})).json();
  const pair={sync_id:c.sync_id,secret:c.secret};
  assert.equal((await call({action:'pull',...pair,secret:'wrong'})).status,403);
  const p=await (await call({action:'pull',...pair})).json();
  const u=await call({action:'push',...pair,base_updated_at:p.updated_at,progress:{...progress,achievements:[1,2],_trackerUpdated:99999999999999}});
  assert.equal(u.status,200);
  assert.ok(rows[0].progress._trackerUpdated<99999999999999);
  assert.equal((await call({action:'push',...pair,base_updated_at:p.updated_at,progress})).status,409);
  assert.equal((await call({action:'push',...pair,progress:[]})).status,400);
  assert.deepEqual(rows[0].progress.achievements,[1,2]);
});
