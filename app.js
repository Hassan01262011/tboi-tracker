
const STORAGE_KEY="tboiTracker.full.v1";
let progress={format:"",achievements:[],collectedItems:[],completedChallenges:[],completionMarks:{}};

function load(){
  try{const x=JSON.parse(localStorage.getItem(STORAGE_KEY)); if(x) progress=x}catch(e){}
  renderAll();
}
function save(){localStorage.setItem(STORAGE_KEY,JSON.stringify(progress))}
const setOf=a=>new Set((a||[]).map(Number));
function isHard(v){return Number(v)>=2} // current export can report 3 for completed marks
function diff(v){v=Number(v)||0; return isHard(v)?"Hard":v===1?"Normal":"None"}

function renderSummary(){
  const a=setOf(progress.achievements), i=setOf(progress.collectedItems), c=setOf(progress.completedChallenges);
  achievementCount.textContent=`${a.size} / 638`;
  itemCount.textContent=`${i.size} / 732`;
  challengeCount.textContent=`${c.size} / 45`;
  let hard=0,total=0;
  Object.values(progress.completionMarks||{}).forEach(m=>Object.keys(MARK_LABELS).forEach(k=>{
    if(k==="UltraGreedier")return; total++; if(isHard(m[k]))hard++;
  }));
  markCount.textContent=progress.format?`${hard} / ${total}`:"0";
  dashboardCards.innerHTML=`
    <div class="card"><h3>Achievements</h3><div class="big">${a.size}</div><div class="muted">${638-a.size} remaining</div></div>
    <div class="card"><h3>Collection</h3><div class="big">${i.size}</div><div class="muted">${732-i.size} vanilla collectible IDs not marked collected</div></div>
    <div class="card"><h3>Challenges</h3><div class="big">${c.size}</div><div class="muted">${45-c.size} remaining</div></div>
    <div class="card"><h3>Hard Marks</h3><div class="big">${hard}</div><div class="muted">Across exported PlayerTypes</div></div>`;
}
function renderItems(q=""){
  const done=setOf(progress.collectedItems); q=q.toLowerCase().trim(); let h="";
  for(let id=1;id<=732;id++){let name=KNOWN_ITEMS[id]||`Collectible #${id}`; if(q&&!(`${id} ${name}`.toLowerCase().includes(q)))continue;
    h+=`<div class="entry ${done.has(id)?"done":""}"><div class="id">ITEM ${id}</div><div class="name">${name}</div><div class="state">${done.has(id)?"COLLECTED":"NOT COLLECTED"}</div></div>`}
  itemGrid.innerHTML=h;
}
function renderAchievements(q=""){
  const done=setOf(progress.achievements); q=q.toLowerCase().trim(); let h="";
  for(let id=1;id<=638;id++){let name=KNOWN_ACHIEVEMENTS[id]||`Achievement / Secret #${id}`; if(q&&!(`${id} ${name}`.toLowerCase().includes(q)))continue;
    h+=`<div class="entry ${done.has(id)?"done":""}"><div class="id">ACHIEVEMENT ${id}</div><div class="name">${name}</div><div class="state">${done.has(id)?"UNLOCKED":"LOCKED"}</div></div>`}
  achievementGrid.innerHTML=h;
}
function renderChallenges(q=""){
  const done=setOf(progress.completedChallenges); q=q.toLowerCase().trim(); let h="";
  for(let id=1;id<=45;id++){let name=CHALLENGE_NAMES[id]||`Challenge #${id}`; if(q&&!(`${id} ${name}`.toLowerCase().includes(q)))continue;
    h+=`<div class="entry ${done.has(id)?"done":""}"><div class="id">CHALLENGE ${id}</div><div class="name">${name}</div><div class="state">${done.has(id)?"COMPLETED":"NOT COMPLETED"}</div></div>`}
  challengeGrid.innerHTML=h;
}
function renderCharacters(q=""){
  q=q.toLowerCase().trim(); let h="";
  const marks=progress.completionMarks||{};
  Object.keys(marks).sort((a,b)=>+a-+b).forEach(id=>{
    let name=CHARACTER_NAMES[id]||`PlayerType ${id}`; if(q&&!(`${id} ${name}`.toLowerCase().includes(q)))return;
    const m=marks[id]||{}; let mh="";
    Object.entries(MARK_LABELS).forEach(([k,label])=>{
      let v=m[k]||0; mh+=`<div class="mark ${isHard(v)?"hard":v===1?"normal":""}"><b>${label}</b><span>${diff(v)} · raw ${v}</span></div>`;
    });
    h+=`<div class="character"><h3>${name} <span class="muted">· PlayerType ${id}</span></h3><div class="marks">${mh}</div></div>`;
  });
  characterList.innerHTML=h||`<div class="card">Import a REPENTOGON exporter save to display character marks.</div>`;
}
function renderAll(){renderSummary();renderItems(itemSearch?.value||"");renderAchievements(achievementSearch?.value||"");renderChallenges(challengeSearch?.value||"");renderCharacters(characterSearch?.value||"")}

saveInput.addEventListener("change",async e=>{
  const f=e.target.files[0]; if(!f)return;
  try{
    const x=JSON.parse(await f.text());
    if(x.format!=="tboi-progress-export-v2" || !Array.isArray(x.achievements) || !x.completionMarks) throw Error("Not a v2 exporter file");
    progress=x; save(); renderAll();
    status.innerHTML=`Loaded <b>${f.name}</b>: ${x.achievements.length} achievements, ${x.collectedItems.length} collected items, ${x.completedChallenges.length} challenges.`;
  }catch(err){status.textContent="Import failed: "+err.message}
  e.target.value="";
});
document.querySelectorAll("nav button").forEach(b=>b.onclick=()=>{
  document.querySelectorAll("nav button,.tab").forEach(x=>x.classList.remove("active"));
  b.classList.add("active"); document.getElementById(b.dataset.tab).classList.add("active");
});
itemSearch.oninput=()=>renderItems(itemSearch.value);
achievementSearch.oninput=()=>renderAchievements(achievementSearch.value);
challengeSearch.oninput=()=>renderChallenges(challengeSearch.value);
characterSearch.oninput=()=>renderCharacters(characterSearch.value);
if("serviceWorker" in navigator) navigator.serviceWorker.register("service-worker.js");
load();
