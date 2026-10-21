// TREK MCP auth-proxy (skill-bundled copy).
// WorkBuddy's static ~/.workbuddy/.mcp.json cannot perform an OAuth client_credentials
// exchange, so this local proxy does it:
//   - exposes http://127.0.0.1:<proxyPort>/mcp (Streamable HTTP)
//   - swaps the Machine client id/secret for an access token at TREK /oauth/token
//     (cached, auto-renewed 5 minutes before expiry)
//   - injects `Authorization: Bearer <token>` and forwards to TREK /mcp,
//     passing Mcp-Session-Id through in BOTH directions (critical: dropping the
//     response header opens a brand-new MCP session on every tool call)
// Dependencies: Node built-ins only. No npm install.
import http from 'node:http';
import { cfg, CONFIG_PATH, TREK_BASE, PROXY_PORT } from './proxy-config.mjs';

const CLIENT_ID = cfg.clientId;
const CLIENT_SECRET = cfg.clientSecret;
const REFRESH_SKEW_MS = 5 * 60 * 1000;

if (!CLIENT_ID || !CLIENT_SECRET) {
  console.error(`[proxy] FATAL: clientId/clientSecret missing in ${CONFIG_PATH}`);
  process.exit(1);
}

let tokenCache = { token: null, expiresAt: 0 };
let inflight = null;

function getToken() {
  if (tokenCache.token && Date.now() < tokenCache.expiresAt - REFRESH_SKEW_MS) {
    return Promise.resolve(tokenCache.token);
  }
  if (inflight) return inflight;
  inflight = new Promise((resolve, reject) => {
    const body = new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
    }).toString();
    const req = http.request(`${TREK_BASE}/oauth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Content-Length': Buffer.byteLength(body),
      },
    }, (res) => {
      let d = '';
      res.on('data', (c) => (d += c));
      res.on('end', () => {
        inflight = null;
        try {
          const j = JSON.parse(d);
          if (!j.access_token) return reject(new Error('no access_token: ' + d.slice(0, 200)));
          tokenCache = { token: j.access_token, expiresAt: Date.now() + (j.expires_in || 3600) * 1000 };
          const scopeCount = ((j.scope || '').match(/ /g) || []).length + 1;
          console.log(`[token] refreshed, expires_in=${j.expires_in}s, scopes=${scopeCount}`);
          resolve(j.access_token);
        } catch {
          reject(new Error('token parse error: ' + d.slice(0, 200)));
        }
      });
    });
    req.on('error', (e) => { inflight = null; reject(e); });
    req.write(body);
    req.end();
  });
  return inflight;
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://localhost:${PROXY_PORT}`);
  if (url.pathname === '/health') {
    res.writeHead(200, { 'Content-Type': 'text/plain' }).end('ok');
    return;
  }
  if (url.pathname !== '/mcp') {
    res.writeHead(404, { 'Content-Type': 'text/plain' }).end('not found');
    return;
  }
  try {
    const token = await getToken();
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = Buffer.concat(chunks);

    const target = new URL('/mcp', TREK_BASE);
    const headers = { ...req.headers };
    delete headers.host;
    delete headers.authorization;
    delete headers['content-length'];
    delete headers.connection;
    headers['authorization'] = `Bearer ${token}`;
    if (body.length) headers['content-length'] = String(body.length);

    const proxyReq = http.request(target, { method: req.method, headers }, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });
    proxyReq.on('error', (e) => {
      console.error('[proxy] upstream error', e.message);
      if (!res.headersSent) res.writeHead(502, { 'Content-Type': 'text/plain' }).end('upstream error: ' + e.message);
    });
    if (body.length) proxyReq.write(body);
    proxyReq.end();
  } catch (e) {
    console.error('[proxy] error', e.message);
    if (!res.headersSent) res.writeHead(500, { 'Content-Type': 'text/plain' }).end('proxy error: ' + e.message);
  }
});

server.listen(PROXY_PORT, '127.0.0.1', () => {
  console.log(`TREK MCP auth-proxy listening on http://127.0.0.1:${PROXY_PORT}/mcp  ->  ${TREK_BASE}/mcp  [config: ${CONFIG_PATH}]`);
});
