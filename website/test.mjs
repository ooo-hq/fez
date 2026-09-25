import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { percent, decimal, milliseconds, validateBenchmark, comparisonHeadline } from './data.js';

const data = JSON.parse(await readFile(new URL('../docs/data/jevbench-public-001.json', import.meta.url)));

test('recorded comparison preserves units, direction, counts, and unavailable values', () => {
  const { fez, kev } = validateBenchmark(data);
  assert.equal(percent(fez.metrics.accuracy), '63.64%');
  assert.equal(milliseconds(fez.metrics.latency.p50_s), '42.08 ms');
  assert.equal(milliseconds(kev.metrics.latency.p95_s), '209.36 ms');
  assert.equal(decimal(fez.metrics.brier_mean), '0.463608');
  assert.equal(comparisonHeadline(fez, kev), 'Accuracy tied; confidence quality regressed.');
  assert.equal(fez.metrics.n_correct, 147);
  assert.equal(fez.metrics.confident_errors, 8);
  assert.equal(kev.metrics.confident_errors, 3);
  assert.equal(percent(data.published_reference.n_correct / data.published_reference.n_attempted), '86.58%');
  assert.equal(percent(0), '0.00%');
  for (const value of [null, undefined, NaN, '', '0.2']) {
    for (const format of [percent, decimal, milliseconds]) assert.equal(format(value), 'Unavailable');
  }
  const missing = structuredClone(fez);
  missing.metrics.brier_mean = null;
  assert.equal(comparisonHeadline(missing, kev), 'Comparison recorded; review the available metrics.');
  for (const invalid of [null, {}, { ...data, models: [] }, { ...data, data_mode: 'live' }]) {
    assert.throws(() => validateBenchmark(invalid), /Invalid recorded benchmark/);
  }
  const inconsistent = structuredClone(data);
  inconsistent.models[0].metrics.n_correct = 999;
  assert.throws(() => validateBenchmark(inconsistent), /Invalid recorded benchmark/);
});
