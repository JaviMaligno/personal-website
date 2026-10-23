// Maintainer-only dependency contracts: preload before importing any consumer.
const fs = require('node:fs');
const path = require('node:path');
const { fileURLToPath } = require('node:url');
const { syncBuiltinESMExports } = require('node:module');
for (const key of Object.keys(process.env)) {
  if (!['SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'TEMP', 'TMP'].includes(key.toUpperCase())) delete process.env[key];
}
process.env.NODE_ENV = 'test';
process.env.EXPO_NO_DOTENV = '1';
process.env.EXPO_NO_TELEMETRY = '1';
if (process.platform === 'win32') process.env.USERPROFILE = process.env.TEMP || process.env.TMP;
const counters = { network: 0, processes: 0, envReads: 0 };
globalThis.__offlineDependencyAttempts = counters;
const denyNetwork = () => { counters.network++; throw Error('Offline dependency contract: network/listen forbidden'); };
const denyProcess = () => { counters.processes++; throw Error('Offline dependency contract: subprocess forbidden'); };
globalThis.fetch = denyNetwork;
const net = require('node:net');
net.Socket.prototype.connect = net.Server.prototype.listen = denyNetwork;
net.connect = net.createConnection = denyNetwork;
require('node:tls').connect = denyNetwork;
for (const name of ['node:http', 'node:https']) require(name).request = require(name).get = denyNetwork;
require('node:http2').connect = denyNetwork;
const dgram = require('node:dgram');
dgram.Socket.prototype.connect = dgram.Socket.prototype.send = denyNetwork;
const child = require('node:child_process');
for (const name of ['spawn', 'spawnSync', 'exec', 'execSync', 'execFile', 'execFileSync', 'fork']) child[name] = denyProcess;
function checkFile(value) {
  if (typeof value === 'number') return;
  const filename = value instanceof URL ? fileURLToPath(value) : Buffer.isBuffer(value) ? value.toString() : String(value);
  if (/^\.env(?:\.|$)/i.test(path.basename(filename))) {
    counters.envReads++;
    throw Error('Offline dependency contract: env-file read forbidden');
  }
}
for (const name of ['readFile', 'readFileSync', 'open', 'openSync']) {
  const original = fs[name];
  fs[name] = function (filename, ...args) { checkFile(filename); return original.call(this, filename, ...args); };
}
for (const name of ['readFile', 'open']) {
  const original = fs.promises[name];
  fs.promises[name] = function (filename, ...args) { checkFile(filename); return original.call(this, filename, ...args); };
}
syncBuiltinESMExports();
