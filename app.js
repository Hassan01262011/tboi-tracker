
const KEY="deadGodTracker.v1";
const blank=()=>({version:1,completedItems:[],completedCharacters:[]});
let state=load();

function load(){try{return {...blank(),...JSON.parse(localStorage.getItem(KEY)||"{}")}}catch{return blank()}}
function save(){localStorage.setItem(KEY,JSON.stringify(state));render()}
function done(type,id){const k=type==="item"?"completedItems":"completedCharacters";return state[k].includes(id)}
function toggle(type,id){const k=type==="item"?"completedItems":"completedCharacters";state[k]=done(type,id)?state[k].filter(x=>x!==id):[...state[k],id];save()}

function card(x,type,rank){
 const el=document.createElement("div"); el.className="card"+(done(type,x.id)?" done":"");
 el.innerHTML=`<div class="check">${done(type,x.id)?"✓":""}</div><div><div class="badge">${type}</div><div class="name"></div><div class="how"></div></div>${rank?`<div class="rank">#${rank}</div>`:""}`;
 el.querySelector(".name").textContent=x.name; el.querySelector(".how").textContent=x.how;
 el.onclick=()=>toggle(type,x.id); return el;
}
function renderList(id,data,type){
 const box=document.getElementById(id); box.innerHTML="";
 data.filter(x=>!done(type,x.id)).sort((a,b)=>b.priority-a.priority).slice(0,10).forEach((x,i)=>box.appendChild(card(x,type,i+1)));
 if(!box.children.length) box.innerHTML='<div class="how">Everything in this queue is complete.</div>';
}
function render(){
 renderList("items",TRACKER_DATA.items,"item"); renderList("characters",TRACKER_DATA.characters,"character");
 const n=state.completedItems.length+state.completedCharacters.length;
 document.getElementById("progress").textContent=`${n} tracker goals completed`;
}
const search=document.getElementById("search");
search.addEventListener("input",()=>{
 const q=search.value.trim().toLowerCase(), sr=document.getElementById("searchResults"), main=document.getElementById("main"), out=document.getElementById("results");
 if(!q){sr.classList.add("hidden");main.classList.remove("hidden");return}
 main.classList.add("hidden");sr.classList.remove("hidden");out.innerHTML="";
 [...TRACKER_DATA.items.map(x=>[x,"item"]),...TRACKER_DATA.characters.map(x=>[x,"character"])]
 .filter(([x])=>(x.name+" "+x.how).toLowerCase().includes(q))
 .forEach(([x,t])=>out.appendChild(card(x,t)));
});
document.getElementById("closeSearch").onclick=()=>{search.value="";search.dispatchEvent(new Event("input"))}
document.getElementById("menuBtn").onclick=()=>document.getElementById("savePanel").classList.toggle("hidden");
document.getElementById("exportBtn").onclick=()=>{
 const blob=new Blob([JSON.stringify(state,null,2)],{type:"application/json"}),a=document.createElement("a");
 a.href=URL.createObjectURL(blob);a.download="dead-god-progress.json";a.click();URL.revokeObjectURL(a.href);
};
document.getElementById("importInput").onchange=async e=>{
 const f=e.target.files[0];if(!f)return;
 try{const v=JSON.parse(await f.text());state={...blank(),...v};save();alert("Progress imported.")}catch{alert("That save file could not be read.")}
 e.target.value="";
};
document.getElementById("resetBtn").onclick=()=>{if(confirm("Reset all tracker progress on this device?")){state=blank();save()}};
if("serviceWorker" in navigator) navigator.serviceWorker.register("./service-worker.js").catch(()=>{});
render();
