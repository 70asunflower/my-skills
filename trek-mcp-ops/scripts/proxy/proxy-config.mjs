// Config resolver shared by the bundled proxy + supervisor.
// Credentials are intentionally NOT bundled with the skill. Resolution order:
//   1. $TREK_PROXY_CONFIG
//   2. <this folder>/proxy-config.json
//   3. <TREK_DEPLOY_DIR|default deploy dir>/mcp-proxy/proxy-config.json
//   4. ~/.workbuddy/trek-proxy-config.json
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const HOME = os.homedir();
const exists = (p) => { try { return !!p && fs.existsSync(p); } catch { return false; } };

const deployDir = process.env.TREK_DEPLOY_DIR || 'D:\\Project\\workspace\\workbuddy\\trek-deploy';

export const CONFIG_PATH = [
  process.env.TREK_PROXY_CONFIG,
  path.join(HERE, 'proxy-config.json'),
  path.join(deployDir, 'mcp-proxy', 'proxy-config.json'),
  path.join(HOME, '.workbuddy', 'trek-proxy-config.json'),
].filter(Boolean).find(exists);

if (!CONFIG_PATH) {
  console.error('[proxy] FATAL: proxy-config.json not found. Copy proxy-config.example.json to ' +
    path.join(HOME, '.workbuddy', 'trek-proxy-config.json') + ' and fill in clientId/clientSecret.');
  process.exit(1);
}

export const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
export const TREK_BASE = cfg.trekBase || 'http://localhost:3000';
export const PROXY_PORT = Number(cfg.proxyPort || 3001);
