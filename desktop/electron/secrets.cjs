// F-14: owner secrets are NEVER compiled into the app. The Electron main process reads them at run time
// from the macOS Keychain (service "odin-anchor", one account per name) via `security`. Env vars are the
// fallback for non-mac/dev (ODIN_ANCHOR_KEY, ODIN_MANAGE_EMAIL, ODIN_MANAGE_PASSWORD). Values are never logged.
const { execFile } = require("child_process");

const SERVICE = "odin-anchor";
const NAMES = Object.freeze({                       // allow-list: renderer can only ask for these
  "anchor-key": "ODIN_ANCHOR_KEY",
  "manage-email": "ODIN_MANAGE_EMAIL",
  "manage-password": "ODIN_MANAGE_PASSWORD",
});

function getSecret(name, opts = {}) {
  if (typeof name !== "string" || !Object.prototype.hasOwnProperty.call(NAMES, name)) return Promise.resolve(null);
  const envName = NAMES[name];
  if (!envName) return Promise.resolve(null);                 // unknown name -> nothing
  const env = opts.env || process.env;
  const bin = opts.securityBin || "security";
  return new Promise((resolve) => {
    // argv array, no shell -> no injection; -w prints only the secret
    execFile(bin, ["find-generic-password", "-s", SERVICE, "-a", name, "-w"],
      { timeout: 5000, env }, (err, stdout) => {
        const v = !err && stdout ? String(stdout).replace(/\r?\n$/, "") : "";
        if (v) return resolve(v);
        const e = env[envName];
        resolve(e ? String(e) : null);
      });
  });
}

module.exports = { getSecret, SERVICE, NAMES };
