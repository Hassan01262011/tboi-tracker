
const KEY="tboiTracker.interactive.v2";
const SYNC_KEY="tboiTracker.cloudSync.v1";
const SYNC_ENDPOINT="https://rqkatvagyyumlzatiqmp.supabase.co/functions/v1/tracker-sync";
let syncTimer=null,syncBusy=false,suppressSync=false;
function getSync(){try{return JSON.parse(localStorage.getItem(SYNC_KEY))||null}catch(_){return null}}
function setSync(v){v?localStorage.setItem(SYNC_KEY,JSON.stringify(v)):localStorage.removeItem(SYNC_KEY);renderSync()}
async function syncApi(body){let r=await fetch(SYNC_ENDPOINT,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}),x=await r.json().catch(()=>({}));if(!r.ok)throw Error(x.error||`Sync failed (${r.status})`);return x}
function syncStamp(){return Number(localStorage.getItem(KEY+".updated"))||0}
function markUpdated(){localStorage.setItem(KEY+".updated",String(Date.now()))}
function renderSync(){let s=getSync(),id=$("syncId"),sec=$("syncSecret");if(!id)return;if(s){id.value=s.sync_id;sec.value=s.secret;$("syncStatus").textContent="Connected. Changes can sync between this device and your other devices.";$("syncCreateArea").hidden=true}else{$("syncStatus").textContent="Create a private sync code on this PC, then enter the same code on your iPhone.";$("syncCreateArea").hidden=false}}
async function pushCloud(show=false){let s=getSync();if(!s||syncBusy||suppressSync)return;syncBusy=true;try{await syncApi({action:"push",...s,progress:{...progress,_trackerUpdated:syncStamp()}});if(show)toast("Uploaded to cloud")}catch(e){if(show)toast(e.message)}finally{syncBusy=false}}
async function pullCloud(show=false){let s=getSync();if(!s||syncBusy)return;syncBusy=true;try{let x=await syncApi({action:"pull",...s}),cloud=x.progress||{},ct=Number(cloud._trackerUpdated)||0;if(ct>syncStamp()){delete cloud._trackerUpdated;suppressSync=true;progress=cloud;localStorage.setItem(KEY,JSON.stringify(progress));localStorage.setItem(KEY+".updated",String(ct));renderAll();suppressSync=false;if(show)toast("Downloaded cloud copy")}else if(show)toast("Already up to date")}catch(e){if(show)toast(e.message)}finally{syncBusy=false}}
function queueSync(){clearTimeout(syncTimer);syncTimer=setTimeout(()=>pushCloud(false),700)}
let progress={format:"manual",achievements:[],collectedItems:[],completedChallenges:[],completionMarks:{}};
const $=id=>document.getElementById(id), setOf=a=>new Set((a||[]).map(Number));
const hard=v=>Number(v)>=2, level=v=>hard(v)?"Hard":Number(v)===1?"Normal":"None";
function uniq(a){return [...new Set(a.map(Number))].sort((x,y)=>x-y)}
function persist(){localStorage.setItem(KEY,JSON.stringify(progress));if(!suppressSync){markUpdated();queueSync()}}
function toast(s){$("toast").textContent=s;$("toast").classList.add("show");clearTimeout(toast.t);toast.t=setTimeout(()=>$("toast").classList.remove("show"),1200)}
function toggleArray(key,id){let s=setOf(progress[key]);s.has(id)?s.delete(id):s.add(id);progress[key]=[...s];persist();renderAll()}
function pct(a,b){return b?Math.round(a/b*100):0}
function renderSummary(){
 let a=setOf(progress.achievements),i=setOf(progress.collectedItems),c=setOf(progress.completedChallenges),hardN=0,total=0;
 Object.values(progress.completionMarks||{}).forEach(m=>Object.keys(MARK_LABELS).forEach(k=>{if(k==="UltraGreedier")return;total++;if(hard(m[k]))hardN++}));
 $("achievementCount").textContent=`${a.size} / 638`;$("itemCount").textContent=`${i.size} / 732`;$("challengeCount").textContent=`${c.size} / 45`;$("markCount").textContent=total?`${hardN} / ${total}`:"0";
 $("achievementBar").style.width=pct(a.size,638)+"%";$("itemBar").style.width=pct(i.size,732)+"%";$("challengeBar").style.width=pct(c.size,45)+"%";$("markBar").style.width=pct(hardN,total)+"%";
 let all=a.size+i.size+c.size+hardN, denom=638+732+45+total;$("overallPercent").textContent=`${pct(all,denom)}% tracked`;
 $("dashboardCards").innerHTML=`<div class=card><h3>Achievements remaining</h3><div class=big>${638-a.size}</div></div><div class=card><h3>Items remaining</h3><div class=big>${732-i.size}</div></div><div class=card><h3>Challenges remaining</h3><div class=big>${45-c.size}</div></div><div class=card><h3>Hard marks remaining</h3><div class=big>${Math.max(0,total-hardN)}</div></div>`;
}
function renderItems(q=""){let s=setOf(progress.collectedItems),h="",z=q.toLowerCase().trim();for(let id=1;id<=732;id++){let n=KNOWN_ITEMS[id]||`Collectible #${id}`;if(z&&!`${id} ${n}`.toLowerCase().includes(z))continue;h+=`<div class="entry ${s.has(id)?"done":""}" onclick="toggleArray('collectedItems',${id})"><div class=id>ITEM ${id}</div><div class=name>${n}</div><div class=state>${s.has(id)?"COLLECTED":"NOT COLLECTED"}</div></div>`}$("itemGrid").innerHTML=h}
function renderAchievements(q=""){let s=setOf(progress.achievements),h="",z=q.toLowerCase().trim();for(let id=1;id<=638;id++){let n=KNOWN_ACHIEVEMENTS[id]||`Achievement / Secret #${id}`;if(z&&!`${id} ${n}`.toLowerCase().includes(z))continue;h+=`<div class="entry ${s.has(id)?"done":""}" onclick="toggleArray('achievements',${id})"><div class=id>ACHIEVEMENT ${id}</div><div class=name>${n}</div><div class=state>${s.has(id)?"UNLOCKED":"LOCKED"}</div></div>`}$("achievementGrid").innerHTML=h}
function renderChallenges(q=""){let s=setOf(progress.completedChallenges),h="",z=q.toLowerCase().trim();for(let id=1;id<=45;id++){let n=CHALLENGE_NAMES[id]||`Challenge #${id}`;if(z&&!`${id} ${n}`.toLowerCase().includes(z))continue;h+=`<div class="entry ${s.has(id)?"done":""}" onclick="toggleArray('completedChallenges',${id})"><div class=id>CHALLENGE ${id}</div><div class=name>${n}</div><div class=state>${s.has(id)?"COMPLETED":"NOT COMPLETED"}</div></div>`}$("challengeGrid").innerHTML=h}
function cycleMark(id,k){progress.completionMarks[id]??={};let v=Number(progress.completionMarks[id][k])||0;progress.completionMarks[id][k]=v===0?1:(v===1?2:0);persist();renderAll()}
function renderCharacters(q=""){let z=q.toLowerCase().trim(),h="",marks=progress.completionMarks||{};let ids=Object.keys(CHARACTER_NAMES).map(Number).filter(id=>id<=40);ids.forEach(id=>{let n=CHARACTER_NAMES[id];if(z&&!`${id} ${n}`.toLowerCase().includes(z))return;let m=marks[id]||{},mh="";Object.entries(MARK_LABELS).forEach(([k,label])=>{let v=Number(m[k])||0;mh+=`<div class="mark ${hard(v)?"hard":v===1?"normal":""}" onclick="cycleMark(${id},'${k}')"><b>${label}</b><span>${level(v)}</span></div>`});h+=`<div class=character><h3>${n} <span class=muted>· PlayerType ${id}</span></h3><div class=marks>${mh}</div></div>`});$("characterList").innerHTML=h}
function renderAll(){renderSummary();renderItems($("itemSearch").value);renderAchievements($("achievementSearch").value);renderChallenges($("challengeSearch").value);renderCharacters($("characterSearch").value)}
$("saveInput").onchange=async e=>{let f=e.target.files[0];if(!f)return;try{let x=JSON.parse(await f.text());if(x.format==="tboi-progress-export-v2"){progress=x}else if(x.achievements&&x.collectedItems&&x.completedChallenges&&x.completionMarks){progress=x}else throw Error("Unsupported file");progress.achievements=uniq(progress.achievements||[]);progress.collectedItems=uniq(progress.collectedItems||[]);progress.completedChallenges=uniq(progress.completedChallenges||[]);persist();renderAll();$("status").textContent=`Loaded ${f.name} · ${progress.achievements.length} achievements · ${progress.collectedItems.length} items · ${progress.completedChallenges.length} challenges`;toast("Save imported")}catch(err){toast("Import failed");$("status").textContent=err.message}e.target.value=""};
$("exportBtn").onclick=()=>{let b=new Blob([JSON.stringify(progress,null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(b);a.download="tboi-tracker-backup.json";a.click();URL.revokeObjectURL(a.href)};
$("resetBtn").onclick=()=>{if(confirm("Reset all locally stored tracker progress?")){progress={format:"manual",achievements:[],collectedItems:[],completedChallenges:[],completionMarks:{}};persist();renderAll();toast("Progress reset")}};
document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>{document.querySelectorAll("nav button,.tab").forEach(x=>x.classList.remove("active"));b.classList.add("active");$(b.dataset.tab).classList.add("active")});
["item","achievement","challenge","character"].forEach(n=>$(n+"Search").oninput=renderAll);
try{let old=JSON.parse(localStorage.getItem(KEY));if(old)progress=old}catch(e){}
$("syncBtn").onclick=()=>{$("syncModal").hidden=false;renderSync()};
$("syncClose").onclick=()=>$("syncModal").hidden=true;
$("syncModal").onclick=e=>{if(e.target===$("syncModal"))$("syncModal").hidden=true};
$("syncCreate").onclick=async()=>{try{let x=await syncApi({action:"create",progress:{...progress,_trackerUpdated:syncStamp()||Date.now()}}),s={sync_id:x.sync_id,secret:x.secret};setSync(s);$("syncStatus").textContent="Sync created. Open this tracker on your iPhone and enter these same two values.";toast("Sync code created")}catch(e){toast(e.message)}};
$("syncConnect").onclick=async()=>{let s={sync_id:$("syncId").value.trim().toUpperCase(),secret:$("syncSecret").value.trim()};if(!s.sync_id||!s.secret)return toast("Enter Sync ID and Secret");setSync(s);try{let x=await syncApi({action:"pull",...s}),cloud=x.progress||{};delete cloud._trackerUpdated;suppressSync=true;progress=cloud;localStorage.setItem(KEY,JSON.stringify(progress));markUpdated();renderAll();suppressSync=false;toast("Connected and downloaded")}catch(e){setSync(null);toast(e.message)}};
$("syncPush").onclick=()=>pushCloud(true);$("syncPull").onclick=()=>pullCloud(true);$("syncDisconnect").onclick=()=>{setSync(null);toast("Cloud sync disconnected")};
window.addEventListener("focus",()=>pullCloud(false));
if("serviceWorker"in navigator)navigator.serviceWorker.register("service-worker.js");
renderAll();renderSync();setTimeout(()=>pullCloud(false),500);
