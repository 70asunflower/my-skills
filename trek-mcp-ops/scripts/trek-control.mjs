#!/usr/bin/env node
// TREK lifecycle orchestrator — start / stop / status / doctor
//
//   node trek-control.mjs doctor   # verify every path & dependency, change nothing
//   node trek-control.mjs status   # what is currently up (docker / trek / proxy / mcp)
//   node trek-control.mjs start    # Docker Desktop -> compose up -> proxy -> self-test
//   node trek-control.mjs stop     # proxy down -> compose down -> quit Docker Desktop
//
// All paths are resolved at runtime by env.mjs (no hardcoded node version, no
// hardcoded docker path). Every failure prints an actionable fix.
import { spawn, execFileSync } from 'node:child_process';
import net from 'node:net';
import fs from 'node:fs';
import http from 'node:http';
import {
  NODE, DOCKER_CLI, DOCKER_DESKTOP, DEPLOY, PROXY_DIR, SUPERVISE, PIDFILE, PROXY_LOG,
  PROXY_CONFIG, PROXY_PORT, TREK_PORT, HEALTH_URL, MCP_URL, HAS_CREDENTIALS,
  preflight, describe,
} from './env.mjs';

const cmd = (process.argv[2] || 'status').toLowerCase();
const say = (m) => console.log(m);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ------------------------------------------------------------------ helpers
function sh(file, args, opts = {}) {
  return execFileSync(file, args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], ...opts });
}
function trySh(file, args, opts = {}) {
  try { return { ok: true, out: sh(file, args, opts) }; }
  catch (e) { return { ok: false, out: (e.stdout || '') + (e.stderr || e.message || '') }; }
}
function dockerRunning() {
  return trySh(DOCKER_CLI, ['info', '--format', '{{.ServerVersion}}']).ok;
}
function portListening(port) {
  return new Promise((res) => {
    const s = net.connect(port, '127.0.0.1');
    s.setTimeout(800);
    s.on('connect', () => { s.destroy(); res(true); });
    s.on('timeout', () => { s.destroy(); res(false); });
    s.on('error', () => { s.destroy(); res(false); });
  });
}
function httpGet(url, timeout = 3000) {
  return new Promise((res) => {
    const req = http.get(url, (r) => {
      let b = ''; r.on('data', (c) => (b += c));
      r.on('end', () => res({ status: r.statusCode, body: b }));
    });
    req.setTimeout(timeout, () => { req.destroy(); res({ status: 0, body: '' }); });
    req.on('error', () => res({ status: 0, body: '' }));
  });
}
// detached + unref + ignored stdio => the child outlives this script (and WorkBuddy).
// NOTE: launch executables DIRECTLY. Going through `cmd /c start ...` is a quoting
// minefield on Windows (an extra pair of quotes silently turns the exe into an
// argument of an empty command and nothing launches, with exit code 0).
function spawnDetached(file, args = []) {
  const p = spawn(file, args, { detached: true, stdio: 'ignore', windowsHide: true });
  p.unref();
  return p;
}
function processRunning(imageName) {
  const r = trySh('tasklist', ['/FI', `IMAGENAME eq ${imageName}`]);
  return r.ok && r.out.toLowerCase().includes(imageName.toLowerCase());
}
function killPort(port) {
  const r = trySh('cmd', ['/c', `netstat -ano | findstr :${port} | findstr LISTENING`]);
  if (!r.ok) return 0;
  const pids = new Set(r.out.split(/\r?\n/).map((l) => l.trim().split(/\s+/).pop()).filter((p) => /^\d+$/.test(p) && p !== '0'));
  let n = 0;
  for (const pid of pids) { if (trySh('taskkill', ['/f', '/pid', pid]).ok) n++; }
  return n;
}

function reportProblems(pf) {
  for (const p of pf.problems) {
    say(`  [${p.level.toUpperCase()}] ${p.msg}`);
    say(`          fix: ${p.fix}`);
  }
}

// ------------------------------------------------------------------- doctor
async function doctor() {
  say('=== TREK doctor ===');
  say(describe());
  say('');
  const pf = preflight();
  if (pf.problems.length === 0) say('  all dependencies resolved.');
  else reportProblems(pf);
  say('');
  say('--- runtime state ---');
  const dk = dockerRunning();
  say(`  docker daemon : ${dk ? 'RUNNING' : 'stopped'}`);
  const trekUp = dk ? (await httpGet(HEALTH_URL)).status === 200 : false;
  say(`  trek :${TREK_PORT}    : ${trekUp ? 'HEALTHY' : 'down'}`);
  const px = await portListening(PROXY_PORT);
  say(`  proxy :${PROXY_PORT}   : ${px ? 'LISTENING' : 'down'}`);
  if (px) {
    const ping = await mcpPing();
    say(`  mcp handshake : ${ping.ok ? `OK (${ping.tools} tools)` : 'FAILED — ' + ping.err}`);
  }
  say('');
  say(pf.ok ? '=> Ready. Bring everything up with:  trek.cmd start'
            : '=> BLOCKED. Fix the FATAL items above first.');
  process.exit(pf.ok ? 0 : 1);
}

// --------------------------------------------------------------- mcp ping
// Full MCP handshake through the proxy: proves docker + trek + oauth + proxy all work.
function mcpPost(body, sid) {
  return new Promise((resolve) => {
    const data = JSON.stringify(body);
    const headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
      'Content-Length': Buffer.byteLength(data),
    };
    if (sid) headers['Mcp-Session-Id'] = sid;
    const req = http.request(MCP_URL, { method: 'POST', headers }, (res) => {
      let buf = '';
      res.on('data', (c) => (buf += c));
      res.on('end', () => {
        let b = null;
        if ((res.headers['content-type'] || '').includes('text/event-stream')) {
          for (const l of buf.split('\n').filter((x) => x.startsWith('data:'))) {
            try { b = JSON.parse(l.slice(5).trim()); } catch {}
          }
        } else { try { b = JSON.parse(buf); } catch {} }
        resolve({ status: res.statusCode, sid: res.headers['mcp-session-id'], body: b, raw: buf });
      });
    });
    req.setTimeout(8000, () => { req.destroy(); resolve({ status: 0, raw: 'timeout' }); });
    req.on('error', (e) => resolve({ status: 0, raw: e.message }));
    req.write(data); req.end();
  });
}
async function mcpPing() {
  const init = await mcpPost({
    jsonrpc: '2.0', id: 1, method: 'initialize',
    params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'trek-control', version: '2' } },
  });
  if (!init.sid) return { ok: false, err: `initialize failed (status=${init.status}) ${String(init.raw).slice(0, 160)}` };
  await mcpPost({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} }, init.sid);
  const list = await mcpPost({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }, init.sid);
  const tools = list.body?.result?.tools;
  if (!Array.isArray(tools)) return { ok: false, err: `tools/list failed ${String(list.raw).slice(0, 160)}` };
  return { ok: true, tools: tools.length };
}

// -------------------------------------------------------------------- start
async function start() {
  const pf = preflight();
  if (!pf.ok) {
    say('[!] preflight failed — cannot start:');
    reportProblems(pf);
    say('\nRun `trek.cmd doctor` for the full picture.');
    process.exit(1);
  }
  if (pf.problems.length) reportProblems(pf); // warnings only

  // 1) Docker daemon
  if (!dockerRunning()) {
    if (!DOCKER_DESKTOP) { say('[!] Docker is down and Docker Desktop.exe was not found. Start Docker manually.'); process.exit(1); }
    say('[1/4] Docker daemon down -> launching Docker Desktop (headless)...');
    spawnDetached(DOCKER_DESKTOP);
    // Verify the process actually appeared before waiting 3 minutes on a no-op.
    let appeared = false;
    for (let i = 0; i < 10 && !appeared; i++) { await sleep(1500); appeared = processRunning('Docker Desktop.exe'); }
    if (!appeared) {
      say('[!] Docker Desktop.exe did not launch. Path used:');
      say('    ' + DOCKER_DESKTOP);
      say('    Start Docker Desktop manually, then re-run: trek.cmd start');
      process.exit(1);
    }
    say('      Docker Desktop process up, waiting for the daemon (can take ~1-2 min on a cold boot)...');
    const deadline = Date.now() + 240000;
    while (Date.now() < deadline) {
      await sleep(4000);
      if (dockerRunning()) break;
      process.stdout.write('.');
    }
    say('');
    if (!dockerRunning()) { say('[!] Docker daemon did not come up within 240s. Open Docker Desktop and check for errors.'); process.exit(1); }
    say('      docker daemon ready.');
  } else {
    say('[1/4] Docker daemon already running.');
  }

  // 2) TREK containers
  say('[2/4] docker compose up -d ...');
  const up = trySh(DOCKER_CLI, ['compose', 'up', '-d'], { cwd: DEPLOY });
  if (!up.ok) { say('[!] compose up failed:\n' + up.out.slice(0, 2000)); process.exit(1); }

  // 3) TREK health
  say(`[3/4] waiting for TREK health at ${HEALTH_URL} ...`);
  let healthy = false;
  const hDeadline = Date.now() + 120000;
  while (Date.now() < hDeadline) {
    if ((await httpGet(HEALTH_URL)).status === 200) { healthy = true; break; }
    await sleep(2500); process.stdout.write('.');
  }
  say('');
  if (!healthy) {
    say('[!] TREK did not become healthy. Container logs (tail):');
    say(trySh(DOCKER_CLI, ['compose', 'logs', '--tail', '40'], { cwd: DEPLOY }).out.slice(-2000));
    process.exit(1);
  }
  say('      TREK healthy.');

  // 4) auth-proxy supervisor (detached, survives WorkBuddy restart)
  if (await portListening(PROXY_PORT)) {
    say(`[4/4] proxy :${PROXY_PORT} already listening.`);
  } else {
    say(`[4/4] starting auth-proxy supervisor (${SUPERVISE}) ...`);
    spawnDetached(NODE, [SUPERVISE]);
    const pDeadline = Date.now() + 20000;
    while (Date.now() < pDeadline) {
      await sleep(1000);
      if (await portListening(PROXY_PORT)) break;
    }
    if (!(await portListening(PROXY_PORT))) {
      say(`[!] proxy did not start. Log: ${PROXY_LOG}`);
      if (PROXY_LOG && fs.existsSync(PROXY_LOG)) say(fs.readFileSync(PROXY_LOG, 'utf8').slice(-1500));
      process.exit(1);
    }
    say('      proxy up.');
  }

  // self-test: real MCP handshake, proves the entire chain end-to-end
  say('[self-test] MCP handshake through the proxy ...');
  let ping = await mcpPing();
  if (!ping.ok) { await sleep(2500); ping = await mcpPing(); } // one retry: token fetch on cold start
  if (!ping.ok) {
    say('[!] self-test FAILED: ' + ping.err);
    say(`    Check credentials in ${PROXY_CONFIG} and the proxy log ${PROXY_LOG}`);
    process.exit(1);
  }
  say(`      OK — ${ping.tools} MCP tools reachable.`);

  say('');
  say('TREK is READY.');
  say(`  Web UI  : http://localhost:${TREK_PORT}`);
  say(`  MCP     : ${MCP_URL}`);
  say('  Browse tools    : trek-call.cmd --list <keyword>');
  say('  Check arguments : trek-call.cmd --schema <tool>');
  say('  Call a tool     : trek-call.cmd <tool> @args.json');
  say('  Free resources  : trek.cmd stop');
}

// --------------------------------------------------------------------- stop
async function stop() {
  say('[1/4] stopping proxy supervisor ...');
  if (PIDFILE && fs.existsSync(PIDFILE)) {
    const pid = fs.readFileSync(PIDFILE, 'utf8').trim();
    if (/^\d+$/.test(pid)) trySh('taskkill', ['/f', '/t', '/pid', pid]);
    try { fs.unlinkSync(PIDFILE); } catch {}
  }
  const killed = killPort(PROXY_PORT);
  say(`      supervisor stopped, ${killed} listener(s) on :${PROXY_PORT} killed.`);

  if (DEPLOY && dockerRunning()) {
    say('[2/4] docker compose down ...');
    const dn = trySh(DOCKER_CLI, ['compose', 'down'], { cwd: DEPLOY });
    say(dn.ok ? '      containers removed (data preserved on bind mounts).'
              : '      compose down warning: ' + dn.out.slice(0, 400));
  } else {
    say('[2/4] docker not running — nothing to compose down.');
  }

  say('[3/4] quitting Docker Desktop to free RAM/CPU ...');
  const t = trySh('taskkill', ['/f', '/im', 'Docker Desktop.exe']);
  say(t.ok ? '      Docker Desktop quit.' : '      Docker Desktop was not running.');
  // Backend helpers linger otherwise and keep the WSL VM warm.
  for (const im of ['com.docker.backend.exe', 'com.docker.build.exe', 'docker.exe']) trySh('taskkill', ['/f', '/im', im]);

  say('[4/4] verifying ...');
  const px = await portListening(PROXY_PORT);
  const tk = (await httpGet(HEALTH_URL, 1500)).status === 200;
  say(`      :${PROXY_PORT} ${px ? 'STILL UP (!)' : 'free'} | trek :${TREK_PORT} ${tk ? 'STILL UP (!)' : 'down'} | docker ${dockerRunning() ? 'STILL RUNNING (!)' : 'stopped'}`);
  say('');
  say('TREK fully shut down. Resources released.');
}

// ------------------------------------------------------------------- status
async function status() {
  const dk = dockerRunning();
  const trekUp = dk ? (await httpGet(HEALTH_URL, 2000)).status === 200 : false;
  const px = await portListening(PROXY_PORT);
  say(`docker ${dk ? 'RUNNING' : 'stopped'} | trek :${TREK_PORT} ${trekUp ? 'HEALTHY' : 'down'} | proxy :${PROXY_PORT} ${px ? 'LISTENING' : 'down'}`);
  if (px) { const p = await mcpPing(); say(`mcp: ${p.ok ? `OK (${p.tools} tools)` : 'FAILED — ' + p.err}`); }
  const allUp = dk && trekUp && px;
  say(allUp ? '=> READY' : '=> NOT READY — run: trek.cmd start');
  process.exit(allUp ? 0 : 1);
}

switch (cmd) {
  case 'start': await start(); break;
  case 'stop': await stop(); break;
  case 'status': await status(); break;
  case 'doctor': await doctor(); break;
  default:
    say('Usage: node trek-control.mjs <doctor|status|start|stop>');
    process.exit(2);
}
