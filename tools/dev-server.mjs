// Local test server (no Netlify account needed):  npm run dev  ->  http://localhost:8888
// Same API code as production, data kept as plain files in ./.local-data
import http from 'node:http';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

process.env.AKSHARA_LOCAL_DIR ||= path.join(path.dirname(fileURLToPath(import.meta.url)), '..', '.local-data');
const { default: api } = await import('../netlify/functions/api.mjs');
const pub = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'public');
const port = +process.env.PORT || 8888;
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png' };

http.createServer(async (req, res) => {
  try {
    if (req.url.startsWith('/api/')) {
      const chunks = []; for await (const c of req) chunks.push(c);
      const r = await api(new Request('http://localhost' + req.url, { method: req.method, headers: req.headers, body: ['GET', 'HEAD'].includes(req.method) ? undefined : Buffer.concat(chunks) }));
      res.writeHead(r.status, Object.fromEntries(r.headers));
      return res.end(Buffer.from(await r.arrayBuffer()));
    }
    let f = req.url.split('?')[0]; if (f === '/') f = '/index.html';
    const data = await readFile(path.join(pub, path.normalize(f).replace(/^(\.\.[\/\\])+/, '')));
    res.writeHead(200, { 'Content-Type': types[path.extname(f)] || 'application/octet-stream' });
    res.end(data);
  } catch (e) { res.writeHead(404); res.end('Not found'); }
}).listen(port, () => console.log('Hotel Akshara (local test) on http://localhost:' + port));
