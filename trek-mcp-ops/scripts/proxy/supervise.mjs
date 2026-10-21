// Supervisor for TREK MCP auth-proxy
// - single-instance guard: if :3001 already listening, exit cleanly (no EADDRINUSE)
// - crash self-heal: respawns the proxy 2s after any unexpected exit
// - logging: mirrors proxy stdout/stderr to console AND proxy.log (timestamped)
// - PID file: writes supervisor.pid so trek-stop.bat can kill the supervisor (not just the child)
import { spawn } from 'node:child_process';
import net from 'node:net';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PROXY_PORT } from './proxy-config.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const NODE = process.execPath; // never goes stale when the bundled Node version changes
const PROXY = path.join(__dirname, 'trek-mcp-proxy.mjs');
const LOG = path.join(__dirname, 'proxy.log');
const PIDFILE = path.join(__dirname, 'supervisor.pid');
const HOST = '127.0.0.1';
const PORT = PROXY_PORT;

function log(line) {
  const msg = `[${new Date().toISOString()}] ${line}`;
  console.log(msg);
  try { fs.appendFileSync(LOG, msg + '\n'); } catch {}
}

function portListening(cb) {
  const sock = net.connect(PORT, HOST);
  sock.setTimeout(1000);
  sock.on('connect', () => { sock.destroy(); cb(true); });
  sock.on('timeout', () => { sock.destroy(); cb(false); });
  sock.on('error', () => { sock.destroy(); cb(false); });
}

function writePid() {
  try { fs.writeFileSync(PIDFILE, String(process.pid)); } catch {}
}
function clearPid() {
  try { fs.unlinkSync(PIDFILE); } catch {}
}

let child = null;
let stopping = false;

function run() {
  log('[supervisor] launching trek-mcp-proxy.mjs ...');
  child = spawn(NODE, [PROXY], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
  child.stdout.on('data', (d) => {
    d.toString().split('\n').forEach((l) => l.trim() && log('[proxy] ' + l.trim()));
  });
  child.stderr.on('data', (d) => {
    d.toString().split('\n').forEach((l) => l.trim() && log('[proxy!] ' + l.trim()));
  });
  child.on('exit', (code, sig) => {
    if (stopping) return;
    log(`[supervisor] proxy exited (code=${code} sig=${sig}); respawn in 2s ...`);
    setTimeout(run, 2000);
  });
}

function shutdown() {
  if (stopping) return;
  stopping = true;
  log('[supervisor] shutting down ...');
  if (child) child.kill('SIGTERM');
  clearPid();
  setTimeout(() => process.exit(0), 400);
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

portListening((up) => {
  if (up) {
    log('[supervisor] :3001 already listening — proxy already running. Exiting (no-op).');
    process.exit(0);
  }
  writePid();
  run();
});
