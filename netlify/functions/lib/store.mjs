// Tiny storage layer. In production it is Netlify Blobs; for local testing
// (AKSHARA_LOCAL_DIR=...) it is plain files. Both support conditional writes,
// which is what keeps counters and table orders safe when several phones
// save at the same moment.
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync, readdirSync, rmSync, existsSync } from 'node:fs';
import path from 'node:path';

function blobsDb(store) {
  return {
    async get(key) {
      const r = await store.getWithMetadata(key, { type: 'json' });
      return r ? { v: r.data, etag: r.etag } : null;
    },
    // cond: { match: etag } | { isNew: true } | undefined (overwrite)
    async put(key, v, cond) {
      const opt = cond && cond.match ? { onlyIfMatch: cond.match } : cond && cond.isNew ? { onlyIfNew: true } : {};
      const r = await store.setJSON(key, v, opt);
      return r.modified !== false;
    },
    async list(prefix) {
      const r = await store.list({ prefix });
      return r.blobs.map(b => b.key);
    },
    async del(key) { await store.delete(key); },
  };
}

function fileDb(dir) {
  mkdirSync(dir, { recursive: true });
  const file = k => path.join(dir, encodeURIComponent(k) + '.json');
  const etagOf = s => createHash('sha1').update(s).digest('hex');
  return {
    async get(key) {
      if (!existsSync(file(key))) return null;
      const s = readFileSync(file(key), 'utf8');
      return { v: JSON.parse(s), etag: etagOf(s) };
    },
    async put(key, v, cond) {
      const cur = existsSync(file(key)) ? etagOf(readFileSync(file(key), 'utf8')) : null;
      if (cond && cond.isNew && cur) return false;
      if (cond && cond.match && cur !== cond.match) return false;
      writeFileSync(file(key), JSON.stringify(v));
      return true;
    },
    async list(prefix) {
      return readdirSync(dir).map(f => decodeURIComponent(f.replace(/\.json$/, ''))).filter(k => k.startsWith(prefix));
    },
    async del(key) { if (existsSync(file(key))) rmSync(file(key)); },
  };
}

let cached;
export async function openDb() {
  if (cached) return cached;
  if (process.env.AKSHARA_LOCAL_DIR) return (cached = fileDb(process.env.AKSHARA_LOCAL_DIR));
  const { getStore } = await import('@netlify/blobs');
  return (cached = blobsDb(getStore({ name: 'akshara', consistency: 'strong' })));
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// Read-modify-write with retry. `fn` mutates the value in place (or returns a new one).
export async function update(db, key, fn, init) {
  for (let i = 0; i < 8; i++) {
    const cur = await db.get(key);
    const base = cur ? structuredClone(cur.v) : await init();
    const out = await fn(base);
    const nv = out === undefined ? base : out;
    if (await db.put(key, nv, cur ? { match: cur.etag } : { isNew: true })) return nv;
    await sleep(25 + Math.random() * 60 * (i + 1));
  }
  throw new Error('Server busy, please try again');
}
