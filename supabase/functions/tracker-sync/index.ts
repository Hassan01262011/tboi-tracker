// Custom capability authentication: only the random pairing secret grants access.
// Database credentials remain exclusively in the Supabase runtime environment.
const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type', 'Access-Control-Allow-Methods': 'POST, OPTIONS', 'Content-Type': 'application/json', 'Cache-Control': 'no-store' };
const reply = (data, status = 200) => new Response(JSON.stringify(data), { status, headers: cors });
const b64 = bytes => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
const hash = async s => b64(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))));
const token = n => b64(crypto.getRandomValues(new Uint8Array(n)));
function valid(p) {
  return p && typeof p === 'object' && !Array.isArray(p) &&
    ['achievements', 'collectedItems', 'completedChallenges'].every(k => Array.isArray(p[k]) && p[k].length <= 10000 && p[k].every(v => Number.isInteger(v) && v > 0 && v < 1000000)) &&
    p.completionMarks && typeof p.completionMarks === 'object' && !Array.isArray(p.completionMarks);
}
async function db(params, method = 'GET', body = undefined) {
  const key = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  const r = await fetch(Deno.env.get('SUPABASE_URL') + '/rest/v1/tracker_sync?' + new URLSearchParams(params), {
    method, headers: { apikey: key, Authorization: 'Bearer ' + key, 'Content-Type': 'application/json', Prefer: 'return=representation' },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  if (!r.ok) throw Error('Database request failed');
  return await r.json();
}
export async function handler(req) {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
  if (req.method !== 'POST') return reply({ error: 'POST only' }, 405);
  try {
    const text = await req.text();
    if (text.length > 500000) return reply({ error: 'Payload too large' }, 413);
    let body; try { body = JSON.parse(text); } catch { return reply({ error: 'Invalid JSON' }, 400); }
    if (!body || !['create', 'pull', 'push'].includes(body.action)) return reply({ error: 'Unknown action' }, 400);
    if (body.action === 'create') {
      if (!valid(body.progress)) return reply({ error: 'Invalid progress' }, 400);
      const sync_id = token(9).toUpperCase(), secret = token(24), now = Date.now();
      const updated_at = new Date(now).toISOString();
      await db({}, 'POST', { sync_id, sync_secret_hash: await hash(secret), progress: { ...body.progress, _trackerUpdated: now }, updated_at });
      return reply({ sync_id, secret, updated_at, tracker_updated: now });
    }
    const sync_id = String(body.sync_id || '').trim().toUpperCase(), secret = String(body.secret || '');
    if (!/^[A-Z0-9_-]{12}$/.test(sync_id) || !secret || secret.length > 256) return reply({ error: 'Invalid sync code' }, 403);
    const [row] = await db({ sync_id: 'eq.' + sync_id, select: 'sync_secret_hash,progress,updated_at' });
    if (!row || row.sync_secret_hash !== await hash(secret)) return reply({ error: 'Invalid sync code' }, 403);
    if (body.action === 'pull') return reply({ progress: row.progress, updated_at: row.updated_at });
    if (!valid(body.progress)) return reply({ error: 'Invalid progress' }, 400);
    if (body.base_updated_at !== undefined && Date.parse(body.base_updated_at) !== Date.parse(row.updated_at)) return reply({ error: 'Cloud changed; download it before uploading' }, 409);
    const now = Math.max(Date.now(), Date.parse(row.updated_at) + 1), updated_at = new Date(now).toISOString();
    const params = { sync_id: 'eq.' + sync_id, updated_at: 'eq.' + row.updated_at };
    const rows = await db(params, 'PATCH', { progress: { ...body.progress, _trackerUpdated: now }, updated_at });
    if (!rows.length) return reply({ error: 'Cloud changed; retry with latest copy' }, 409);
    return reply({ ok: true, updated_at, tracker_updated: now });
  } catch { return reply({ error: 'Sync temporarily unavailable; please retry' }, 500); }
}
Deno.serve(handler);
