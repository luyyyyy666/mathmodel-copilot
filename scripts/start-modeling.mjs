#!/usr/bin/env node
// Launch the registered source-built Codex in an initialized modeling workspace.
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { access, readFile, realpath } from 'node:fs/promises';
import { constants } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';
import { parseArgs } from 'node:util';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

async function main() {
  const { values } = parseArgs({
    options: {
      project: { type: 'string' },
      registration: { type: 'string', default: path.join(root, '.runtime/runtime.json') },
      check: { type: 'boolean', default: false },
      help: { type: 'boolean', default: false },
    },
  });
  if (values.help) {
    console.log('node scripts/start-modeling.mjs --project /absolute/modeling-project [--registration runtime.json] [--check]');
    return;
  }
  if (!values.project) throw new Error('--project is required');
  const project = await realpath(values.project);
  const state = JSON.parse(await readFile(path.join(project, '.workflow/state.json'), 'utf8'));
  if (state.format !== 1) throw new Error('Unsupported or uninitialized workflow workspace');
  await access(path.join(project, '.agents/skills/mathmodel-workflow/SKILL.md'));
  await access(path.join(project, 'AGENTS.md'));
  const registration = JSON.parse(await readFile(values.registration, 'utf8'));
  if (registration.kind !== 'source-build' || typeof registration.binary !== 'string'
      || !path.isAbsolute(registration.binary) || !/^[a-f0-9]{64}$/.test(registration.sha256)) {
    throw new Error('Expected a valid source-build registration with absolute binary path and SHA-256');
  }
  await access(registration.binary, constants.X_OK);
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(registration.binary)) hash.update(chunk);
  if (hash.digest('hex') !== registration.sha256) throw new Error('Registered runtime binary SHA-256 mismatch');
  const prompt = '读取 AGENTS.md 和 .agents/skills/mathmodel-workflow/SKILL.md。' +
    '先用工作流脚本 status、next 检查已有进度，然后完成当前建模任务的剩余链路。' +
    '实际运行计算与验证，保留来源和复现证据；遇到工具或输入阻塞明确报告。' +
    '按已有授权继续，不把本地阶段登记当作人工验收。不要重新初始化项目或覆盖旧结果。';
  const args = ['-C', project, '-s', 'workspace-write', '-a', 'on-request', prompt];
  if (values.check) {
    console.log(JSON.stringify({ binary: registration.binary, project, args, sha256_verified: true,
      model_called: false, authentication_checked: false }, null, 2));
    return;
  }
  const child = spawn(registration.binary, args, { cwd: project, stdio: 'inherit' });
  const code = await new Promise((resolve, reject) => {
    child.on('error', reject);
    child.on('exit', (exitCode, signal) => resolve(exitCode ?? (signal ? 1 : 0)));
  });
  process.exitCode = code;
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
