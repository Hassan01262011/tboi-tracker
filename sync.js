const KEY = "tboiTracker.interactive.v2";
const SYNC_KEY = "tboiTracker.cloudSync.v1";
const SYNC_ENDPOINT = "https://rqkatvagyyumlzatiqmp.supabase.co/functions/v1/tracker-sync";
const DEAD_GOD_LIMITS = { achievements: 638, collectedItems: 732, completedChallenges: 45, maxCharacter: 40 };
let syncTimer, syncBusy = false, suppressSync = false;
let revision = null, editVersion = 0;
let dirty = localStorage.getItem(KEY + '.dirty') === '1';
function boundedIds(values, max) {
  return [...new Set((Array.isArray(values) ? values : []).map(Number).filter(v => Number.isInteger(v) && v > 0 && v <= max))].sort((a,b) => a-b);
}
function normalizeProgress(value = {}) {
  const p = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const marks = {};
  if (p.completionMarks && typeof p.completionMarks === 'object' && !Array.isArray(p.completionMarks)) {
    for (const [id, mark] of Object.entries(p.completionMarks)) {
      const n = Number(id);
      if (Number.isInteger(n) && n >= 0 && n <= DEAD_GOD_LIMITS.maxCharacter && mark && typeof mark === 'object' && !Array.isArray(mark)) marks[n] = mark;
    }
  }
  return {
    ...p,
    format: p.format || 'manual',
    achievements: boundedIds(p.achievements, DEAD_GOD_LIMITS.achievements),
    collectedItems: boundedIds(p.collectedItems, DEAD_GOD_LIMITS.collectedItems),
    completedChallenges: boundedIds(p.completedChallenges, DEAD_GOD_LIMITS.completedChallenges),
    completionMarks: marks
  };
}
function getSync() { try { return JSON.parse(localStorage.getItem(SYNC_KEY)) || null; } catch { return null; } }
function setSync(s) {
  s ? localStorage.setItem(SYNC_KEY, JSON.stringify(s)) : localStorage.removeItem(SYNC_KEY);
  revision = null;
  renderSync();
}
function syncStamp() { return Number(localStorage.getItem(KEY + '.updated')) || 0; }
function markUpdated() {
  editVersion++;
  dirty = true;
  localStorage.setItem(KEY + '.dirty', '1');
  localStorage.setItem(KEY + '.updated', String(Date.now()));
}
function syncStatus(message) {
  document.getElementById('syncStatus').textContent = message;
  document.getElementById('status').textContent = message;
}
function renderSync() {
  const s = getSync();
  document.getElementById('syncId').value = s?.sync_id || '';
  document.getElementById('syncSecret').value = s?.secret || '';
  document.getElementById('syncCreateArea').hidden = !!s;
  syncStatus(s ? 'Paired. Checking cloud every 5 seconds while this page is visible.' : 'Not paired. Open Cloud sync and enter your existing Sync ID and Secret.');
}
async function syncApi(body) {
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const r = await fetch(SYNC_ENDPOINT, { method: 'POST', cache: 'no-store', signal: controller.signal,
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await r.json();
    if (!r.ok) { const error = new Error(data.error || `Sync failed (${r.status})`); error.status = r.status; throw error; }
    return data;
  } finally { clearTimeout(timeout); }
}
function applyCloud(x) {
  const cloud = normalizeProgress(x.progress || {});
  progress = cloud;
  delete progress._trackerUpdated;
  localStorage.setItem(KEY, JSON.stringify(progress));
  localStorage.setItem(KEY + '.updated', String(Number(x.progress?._trackerUpdated) || 0));
  localStorage.removeItem(KEY + '.dirty'); dirty = false;
  revision = x.updated_at;
  renderAll();
}
async function pullCloud(show = false) {
  const s = getSync();
  if (!s || syncBusy) return;
  if (dirty) return pushCloud(show);
  syncBusy = true;
  const version = editVersion;
  try {
    const x = await syncApi({ action: 'pull', ...s });
    if (JSON.stringify(s) !== JSON.stringify(getSync())) return;
    // Do not discard a local click made while the request was in flight.
    if (version === editVersion && x.updated_at !== revision) applyCloud(x);
    syncStatus(`Cloud checked ${new Date().toLocaleTimeString()} · ${progress.achievements.length} achievements · ${progress.source === 'game' ? 'Game export' : 'Tracker copy'}`);
    if (show) toast('Cloud checked');
  } catch (e) { syncStatus('Sync error: ' + e.message + '. Will retry automatically.'); }
  finally { syncBusy = false; if (dirty) queueSync(); }
}
async function pushCloud(show = false) {
  const s = getSync();
  if (!s || suppressSync) return;
  if (syncBusy) { queueSync(); return; }
  syncBusy = true;
  const version = editVersion;
  try {
    // A reloaded/offline client must not overwrite an unseen newer cloud copy.
    if (!revision) {
      const x = await syncApi({ action: 'pull', ...s });
      if (JSON.stringify(s) !== JSON.stringify(getSync())) return;
      if (dirty && Number(x.progress?._trackerUpdated) > syncStamp()) {
        localStorage.setItem(KEY + '.conflictBackup', JSON.stringify(progress));
        applyCloud(x); syncStatus('Newer cloud progress restored. Local edits kept in a conflict backup.'); return;
      }
      revision = x.updated_at;
    }
    progress = normalizeProgress(progress);
    const x = await syncApi({ action: 'push', ...s, base_updated_at: revision,
      progress: { ...progress, source: 'manual', _trackerUpdated: syncStamp() } });
    if (JSON.stringify(s) !== JSON.stringify(getSync())) return;
    revision = x.updated_at;
    if (version === editVersion) {
      dirty = false; localStorage.removeItem(KEY + '.dirty');
      localStorage.setItem(KEY + '.updated', String(x.tracker_updated));
    }
    syncStatus('Saved to cloud at ' + new Date().toLocaleTimeString());
    if (show) toast('Uploaded');
  } catch (e) {
    if (e.status === 409) {
      localStorage.setItem(KEY + '.conflictBackup', JSON.stringify(progress));
      dirty = false; localStorage.removeItem(KEY + '.dirty'); revision = null;
      syncStatus('Cloud changed first. Local copy backed up; downloading newest progress.');
      setTimeout(() => pullCloud(), 0);
    } else syncStatus('Sync error: ' + e.message + '. Will retry automatically.');
  } finally { syncBusy = false; }
}
function queueSync() { clearTimeout(syncTimer); syncTimer = setTimeout(() => pushCloud(), 700); }
async function connectSync() {
  if (syncBusy) return;
  const s = { sync_id: $('syncId').value.trim().toUpperCase(), secret: $('syncSecret').value.trim() };
  if (!s.sync_id || !s.secret) return toast('Enter Sync ID and Secret');
  syncBusy = true;
  try {
    const x = await syncApi({ action: 'pull', ...s });
    localStorage.setItem(KEY + '.pairBackup', JSON.stringify(progress));
    setSync(s); applyCloud(x); toast('Paired');
  } catch (e) { syncStatus(e.message); } finally { syncBusy = false; }
}
async function createSync() {
  if (syncBusy) return;
  syncBusy = true;
  try {
    progress = normalizeProgress(progress);
    const x = await syncApi({ action: 'create', progress });
    setSync({ sync_id: x.sync_id, secret: x.secret });
    applyCloud({ ...x, progress: { ...progress, _trackerUpdated: x.tracker_updated } });
    toast('Sync code created');
  } catch (e) { syncStatus(e.message); } finally { syncBusy = false; }
}
setInterval(() => { if (!document.hidden) pullCloud(); }, 5000);
window.addEventListener('online', () => pullCloud());
document.addEventListener('visibilitychange', () => { if (!document.hidden) pullCloud(); });
