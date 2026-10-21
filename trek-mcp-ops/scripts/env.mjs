// Shared environment/path resolver for the trek-mcp-ops skill.
// Design goal: ZERO hardcoded fragile paths. Everything is resolved at runtime with
// explicit fallbacks and actionable error messages, so a fresh agent with no context
// can run the scripts and immediately understand what (if anything) is missing.
//
// Override any of these with environment variables:
//   TREK_DEPLOY_DIR     -> folder containing docker-compose.yml
//   TREK_PROXY_CONFIG   -> path to proxy-config.json
//   TREK_DOCKER_CLI     -> path to docker.exe
//   TREK_DOCKER_DESKTOP -> path to "Docker Desktop.exe"
// Or create C:\Users\<you>\.workbuddy\trek-mcp-ops.json :
//   { "deployDir": "...", "proxyConfig": "...", "dockerCli": "...", "dockerDesktop": "..." }
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
export const SKILL_DIR = path.dirname(SCRIPT_DIR);
export const HOME = os.homedir();

// ---------------------------------------------------------------- user config
const USER_CFG_PATH = path.join(HOME, '.workbuddy', 'trek-mcp-ops.json');
let userCfg = {};
try {
  if (fs.existsSync(USER_CFG_PATH)) userCfg = JSON.parse(fs.readFileSync(USER_CFG_PATH, 'utf8'));
} catch (e) {
  console.error(`[env] WARN: cannot parse ${USER_CFG_PATH}: ${e.message}`);
}

const exists = (p) => { try { return !!p && fs.existsSync(p); } catch { return false; } };

function whichExe(name) {
  try {
    const out = execFileSync('where', [name], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
    const first = out.split(/\r?\n/).map((s) => s.trim()).filter(Boolean)[0];
    return exists(first) ? first : null;
  } catch { return null; }
}

function firstExisting(cands) {
  for (const c of cands) if (exists(c)) return c;
  return null;
}

// ------------------------------------------------------------------ node.exe
// process.execPath is ALWAYS the node binary currently executing this script,
// so it can never go stale when WorkBuddy upgrades its bundled Node version.
export const NODE = process.execPath;

// -------------------------------------------------------------------- docker
const PF = process.env['ProgramFiles'] || 'C:\\Program Files';
const PF86 = process.env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)';
const LOCALAPPDATA = process.env['LOCALAPPDATA'] || path.join(HOME, 'AppData', 'Local');

export const DOCKER_CLI =
  firstExisting([
    process.env.TREK_DOCKER_CLI,
    userCfg.dockerCli,
    path.join(PF, 'Docker', 'Docker', 'resources', 'bin', 'docker.exe'),
    path.join(PF86, 'Docker', 'Docker', 'resources', 'bin', 'docker.exe'),
    path.join(LOCALAPPDATA, 'Docker', 'Docker', 'resources', 'bin', 'docker.exe'),
  ]) || whichExe('docker') || 'docker';

export const DOCKER_DESKTOP =
  firstExisting([
    process.env.TREK_DOCKER_DESKTOP,
    userCfg.dockerDesktop,
    path.join(PF, 'Docker', 'Docker', 'Docker Desktop.exe'),
    path.join(PF86, 'Docker', 'Docker', 'Docker Desktop.exe'),
    path.join(LOCALAPPDATA, 'Docker', 'Docker', 'Docker Desktop.exe'),
  ]) || null;

// --------------------------------------------------------------- deploy dir
function resolveDeploy() {
  const cands = [
    process.env.TREK_DEPLOY_DIR,
    userCfg.deployDir,
    'D:\\Project\\workspace\\workbuddy\\trek-deploy',
    path.join(HOME, 'trek-deploy'),
    path.resolve(SKILL_DIR, '..', '..', '..', 'trek-deploy'),
  ].filter(Boolean);
  for (const c of cands) {
    if (exists(path.join(c, 'docker-compose.yml'))) return c;
  }
  return null;
}
export const DEPLOY = resolveDeploy();

// ---------------------------------------------------------------- proxy dir
// Prefer the copy BUNDLED INSIDE this skill so the skill is genuinely self-contained
// and edits to scripts/proxy/ take effect directly (no drift with the deploy copy).
// Fall back to the deploy copy (where proxy.log / supervisor.pid have historically
// lived) only if the skill copy is missing.
const SKILL_PROXY_DIR = path.join(SCRIPT_DIR, 'proxy');
function resolveProxyDir() {
  if (exists(path.join(SKILL_PROXY_DIR, 'trek-mcp-proxy.mjs')) && exists(path.join(SKILL_PROXY_DIR, 'supervise.mjs'))) {
    return SKILL_PROXY_DIR;
  }
  const deployProxy = DEPLOY ? path.join(DEPLOY, 'mcp-proxy') : null;
  if (deployProxy && exists(path.join(deployProxy, 'trek-mcp-proxy.mjs')) && exists(path.join(deployProxy, 'supervise.mjs'))) {
    return deployProxy;
  }
  return null;
}
export const PROXY_DIR = resolveProxyDir();
export const SUPERVISE = PROXY_DIR ? path.join(PROXY_DIR, 'supervise.mjs') : null;
export const PIDFILE = PROXY_DIR ? path.join(PROXY_DIR, 'supervisor.pid') : null;
export const PROXY_LOG = PROXY_DIR ? path.join(PROXY_DIR, 'proxy.log') : null;

// ------------------------------------------------------------- proxy config
// Credentials live OUTSIDE the skill by default (never packaged into a shareable zip).
export function resolveProxyConfigPath() {
  return firstExisting([
    process.env.TREK_PROXY_CONFIG,
    userCfg.proxyConfig,
    DEPLOY ? path.join(DEPLOY, 'mcp-proxy', 'proxy-config.json') : null,
    path.join(SKILL_PROXY_DIR, 'proxy-config.json'),
    path.join(HOME, '.workbuddy', 'trek-proxy-config.json'),
  ].filter(Boolean));
}
export const PROXY_CONFIG = resolveProxyConfigPath();

let cfg = {};
if (PROXY_CONFIG) {
  try { cfg = JSON.parse(fs.readFileSync(PROXY_CONFIG, 'utf8')); }
  catch (e) { console.error(`[env] WARN: cannot parse ${PROXY_CONFIG}: ${e.message}`); }
}
export const TREK_BASE = cfg.trekBase || 'http://localhost:3000';
export const PROXY_PORT = Number(cfg.proxyPort || 3001);
export const TREK_PORT = Number(new URL(TREK_BASE).port || 3000);
export const HEALTH_URL = `${TREK_BASE.replace(/\/$/, '')}/api/health`;
export const MCP_URL = `http://127.0.0.1:${PROXY_PORT}/mcp`;
export const HAS_CREDENTIALS = !!(cfg.clientId && cfg.clientSecret);

// ------------------------------------------------------------------ preflight
// Returns { ok, problems: [{level, msg, fix}] } — used by `doctor` and by start/stop
// so a context-free agent gets a precise, actionable failure instead of a stack trace.
export function preflight() {
  const problems = [];
  if (!DEPLOY) {
    problems.push({
      level: 'fatal',
      msg: 'TREK deploy dir not found (no docker-compose.yml in any known location).',
      fix: 'Set TREK_DEPLOY_DIR=<folder with docker-compose.yml>, or add {"deployDir":"..."} to ' + USER_CFG_PATH,
    });
  }
  if (!exists(DOCKER_CLI) && DOCKER_CLI === 'docker') {
    problems.push({
      level: 'fatal',
      msg: 'docker CLI not found.',
      fix: 'Install Docker Desktop, or set TREK_DOCKER_CLI=<path to docker.exe>',
    });
  }
  if (!DOCKER_DESKTOP) {
    problems.push({
      level: 'warn',
      msg: 'Docker Desktop.exe not found — cannot auto-start/auto-quit the daemon.',
      fix: 'Set TREK_DOCKER_DESKTOP=<path>, or start/stop Docker manually.',
    });
  }
  if (!PROXY_DIR) {
    problems.push({
      level: 'fatal',
      msg: 'MCP auth-proxy sources not found (trek-mcp-proxy.mjs / supervise.mjs).',
      fix: 'Expected in <deployDir>\\mcp-proxy or in ' + SKILL_PROXY_DIR,
    });
  }
  if (!PROXY_CONFIG) {
    problems.push({
      level: 'fatal',
      msg: 'proxy-config.json not found (holds the TREK Machine-client OAuth credentials).',
      fix: 'Copy ' + path.join(SKILL_PROXY_DIR, 'proxy-config.example.json') + ' to ' +
           path.join(HOME, '.workbuddy', 'trek-proxy-config.json') +
           ' and fill in clientId/clientSecret from TREK Settings > Integrations > Machine clients.',
    });
  } else if (!HAS_CREDENTIALS) {
    problems.push({
      level: 'fatal',
      msg: `proxy-config.json found (${PROXY_CONFIG}) but clientId/clientSecret are missing.`,
      fix: 'Create a Machine client in TREK (Settings > Integrations) and paste the credentials.',
    });
  }
  return { ok: !problems.some((p) => p.level === 'fatal'), problems };
}

export function describe() {
  return [
    `node          : ${NODE}`,
    `docker cli    : ${DOCKER_CLI}`,
    `docker desktop: ${DOCKER_DESKTOP || '(not found)'}`,
    `deploy dir    : ${DEPLOY || '(not found)'}`,
    `proxy dir     : ${PROXY_DIR || '(not found)'}`,
    `proxy config  : ${PROXY_CONFIG || '(not found)'}${PROXY_CONFIG ? (HAS_CREDENTIALS ? ' [credentials OK]' : ' [NO CREDENTIALS]') : ''}`,
    `trek base     : ${TREK_BASE}  (health: ${HEALTH_URL})`,
    `mcp endpoint  : ${MCP_URL}`,
    `user override : ${exists(USER_CFG_PATH) ? USER_CFG_PATH : '(none)'}`,
  ].join('\n');
}
