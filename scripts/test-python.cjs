'use strict';

const path = require('node:path');
const {spawnSync} = require('node:child_process');

const result = spawnSync(process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3'),
  ['-S', '-m', 'unittest', 'discover', '-s',
    path.join(__dirname, '../plugins/novel-txt-reader/skills/novel-txt-reader/tests'),
    '-p', 'test_*.py', '-v'], {stdio: 'inherit',
    env: {...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1'}});
if (result.error) console.error(result.error.message);
process.exitCode = result.status === null ? 1 : result.status;
