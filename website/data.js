const numeric = value => typeof value === 'number' && Number.isFinite(value);
export const decimal = value => numeric(value) ? value.toFixed(6) : 'Unavailable';
export const percent = value => numeric(value) ? `${(value * 100).toFixed(2)}%` : 'Unavailable';
export const milliseconds = value => numeric(value) ? `${(value * 1000).toFixed(2)} ms` : 'Unavailable';

export function validateBenchmark(data) {
  const invalid = () => { throw new Error('Invalid recorded benchmark'); };
  if (data?.schema_version !== 'fez.public-benchmark/v1' || data.data_mode !== 'recorded_experiment'
    || data.status !== 'completed' || !Array.isArray(data.models) || !data.benchmark || !data.runtime) invalid();
  const fez = data.models.find(model => model.id === 'fez');
  const kev = data.models.find(model => model.id === 'kev');
  for (const model of [fez, kev]) {
    if (!model?.metrics || !/^[a-f0-9]{64}$/.test(model.checkpoint_sha256)) invalid();
    const { n_attempted: total, n_correct: correct, accuracy } = model.metrics;
    if (!Number.isInteger(total) || total <= 0 || !Number.isInteger(correct)
      || correct < 0 || correct > total) invalid();
    if (accuracy != null && (!numeric(accuracy) || Math.abs(accuracy - correct / total) > 1e-8)) invalid();
  }
  if (fez.metrics.n_attempted !== kev.metrics.n_attempted) invalid();
  return { fez, kev };
}

export function comparisonHeadline(fez, kev) {
  const a = fez.metrics;
  const b = kev.metrics;
  if ([a.accuracy, b.accuracy, a.brier_mean, b.brier_mean, a.ece, b.ece].every(numeric)
    && a.accuracy === b.accuracy && a.brier_mean > b.brier_mean && a.ece > b.ece) {
    return 'Accuracy tied; confidence quality regressed.';
  }
  return 'Comparison recorded; review the available metrics.';
}
