const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function setup() {
  const storage = new Map(), elements = new Map();
  const ctx = vm.createContext({console, JSON, Date, AbortController,
    setTimeout:()=>1, clearTimeout(){}, setInterval(){},
    window:{addEventListener(){}}, document:{hidden:false,addEventListener(){},getElementById(id){if(!elements.has(id))elements.set(id,{});return elements.get(id);}},
    localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,String(v)),removeItem:k=>storage.delete(k)},
    fetch:async()=>{throw Error('unmocked')}
  });
  vm.runInContext(fs.readFileSync('sync.js','utf8') + `\nlet progress={achievements:[],collectedItems:[],completedChallenges:[],completionMarks:{}};function renderAll(){};function toast(){};const $=id=>document.getElementById(id);setSync({sync_id:'TEST',secret:'SECRET'});`,ctx);
  return {ctx, storage, run:s=>vm.runInContext(s,ctx)};
}
test('cloud updates apply despite incorrect future local timestamp',async()=>{
  const {ctx,run}=setup();
  run(`localStorage.setItem(KEY+'.updated','9999999999999')`);
  ctx.fetch=async()=>({ok:true,json:async()=>({updated_at:'revision-2',progress:{achievements:[1,2],_trackerUpdated:100}})});
  await run('pullCloud()');assert.equal(run('progress.achievements.length'),2);
});
test('a local edit during pull is preserved',async()=>{
  const {ctx,run}=setup();let release;
  ctx.fetch=()=>new Promise(r=>release=r);
  const pull=run('pullCloud()');run('progress.achievements=[99];markUpdated()');
  release({ok:true,json:async()=>({updated_at:'2',progress:{achievements:[1]}})});
  await pull;assert.equal(run('progress.achievements[0]'),99);
});
test('stale push conflict preserves backup and schedules pull',async()=>{
  const {ctx,run,storage}=setup();run(`revision='old';progress.achievements=[99];markUpdated()`);
  ctx.fetch=async()=>({ok:false,status:409,json:async()=>({error:'conflict'})});
  await run('pushCloud()');assert.ok(storage.get('tboiTracker.interactive.v2.conflictBackup'));assert.equal(run('dirty'),false);
});
test('failed upload remains dirty for retries',async()=>{
  const {ctx,run}=setup();run(`revision='old';markUpdated()`);
  ctx.fetch=async()=>{throw Error('offline')};await run('pushCloud()');assert.equal(run('dirty'),true);
});
test('pairing uses server revision, never stamps local clock as newer',async()=>{
  const {ctx,run}=setup();run(`$('syncId').value='PAIR';$('syncSecret').value='SECRET'`);
  ctx.fetch=async()=>({ok:true,json:async()=>({updated_at:'server-revision',progress:{achievements:[7],_trackerUpdated:123}})});
  await run('connectSync()');assert.equal(run('syncStamp()'),123);assert.equal(run('dirty'),false);
});
