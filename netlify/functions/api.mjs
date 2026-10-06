// Hotel Akshara billing API (Netlify Function). Served at /api/*
import { randomBytes, scryptSync, timingSafeEqual, createHmac } from 'node:crypto';
import { openDb, update } from './lib/store.mjs';
import seed from './lib/seed.mjs';

const SECTIONS = ['hotel', 'bar'];
const TZ = process.env.APP_TIMEZONE || 'Asia/Kolkata';
const PUBLIC_KEYS = Object.keys(seed.defaults);
const TOKEN_DAYS = 30;

class ApiError extends Error {
  constructor(code, msg) { super(msg); this.code = code; this.msg = msg; }
}

/* ---------------- small helpers ---------------- */
const num = x => { x = Number(x) || 0; return Number.isInteger(x) ? x : Math.round(x * 100) / 100; };
const toFloat = (v, d = 0) => { const n = parseFloat(v); return Number.isFinite(n) ? n : d; };
const sec = x => (x === 'bar' ? 'bar' : 'hotel');
const nowStr = () => new Date().toLocaleString('sv-SE', { timeZone: TZ }); // YYYY-MM-DD HH:mm:ss
const sleep = ms => new Promise(r => setTimeout(r, ms));
const json = (data, code = 200) =>
  new Response(JSON.stringify(data), { status: code, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });

function hashPw(pw, salt = randomBytes(8).toString('hex')) {
  return salt + ':' + scryptSync(String(pw), salt, 32).toString('hex');
}
function checkPw(pw, h) {
  if (!h || typeof pw !== 'string' || !pw) return false;
  const [salt, hx] = h.split(':');
  const a = Buffer.from(scryptSync(pw, salt, 32).toString('hex'));
  const b = Buffer.from(hx);
  return a.length === b.length && timingSafeEqual(a, b);
}
function sign(settings, exp) {
  return exp + '.' + createHmac('sha256', settings.secret + settings.app_hash).update(String(exp)).digest('hex');
}
function validToken(settings, tok) {
  if (!tok) return false;
  const [exp, mac] = tok.split('.');
  if (!(Number(exp) > Date.now()) || !mac) return false;
  const good = sign(settings, exp).split('.')[1];
  return mac.length === good.length && timingSafeEqual(Buffer.from(mac), Buffer.from(good));
}
const newToken = settings => sign(settings, Date.now() + TOKEN_DAYS * 864e5);

/* ---------------- stored documents ---------------- */
async function getSettings(db) {
  let c = await db.get('settings');
  if (c) return c.v;
  const v = {
    ...seed.defaults,
    secret: randomBytes(24).toString('hex'),
    admin_hash: hashPw(process.env.ADMIN_PIN || '1234'),
    app_hash: process.env.APP_PASSWORD ? hashPw(process.env.APP_PASSWORD) : '',
  };
  if (await db.put('settings', v, { isNew: true })) return v;
  c = await db.get('settings');
  return c.v;
}

async function getMenu(db) {
  let c = await db.get('menu');
  if (c) return c.v;
  const v = {
    categories: seed.categories.map(x => ({ id: x.id, name_mr: x.name_mr, name_en: x.name_en, sort: x.sort, section: x.section })),
    items: seed.items.map(x => ({ id: x.id, category_id: x.category_id, name_mr: x.name_mr, name_en: x.name_en, type: x.type, variants: x.variants, active: 1, sort: x.sort })),
    seq: { cat: Math.max(0, ...seed.categories.map(x => x.id)), item: Math.max(0, ...seed.items.map(x => x.id)) },
  };
  if (await db.put('menu', v, { isNew: true })) return v;
  c = await db.get('menu');
  return c.v;
}

const bySortId = (a, b) => (a.sort - b.sort) || (a.id - b.id);
function menuView(m) {
  const secOf = Object.fromEntries(m.categories.map(c => [c.id, sec(c.section)]));
  return {
    categories: [...m.categories].sort(bySortId).map(c => ({ ...c, section: sec(c.section) })),
    items: [...m.items].sort(bySortId).map(i => ({ ...i, section: secOf[i.category_id] || 'hotel' })),
  };
}

function cleanVariants(raw) {
  const out = [];
  for (const v of raw || []) {
    if (!v || typeof v !== 'object') continue;
    const p = toFloat(v.p, -1);
    if (p < 0) continue;
    out.push({ mr: String(v.mr ?? '').trim(), en: String(v.en ?? '').trim(), p: num(p) });
  }
  if (!out.length) throw new ApiError(400, 'At least one price is required / किमान एक दर आवश्यक');
  return out;
}

function cleanLines(raw) {
  const lines = [];
  for (const it of raw || []) {
    if (!it || typeof it !== 'object') continue;
    const qty = Math.trunc(toFloat(it.qty, 0));
    const price = toFloat(it.price, -1);
    if (qty <= 0 || price < 0) continue;
    lines.push({
      item_id: it.item_id ?? null, section: sec(it.section),
      name_mr: String(it.name_mr ?? ''), name_en: String(it.name_en ?? ''),
      vmr: String(it.vmr ?? ''), ven: String(it.ven ?? ''), price: num(price), qty,
    });
  }
  return lines;
}

/* ---------------- orders (open tables) ---------------- */
function orderRow(o) {
  const tot = { hotel: 0, bar: 0 };
  for (const l of o.items) tot[sec(l.section)] += l.price * l.qty;
  return {
    table_no: o.table_no, customer: o.customer || '', items: o.items, created_at: o.created_at, updated_at: o.updated_at,
    hotel_total: num(tot.hotel), bar_total: num(tot.bar), total: num(tot.hotel + tot.bar),
    count: o.items.reduce((a, l) => a + l.qty, 0),
  };
}
const blankOrder = tno => {
  const now = nowStr();
  return { table_no: tno, customer: '', items: [], created_at: now, updated_at: now, hotel_total: 0, bar_total: 0, total: 0, count: 0 };
};

/* ---------------- bills (one blob per day) ---------------- */
function normTs(ts) {
  ts = String(ts || '').trim().slice(0, 16);
  if (!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/.test(ts) || isNaN(Date.parse(ts.replace(' ', 'T')))) ts = nowStr().slice(0, 16);
  return ts;
}

async function addBills(db, entries, ts, tableNo, customer) {
  const meta = await update(db, 'meta', m => { m.billSeq = (m.billSeq || 0) + entries.length; }, () => ({ billSeq: 0 }));
  const first = meta.billSeq - entries.length + 1;
  const bills = entries.map((e, i) => {
    const subtotal = e.lines.reduce((a, l) => a + l.price * l.qty, 0);
    const discount = Math.min(Math.max(toFloat(e.discount, 0), 0), subtotal);
    return {
      id: first + i, created_at: ts, table_no: String(tableNo || '').trim().slice(0, 20),
      customer: String(customer || '').trim().slice(0, 60), items: e.lines,
      subtotal: num(subtotal), discount: num(discount), total: num(subtotal - discount), section: e.section,
    };
  });
  await update(db, 'bills/' + ts.slice(0, 10), arr => { arr.push(...bills); }, () => []);
  return bills;
}

async function readAll(db, keys) {
  const out = [];
  for (let i = 0; i < keys.length; i += 25) {
    const part = await Promise.all(keys.slice(i, i + 25).map(k => db.get(k).then(c => (c ? c.v : []))));
    out.push(...part.flat());
  }
  return out;
}
const billsOfDay = async (db, d) => { const c = await db.get('bills/' + d); return c ? c.v : []; };
async function billsOfRange(db, from, to) {
  const keys = (await db.list('bills/')).filter(k => { const m = k.slice(6, 13); return m >= from && m <= to; });
  return readAll(db, keys);
}

function summarize(bills) {
  const s = { total: 0, count: bills.length, subtotal: 0, discount: 0, hotel: 0, bar: 0 };
  for (const b of bills) {
    s.total += b.total; s.subtotal += b.subtotal; s.discount += b.discount; s[sec(b.section)] += b.total;
  }
  for (const k of Object.keys(s)) s[k] = num(s[k]);
  return s;
}
function aggItems(bills) {
  const agg = new Map();
  for (const b of bills) {
    for (const l of b.items) {
      const key = JSON.stringify([l.name_mr, l.name_en, l.vmr, l.ven, l.price]);
      const a = agg.get(key) || { name_mr: l.name_mr, name_en: l.name_en, vmr: l.vmr, ven: l.ven, price: l.price, qty: 0 };
      a.qty += l.qty; agg.set(key, a);
    }
  }
  const out = [...agg.values()].sort((x, y) => y.qty * y.price - x.qty * x.price);
  for (const a of out) a.amount = num(a.qty * a.price);
  return out;
}
const csvCell = v => { v = String(v ?? ''); return /[",\r\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
const csvRow = a => a.map(csvCell).join(',') + '\r\n';

/* ---------------- router ---------------- */
async function route(db, method, parts, q, body, req) {
  const res = parts[0] || '';
  const settings = await getSettings(db);

  // ----- app login (staff password) -----
  if (res === 'auth') {
    const sub = parts[1] || '';
    if (method === 'GET' && sub === 'status') return { setup: !settings.app_hash };
    if (method === 'POST' && sub === 'setup') {
      if (settings.app_hash) throw new ApiError(403, 'Password already set');
      const pw = String(body.password || '');
      if (pw.length < 6) throw new ApiError(400, 'Password must be at least 6 characters / पासवर्ड किमान ६ अक्षरी हवा');
      const s2 = await update(db, 'settings', s => { if (s.app_hash) throw new ApiError(403, 'Password already set'); s.app_hash = hashPw(pw); });
      return { token: newToken(s2) };
    }
    if (method === 'POST' && !sub) {
      if (!checkPw(String(body.password || ''), settings.app_hash)) { await sleep(500); throw new ApiError(401, 'Wrong password / चुकीचा पासवर्ड'); }
      return { token: newToken(settings) };
    }
    throw new ApiError(404, 'Not found');
  }
  const bearer = (req.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
  if (!validToken(settings, bearer)) { const e = new ApiError(401, 'Please log in / कृपया लॉगिन करा'); e.auth = true; throw e; }

  const pinOk = checkPw(req.headers.get('x-admin-pin') || '', settings.admin_hash);
  const needAdmin = () => { if (!pinOk) throw new ApiError(401, 'Admin PIN required / ॲडमिन पिन आवश्यक'); };
  const rid = parts[1] && /^\d+$/.test(parts[1]) ? parseInt(parts[1], 10) : null;

  // ----- menu -----
  if (res === 'menu' && method === 'GET') return menuView(await getMenu(db));

  if (res === 'login' && method === 'POST') {
    if (checkPw(String(body.pin ?? ''), settings.admin_hash)) return { ok: true };
    await sleep(500);
    throw new ApiError(401, 'Wrong PIN / चुकीचा पिन');
  }

  // ----- settings -----
  if (res === 'settings') {
    const view = s => Object.fromEntries(PUBLIC_KEYS.map(k => [k, s[k] ?? '']));
    if (method === 'GET') return view(settings);
    if (method === 'PUT') {
      needAdmin();
      const newpin = String(body.new_pin ?? '').trim();
      const newpw = String(body.new_password ?? '').trim();
      if (newpin && newpin.length < 4) throw new ApiError(400, 'PIN must be at least 4 characters / पिन किमान ४ अंकी हवा');
      if (newpw && newpw.length < 6) throw new ApiError(400, 'Password must be at least 6 characters / पासवर्ड किमान ६ अक्षरी हवा');
      const s2 = await update(db, 'settings', s => {
        for (const k of PUBLIC_KEYS) if (k in body) s[k] = String(body[k]).trim();
        if (newpin) s.admin_hash = hashPw(newpin);
        if (newpw) s.app_hash = hashPw(newpw);
      });
      const out = view(s2);
      if (newpw) out.token = newToken(s2);   // keep this device logged in
      return out;
    }
  }

  // ----- categories -----
  if (res === 'categories') {
    needAdmin();
    if (method === 'POST' || method === 'PUT') {
      const mr = String(body.name_mr ?? '').trim(), en = String(body.name_en ?? '').trim();
      if (!mr && !en) throw new ApiError(400, 'Name required / नाव आवश्यक');
      const sort = Math.trunc(toFloat(body.sort, 0)), section = sec(body.section);
      let out;
      await update(db, 'menu', m => {
        if (method === 'POST') {
          m.seq.cat += 1; out = { id: m.seq.cat, name_mr: mr, name_en: en, sort, section }; m.categories.push(out);
        } else {
          out = m.categories.find(c => c.id === rid);
          if (!out) throw new ApiError(404, 'Not found');
          Object.assign(out, { name_mr: mr, name_en: en, sort, section });
        }
      }, () => getMenu(db));
      return out;
    }
    if (method === 'DELETE' && rid) {
      await update(db, 'menu', m => {
        m.items = m.items.filter(i => i.category_id !== rid);
        m.categories = m.categories.filter(c => c.id !== rid);
      }, () => getMenu(db));
      return { ok: true };
    }
  }

  // ----- items -----
  if (res === 'items') {
    needAdmin();
    if (method === 'POST' || method === 'PUT') {
      const mr = String(body.name_mr ?? '').trim(), en = String(body.name_en ?? '').trim();
      if (!mr && !en) throw new ApiError(400, 'Name required / नाव आवश्यक');
      const cid = Math.trunc(toFloat(body.category_id, 0));
      const typ = body.type === 'nonveg' ? 'nonveg' : 'veg';
      const active = (body.active ?? 1) ? 1 : 0;
      const variants = cleanVariants(body.variants);
      let out;
      const nv = await update(db, 'menu', m => {
        if (!m.categories.some(c => c.id === cid)) throw new ApiError(400, 'Select category / विभाग निवडा');
        if (method === 'POST') {
          m.seq.item += 1;
          const mx = Math.max(0, ...m.items.filter(i => i.category_id === cid).map(i => i.sort)) + 1;
          out = { id: m.seq.item, category_id: cid, name_mr: mr, name_en: en, type: typ, variants, active, sort: mx };
          m.items.push(out);
        } else {
          out = m.items.find(i => i.id === rid);
          if (!out) throw new ApiError(404, 'Not found');
          Object.assign(out, { category_id: cid, name_mr: mr, name_en: en, type: typ, variants, active });
        }
      }, () => getMenu(db));
      return { ...out, section: sec((nv.categories.find(c => c.id === out.category_id) || {}).section) };
    }
    if (method === 'DELETE' && rid) {
      await update(db, 'menu', m => { m.items = m.items.filter(i => i.id !== rid); }, () => getMenu(db));
      return { ok: true };
    }
  }

  // ----- open table orders -----
  if (res === 'orders') {
    const tno = (parts[1] || '').trim().slice(0, 20);
    if (!tno) {
      if (method === 'GET') {
        const c = await db.get('orders');
        return Object.values(c ? c.v : {}).map(orderRow).sort((a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : 0));
      }
    } else {
      const action = parts[2] || '';
      if (method === 'GET') {
        const c = await db.get('orders');
        const o = c && c.v[tno];
        return o ? orderRow(o) : blankOrder(tno);
      }
      if (method === 'PUT') {
        const lines = cleanLines(body.items);
        const customer = String(body.customer ?? '').trim().slice(0, 60);
        let out;
        await update(db, 'orders', m => {
          if (!lines.length) { delete m[tno]; out = blankOrder(tno); return; }
          const now = nowStr();
          m[tno] = { table_no: tno, customer, items: lines, created_at: m[tno] ? m[tno].created_at : now, updated_at: now };
          out = orderRow(m[tno]);
        }, () => ({}));
        return out;
      }
      if (method === 'DELETE') {
        await update(db, 'orders', m => { delete m[tno]; }, () => ({}));
        return { ok: true };
      }
      if (method === 'POST' && action === 'checkout') {
        // claim the order first (so it can never be billed twice), then create the bills
        let claimed;
        await update(db, 'orders', m => { claimed = m[tno]; delete m[tno]; }, () => ({}));
        if (!claimed) throw new ApiError(404, 'No order on this table / या टेबलवर ऑर्डर नाही');
        try {
          const o = orderRow(claimed);
          const disc = body.discounts && typeof body.discounts === 'object' ? body.discounts : {};
          const entries = SECTIONS.map(s => ({ section: s, lines: o.items.filter(l => sec(l.section) === s), discount: disc[s] })).filter(e => e.lines.length);
          return { bills: await addBills(db, entries, normTs(body.created_at), tno, o.customer) };
        } catch (e) {
          await update(db, 'orders', m => { if (!m[tno]) m[tno] = claimed; }, () => ({}));   // put the table back
          throw e;
        }
      }
    }
  }

  // ----- bills -----
  if (res === 'bills') {
    if (method === 'POST') {
      const lines = cleanLines(body.items);
      if (!lines.length) throw new ApiError(400, 'Bill is empty / बिल रिकामे आहे');
      const [b] = await addBills(db, [{ section: sec(body.section), lines, discount: body.discount }], normTs(body.created_at), body.table_no, body.customer);
      return b;
    }
    if (method === 'GET') {
      const d = (q.date || nowStr().slice(0, 10)).slice(0, 10);
      const arr = await billsOfDay(db, d);
      return arr.sort((a, b) => (a.created_at < b.created_at ? 1 : a.created_at > b.created_at ? -1 : b.id - a.id));
    }
    if (method === 'DELETE' && rid) {
      needAdmin();
      const d = String(q.date || '').slice(0, 10);
      if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) throw new ApiError(400, 'date required');
      await update(db, 'bills/' + d, arr => arr.filter(b => b.id !== rid), () => []);
      return { ok: true };
    }
  }

  // ----- reports -----
  if (res === 'report' && method === 'GET') {
    const kind = parts[1] || 'day';
    if (kind === 'day') {
      const bills = await billsOfDay(db, (q.date || nowStr().slice(0, 10)).slice(0, 10));
      const out = summarize(bills);
      out.sections = {};
      for (const s of SECTIONS) {
        const sb = bills.filter(b => sec(b.section) === s);
        out.sections[s] = { ...summarize(sb), items: aggItems(sb) };
      }
      return out;
    }
    if (kind === 'month') {
      const m = q.month || nowStr().slice(0, 7);
      const bills = await billsOfRange(db, m, m);
      const out = summarize(bills);
      const days = {};
      for (const b of bills) (days[b.created_at.slice(0, 10)] ||= []).push(b);
      out.days = Object.keys(days).sort().map(k => ({ date: k, ...summarize(days[k]) }));
      return out;
    }
  }

  // ----- CSV export (any month range, e.g. a whole year) -----
  if (res === 'export' && method === 'GET') {
    let frm = q.from || q.month || nowStr().slice(0, 7), to = q.to || frm;
    for (const v of [frm, to]) if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(v)) throw new ApiError(400, 'Invalid month / चुकीचा महिना');
    if (frm > to) [frm, to] = [to, frm];
    const only = SECTIONS.includes(q.section) ? q.section : '';
    let bills = (await billsOfRange(db, frm, to)).sort((a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : a.id - b.id));
    if (only) bills = bills.filter(b => sec(b.section) === only);
    let csv = '';
    if (q.kind === 'summary') {
      csv += csvRow(['Month', 'Bills', 'Hotel Total', 'Bar Total', 'Discount', 'Total']);
      const months = {};
      for (const b of bills) (months[b.created_at.slice(0, 7)] ||= []).push(b);
      for (const k of Object.keys(months).sort()) { const s = summarize(months[k]); csv += csvRow([k, s.count, s.hotel, s.bar, s.discount, s.total]); }
      const s = summarize(bills);
      csv += csvRow(['TOTAL', s.count, s.hotel, s.bar, s.discount, s.total]);
    } else {
      csv += csvRow(['Bill No', 'Date Time', 'Section', 'Table', 'Customer', 'Items', 'Subtotal', 'Discount', 'Total']);
      for (const b of bills) {
        const items = b.items.map(l => (l.name_en || l.name_mr) + ((l.ven || l.vmr) ? ' (' + (l.ven || l.vmr) + ')' : '') + ' x' + l.qty + ' @' + l.price).join('; ');
        csv += csvRow([b.id, b.created_at, sec(b.section) === 'bar' ? 'Bar' : 'Hotel', b.table_no, b.customer, items, b.subtotal, b.discount, b.total]);
      }
      const s = summarize(bills);
      csv += csvRow(['', '', '', '', '', 'TOTAL', s.subtotal, s.discount, s.total]);
    }
    const name = `akshara-${q.kind === 'summary' ? 'summary' : 'bills'}-${frm}${frm === to ? '' : '_to_' + to}${only ? '-' + only : ''}.csv`;
    return new Response('﻿' + csv, { status: 200, headers: { 'Content-Type': 'text/csv; charset=utf-8', 'Content-Disposition': `attachment; filename="${name}"`, 'Cache-Control': 'no-store' } });
  }

  // ----- one-time import of the old Python database (tools/export_db.py) -----
  if (res === 'import' && method === 'POST') {
    needAdmin();
    if (!Array.isArray(body.categories) || !Array.isArray(body.items) || !Array.isArray(body.bills)) throw new ApiError(400, 'Not a valid export file');
    const cats = body.categories.map(c => ({ id: +c.id, name_mr: String(c.name_mr ?? ''), name_en: String(c.name_en ?? ''), sort: +c.sort || 0, section: sec(c.section) }));
    const items = body.items.map(i => ({
      id: +i.id, category_id: +i.category_id, name_mr: String(i.name_mr ?? ''), name_en: String(i.name_en ?? ''),
      type: i.type === 'nonveg' ? 'nonveg' : 'veg', variants: cleanVariants(i.variants), active: i.active ? 1 : 0, sort: +i.sort || 0,
    }));
    await db.put('menu', { categories: cats, items, seq: { cat: Math.max(0, ...cats.map(c => c.id)), item: Math.max(0, ...items.map(i => i.id)) } });
    for (const k of await db.list('bills/')) await db.del(k);
    const days = {};
    let maxId = 0;
    for (const b of body.bills) {
      const bill = {
        id: +b.id, created_at: String(b.created_at).slice(0, 16), table_no: String(b.table_no ?? ''), customer: String(b.customer ?? ''),
        items: cleanLines(b.items), subtotal: num(b.subtotal), discount: num(b.discount), total: num(b.total), section: sec(b.section),
      };
      maxId = Math.max(maxId, bill.id);
      (days[bill.created_at.slice(0, 10)] ||= []).push(bill);
    }
    for (const [d, arr] of Object.entries(days)) await db.put('bills/' + d, arr);
    await update(db, 'meta', m => { m.billSeq = Math.max(m.billSeq || 0, maxId); }, () => ({ billSeq: 0 }));
    if (body.settings && typeof body.settings === 'object') {
      await update(db, 'settings', s => { for (const k of PUBLIC_KEYS) if (k in body.settings) s[k] = String(body.settings[k]); });
    }
    return { categories: cats.length, items: items.length, bills: body.bills.length };
  }

  throw new ApiError(404, 'Not found');
}

export default async (req) => {
  const url = new URL(req.url);
  const parts = url.pathname.replace(/^\/(\.netlify\/functions\/)?api\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
  const q = Object.fromEntries(url.searchParams);
  let body = {};
  if (req.method === 'POST' || req.method === 'PUT') {
    try { body = await req.json(); } catch { body = {}; }
    if (!body || typeof body !== 'object' || Array.isArray(body)) body = {};
  }
  try {
    const out = await route(await openDb(), req.method, parts, q, body, req);
    return out instanceof Response ? out : json(out);
  } catch (e) {
    if (e instanceof ApiError) return json({ error: e.msg, ...(e.auth ? { auth: true } : {}) }, e.code);
    console.error(e);
    return json({ error: 'Server error: ' + e.message }, 500);
  }
};

export const config = { path: '/api/*' };
