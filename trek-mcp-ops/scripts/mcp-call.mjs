#!/usr/bin/env node
// Direct TREK MCP bridge — call any of the 135 tools WITHOUT restarting WorkBuddy.
//
//   node mcp-call.mjs <tool> [jsonArgs]      call a tool
//   node mcp-call.mjs <tool> @args.json      read the arguments from a JSON file
//                                            (use this for long / Chinese text —
//                                             avoids shell quoting corruption)
//   node mcp-call.mjs --list [keyword]       list tool names (optionally filtered)
//   node mcp-call.mjs --schema <tool>        print a tool's input schema
//                                            (settles snake_case vs camelCase doubts)
//   ... --force                              skip the argument pre-check
//
// ARGUMENT PRE-CHECK (on by default): TREK SILENTLY IGNORES unknown properties and
// still answers 200/OK, so a typo like `durationMinutes` (correct: `duration_minutes`)
// looks like a success while nothing changed. Before every call the arguments are
// validated against the tool's own inputSchema; unknown or missing-required keys abort
// the call with the correct names listed.
//
// Talks to the local auth-proxy, which injects the OAuth token.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { MCP_URL, PROXY_PORT } from './env.mjs';

// Agents usually work in git-bash, where paths look like /tmp/x.json or /d/proj/x.json.
// Node on Windows cannot open those, so translate the common MSYS forms.
function resolveArgsPath(p) {
  const tried = [p];
  if (fs.existsSync(p)) return p;
  const drive = /^\/([a-zA-Z])\/(.*)$/.exec(p);          // /d/proj/x.json -> D:\proj\x.json
  if (drive) {
    const w = `${drive[1].toUpperCase()}:\\${drive[2].replace(/\//g, '\\')}`;
    tried.push(w);
    if (fs.existsSync(w)) return w;
  }
  if (p.startsWith('/tmp/')) {                            // /tmp/x.json -> %TEMP%\x.json
    const w = path.join(os.tmpdir(), p.slice(5).replace(/\//g, '\\'));
    tried.push(w);
    if (fs.existsSync(w)) return w;
  }
  if (p.startsWith('~/')) {
    const w = path.join(os.homedir(), p.slice(2).replace(/\//g, '\\'));
    tried.push(w);
    if (fs.existsSync(w)) return w;
  }
  const abs = path.resolve(p);
  tried.push(abs);
  if (fs.existsSync(abs)) return abs;
  return { notFound: tried };
}

const rawArgv = process.argv.slice(2);
const FORCE = rawArgv.includes('--force');
const argv = rawArgv.filter((a) => a !== '--force');
if (argv.length === 0) {
  console.error('Usage: node mcp-call.mjs <tool> [jsonArgs|@file.json]');
  console.error('       node mcp-call.mjs --list [keyword]');
  console.error('       node mcp-call.mjs --schema <tool>');
  process.exit(2);
}

function post(body, sessionId) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/event-stream',
      'Content-Length': Buffer.byteLength(data),
    };
    if (sessionId) headers['Mcp-Session-Id'] = sessionId;
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
    req.setTimeout(30000, () => { req.destroy(new Error('request timed out after 30s')); });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function connect() {
  let init;
  try {
    init = await post({
      jsonrpc: '2.0', id: 1, method: 'initialize',
      params: { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'wb-direct', version: '2' } },
    });
  } catch (e) {
    console.error(`[!] Cannot reach the TREK MCP proxy at ${MCP_URL} (${e.message}).`);
    console.error('    TREK is probably not running. Bring it up first:');
    console.error('      node scripts/trek-control.mjs start');
    process.exit(1);
  }
  if (!init.sid) {
    console.error(`[!] MCP initialize failed (status=${init.status}): ${String(init.raw).slice(0, 300)}`);
    console.error('    Diagnose with: node scripts/trek-control.mjs doctor');
    process.exit(1);
  }
  await post({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} }, init.sid);
  return init.sid;
}

async function listTools(sid) {
  const r = await post({ jsonrpc: '2.0', id: 2, method: 'tools/list', params: {} }, sid);
  const tools = r.body?.result?.tools;
  if (!Array.isArray(tools)) {
    console.error('[!] tools/list failed: ' + String(r.raw).slice(0, 300));
    process.exit(1);
  }
  return tools;
}

const sid = await connect();

// ---------------------------------------------------------------- --list
if (argv[0] === '--list') {
  const kw = (argv[1] || '').toLowerCase();
  const tools = await listTools(sid);
  const hit = kw
    ? tools.filter((t) => t.name.toLowerCase().includes(kw) || (t.description || '').toLowerCase().includes(kw))
    : tools;
  for (const t of hit) console.log(`${t.name}\t${(t.description || '').split('\n')[0].slice(0, 110)}`);
  console.log(`\n(${hit.length}/${tools.length} tools${kw ? ` matching "${kw}"` : ''})`);
  process.exit(0);
}

// -------------------------------------------------------------- --schema
if (argv[0] === '--schema') {
  const name = argv[1];
  if (!name) { console.error('Usage: node mcp-call.mjs --schema <tool>'); process.exit(2); }
  const tools = await listTools(sid);
  const t = tools.find((x) => x.name === name);
  if (!t) {
    const near = tools.filter((x) => x.name.includes(name)).map((x) => x.name).slice(0, 10);
    console.error(`[!] tool "${name}" not found.` + (near.length ? ' Did you mean: ' + near.join(', ') : ''));
    process.exit(1);
  }
  console.log(t.name);
  if (t.description) console.log(t.description);
  console.log(JSON.stringify(t.inputSchema, null, 2));
  process.exit(0);
}

// ------------------------------------------------------------- tool call
const tool = argv[0];
let args = {};
if (argv[1]) {
  const spec = argv[1];
  let text = spec;
  if (spec.startsWith('@')) {
    const f = resolveArgsPath(spec.slice(1));
    if (typeof f !== 'string') {
      console.error('[!] args file not found. Tried:');
      for (const t of f.notFound) console.error('      ' + t);
      process.exit(2);
    }
    text = fs.readFileSync(f, 'utf8');
  }
  try { args = JSON.parse(text); }
  catch (e) {
    console.error(`[!] Invalid JSON args: ${e.message}`);
    console.error('    Tip: for long or non-ASCII payloads write a .json file and pass @that-file.json');
    process.exit(2);
  }
}

// --- argument pre-check against the tool's own schema (TREK drops unknown keys silently)
if (!FORCE) {
  const tools = await listTools(sid);
  const def = tools.find((t) => t.name === tool);
  if (!def) {
    const near = tools.filter((t) => t.name.includes(tool.replace(/^(get|list|create|update|delete)_/, ''))).map((t) => t.name).slice(0, 8);
    console.error(`[!] tool "${tool}" does not exist.` + (near.length ? '\n    Closest: ' + near.join(', ') : ''));
    console.error('    Browse with: node scripts/mcp-call.mjs --list <keyword>');
    process.exit(1);
  }
  const props = def.inputSchema?.properties || {};
  const known = Object.keys(props);
  const unknown = Object.keys(args).filter((k) => !known.includes(k));
  const missing = (def.inputSchema?.required || []).filter((k) => !(k in args));
  if (unknown.length || missing.length) {
    console.error(`[!] Argument check failed for "${tool}" — call ABORTED (nothing was changed).`);
    if (unknown.length) {
      console.error(`    Unknown key(s): ${unknown.join(', ')}`);
      for (const u of unknown) {
        const norm = (s) => s.toLowerCase().replace(/[^a-z0-9]/g, '');
        const cand = known.filter((k) => norm(k) === norm(u));
        if (cand.length) console.error(`      "${u}" -> did you mean "${cand[0]}"? (TREK mixes camelCase ids with snake_case fields)`);
      }
      console.error(`    Accepted keys: ${known.join(', ')}`);
    }
    if (missing.length) console.error(`    Missing required: ${missing.join(', ')}`);
    console.error(`    Full schema: node scripts/mcp-call.mjs --schema ${tool}`);
    console.error('    Override (not recommended): add --force');
    process.exit(1);
  }
}

const r = await post({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: tool, arguments: args } }, sid);
const result = r.body?.result;
if (!result) {
  const err = r.body?.error;
  console.error(`[!] Call failed (status=${r.status}, port=${PROXY_PORT}).`);
  console.error(err ? `    ${err.code}: ${err.message}` : `    ${String(r.raw).slice(0, 400)}`);
  console.error(`    Inspect the expected arguments with: node scripts/mcp-call.mjs --schema ${tool}`);
  process.exit(1);
}
if (result.isError) console.error('[tool reported error]');
for (const c of result.content || []) {
  if (c.type === 'text') console.log(c.text);
  else console.log(JSON.stringify(c));
}
process.exit(result.isError ? 1 : 0);
