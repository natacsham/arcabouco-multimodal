// Presentation QA only. The comparison never updates a fixture or the engine.
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';

export const EDITORIAL_BASELINE = '9445c51';
const sha = data => crypto.createHash('sha256').update(data).digest('hex');
const git = (root, args) => execFileSync('git', args, {cwd: root, maxBuffer: 64 * 1024 * 1024});

export async function coreInvariantAudit(root) {
  const files = git(root, ['ls-tree', '-r', '--name-only', EDITORIAL_BASELINE, '--',
    'ontology', 'data', 'shapes', 'queries', 'engine.py', 'web/amado/engine.py',
    'web/amado/bridge.py', 'web/amado/assets/base.zip', 'web/amado/app.js',
    'web/amado/guided.js', 'web/amado/client.mjs', 'web/amado/worker.mjs'])
    .toString('utf8').trim().split(/\r?\n/).filter(Boolean);
  assert(files.length >= 21, 'Expected the complete semantic and runtime invariant set.');
  const rows = [];
  for (const file of files) {
    const baseline = sha(git(root, ['show', `${EDITORIAL_BASELINE}:${file}`]));
    const current = sha(await fs.readFile(path.join(root, file)));
    rows.push({file, baseline_sha256: baseline, current_sha256: current, unchanged: baseline === current});
  }
  assert(rows.every(row => row.unchanged), 'Unexpected change to preserved ontology, data or runtime files: ' + rows.filter(row => !row.unchanged).map(row => row.file).join(', '));
  return {baseline_commit: EDITORIAL_BASELINE, count: rows.length, all_unchanged: true, files: rows};
}

export function historicalReport(root, file, reference = EDITORIAL_BASELINE) {
  const raw = git(root, ['show', `${reference}:${file}`]);
  const data = JSON.parse(raw.toString('utf8'));
  assert.equal(data.completed, true, 'The historical report must be a completed execution.');
  return {git_reference: `${reference}:${file}`, sha256: sha(raw),
    completed: data.completed, prior_checks_passed: Object.values(data.checks || {}).filter(value => value === true).length,
    prior_scope: data.scope || data.change_verification?.scope || null,
    comparison: data.comparison || null,
    warning: 'Historical evidence; its checks are not counted as executed by the current run.'};
}

export async function typographySnapshot(page) {
  return page.evaluate(() => {
    const visible = el => el.checkVisibility() && el.getBoundingClientRect().width > 0 && el.getBoundingClientRect().height > 0;
    const describe = el => ({text: el.textContent.replace(/\s+/g, ' ').trim().slice(0, 85),
      pixels: parseFloat(getComputedStyle(el).fontSize), line_height: getComputedStyle(el).lineHeight});
    const headings = Object.fromEntries(['h1','h2','h3'].map(tag => [tag, [...document.querySelectorAll('main '+tag)].filter(visible).map(describe)]));
    const functional = [];
    const selectors = ['main label', 'main legend', 'main button', 'main summary', 'main textarea', 'main select',
      'main .field-help', 'main .resource-state', 'main .mode-pill', 'main .guide-config-purpose',
      'main .guide-config-availability', 'main .guide-config-title', 'main .confirmation',
      'main .guide-result-help', 'main .limit',
      '#health', '#expected-result', '#expected-result-note', '#practical-headline'];
    for (const selector of selectors) [...document.querySelectorAll(selector)].forEach((el, index) => {
      if (visible(el)) functional.push({key: `${selector}:${index}`, ...describe(el)});
    });
    return {viewport: {width: innerWidth, height: innerHeight},
      root: parseFloat(getComputedStyle(document.documentElement).fontSize),
      body: parseFloat(getComputedStyle(document.body).fontSize), headings, functional};
  });
}

export function assertAmadoTypography(snapshot, mobile = false) {
  assert.equal(snapshot.root, 16, 'AMADO root at 100% must be 16px.');
  assert.equal(snapshot.body, 16, 'AMADO body at 100% must be 16px.');
  assert(snapshot.headings.h1.length > 0, 'A visible H1 is required.');
  for (const [tag, expected] of Object.entries({h1: mobile ? 28 : 32, h2: 24, h3: 18})) {
    for (const row of snapshot.headings[tag]) assert(Math.abs(row.pixels - expected) < .1,
      `${tag} must be ${expected}px: ${row.text} (${row.pixels}px)`);
  }
  assert(snapshot.functional.length > 0, 'Functional labels must be sampled.');
  const small = snapshot.functional.filter(row => row.pixels < 15.9);
  assert.equal(small.length, 0, 'Functional text below 16px: ' + small.map(row => `${row.key} ${row.pixels}px`).join(', '));
}

export function assertFixedViewportDoubling(before, after) {
  assert.deepEqual(after.viewport, before.viewport, 'Text enlargement must be measured at the same viewport.');
  const ratios = [];
  const add = (key, oldSize, newSize) => {
    const ratio = newSize / oldSize; ratios.push({key, before: oldSize, after: newSize, ratio});
    assert(Math.abs(ratio - 2) < .03, `${key} did not double at 200% (${oldSize} → ${newSize}).`);
  };
  add('root', before.root, after.root); add('body', before.body, after.body);
  for (const tag of ['h1','h2','h3']) before.headings[tag].forEach((row, index) => {
    const current = after.headings[tag].find(item => item.text === row.text) || after.headings[tag][index];
    assert(current, `Visible heading disappeared when enlarged: ${row.text}`);
    add(`${tag}:${index}`, row.pixels, current.pixels);
  });
  for (const row of before.functional) {
    const current = after.functional.find(item => item.key === row.key);
    assert(current, `Functional content disappeared when enlarged: ${row.key}`);
    add(row.key, row.pixels, current.pixels);
  }
  return ratios;
}
