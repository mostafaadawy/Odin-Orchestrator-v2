const { execSync } = require('child_process');
const path = require('path');
exports.default = async function (context) {
  const app = path.join(context.appOutDir, `${context.packager.appInfo.productFilename}.app`);
  console.log('[afterPack] ad-hoc signing', app);
  try { execSync(`xattr -cr "${app}"`, { stdio: 'inherit' }); } catch (e) {}
  execSync(`codesign --force --deep --sign - "${app}"`, { stdio: 'inherit' });
  execSync(`codesign --verify --deep --strict "${app}"`, { stdio: 'inherit' });
  console.log('[afterPack] signed + verified OK');
};
