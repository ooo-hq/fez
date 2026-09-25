import { percent, decimal, milliseconds, validateBenchmark, comparisonHeadline } from './data.js';

const benchmark = document.querySelector('#benchmark');
const candidate = document.querySelector('#candidate-hash');
const escape = value => String(value ?? 'Unavailable').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const count = value => Number.isInteger(value) && value >= 0 ? String(value) : 'Unavailable';
const githubURL = value => {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.hostname === 'github.com' ? escape(url.href) : null;
  } catch { return null; }
};
const sourceLink = (url, label) => githubURL(url) ? `<a href="${githubURL(url)}">${label} <span aria-hidden="true">↗</span></a>` : '<span>Source unavailable</span>';
const timestamp = value => {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Unavailable';
  return `${new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'UTC', hourCycle: 'h23' }).format(new Date(value))} UTC`;
};

function renderBenchmark(data, fez, kev) {
  const f = fez.metrics;
  const k = kev.metrics;
  const rows = [
    ['Accuracy', 'higher is better', percent(k.accuracy), percent(f.accuracy)],
    ['Correct answers', '', `${count(k.n_correct)} / ${count(k.n_attempted)}`, `${count(f.n_correct)} / ${count(f.n_attempted)}`],
    ['Brier loss', 'lower is better', decimal(k.brier_mean), decimal(f.brier_mean), f.brier_mean != null && k.brier_mean != null && f.brier_mean > k.brier_mean],
    ['Calibration error (ECE)', 'lower is better', decimal(k.ece), decimal(f.ece), f.ece != null && k.ece != null && f.ece > k.ece],
    ['Confident mistakes', 'wrong at ≥90% confidence', count(k.confident_errors), count(f.confident_errors), f.confident_errors != null && k.confident_errors != null && f.confident_errors > k.confident_errors],
    ['Median latency', 'localhost HTTP', milliseconds(k.latency?.p50_s), milliseconds(f.latency?.p50_s)],
    ['p95 latency', 'localhost HTTP', milliseconds(k.latency?.p95_s), milliseconds(f.latency?.p95_s)],
    ['Valid probability outputs', '', percent(k.schema_validity), percent(f.schema_validity)],
  ];
  const slices = ['easy', 'original', 'hard'].map(name => {
    const a = fez.slices?.[name];
    const b = kev.slices?.[name];
    return `<tr><th scope="row">${name[0].toUpperCase() + name.slice(1)}</th><td>${count(b?.n_correct)} / ${count(b?.n_scorable)}<span class="table-sub">${percent(b?.accuracy)}</span></td><td>${count(a?.n_correct)} / ${count(a?.n_scorable)}<span class="table-sub">${percent(a?.accuracy)}</span></td></tr>`;
  }).join('');
  const reference = data.published_reference;
  const referenceAccuracy = reference?.n_attempted > 0 && Number.isInteger(reference?.n_correct)
    ? reference.n_correct / reference.n_attempted : null;
  return `
    <div class="result-banner"><span class="result-mark" aria-hidden="true">=</span><div><h3>${escape(comparisonHeadline(fez, kev))}</h3><p>Fez corrected ${count(data.paired_outcomes?.fez_corrected)} Kev errors and introduced ${count(data.paired_outcomes?.fez_regressed)}. No general improvement is established.</p></div></div>
    <dl class="metrics">
      <div class="metric"><dt>Fez accuracy</dt><dd>${percent(f.accuracy)}</dd><p>${count(f.n_correct)} of ${count(f.n_attempted)} public items correct</p></div>
      <div class="metric"><dt>Fez Brier loss</dt><dd class="long-number">${decimal(f.brier_mean)}</dd><p>Kev: ${decimal(k.brier_mean)}. Lower is better.</p></div>
      <div class="metric"><dt>Fez confident mistakes</dt><dd>${count(f.confident_errors)}</dd><p>${count(k.confident_errors)} for Kev. Wrong at ≥90% confidence.</p></div>
    </dl>
    <div class="comparison-panel">
      <div class="panel-heading"><div><h3>${escape(data.benchmark.name)} public comparison</h3><p>${escape(data.benchmark.subset)}</p></div><a href="./data/jevbench-public-001.json">Source JSON <span aria-hidden="true">↗</span></a></div>
      <div class="table-scroll" role="region" aria-label="Overall model comparison" tabindex="0"><table><caption>Recorded Fez and published Kev comparison on the same public items</caption><thead><tr><th scope="col">Metric</th><th scope="col">Published Kev 0.8B<span class="table-sub">Reference checkpoint</span></th><th scope="col" class="candidate-col">Fez candidate<span class="table-sub">Experimental checkpoint</span></th></tr></thead><tbody>
        ${rows.map(([label, hint, baseline, current, worse]) => `<tr><th scope="row">${label}${hint ? `<span class="metric-direction">${hint}</span>` : ''}</th><td>${baseline}</td><td${worse ? ' class="regression"' : ''}>${current}</td></tr>`).join('')}
      </tbody></table></div>
      <p class="table-note">Brier loss measures probability error; ECE measures the gap between confidence and observed accuracy. Lower is better for both. Timing: ${escape(data.runtime.measurement)} on ${escape(data.runtime.hardware)}, via localhost HTTP. This does not establish a reliable speedup or production SLA.</p>
    </div>
    <div class="quality-bottom">
      <div class="comparison-panel"><div class="panel-heading"><div><h3>Accuracy by difficulty</h3><p>Correct / total items, with accuracy below</p></div></div><div class="table-scroll" role="region" aria-label="Accuracy by difficulty" tabindex="0"><table class="slice-table"><caption>Easy, original, and hard public item results</caption><thead><tr><th scope="col">Subset</th><th scope="col">Kev</th><th scope="col" class="candidate-col">Fez</th></tr></thead><tbody>${slices}</tbody></table></div></div>
      <aside class="reference-panel" aria-label="Published external reference"><div class="reference-label">Published reference <span aria-hidden="true">↗</span></div><h3>${escape(reference?.name)}</h3><div class="reference-score">${percent(referenceAccuracy)}<span>${count(reference?.n_correct)} / ${count(reference?.n_attempted)} correct</span></div><p>${escape(reference?.scope)} Not run on our hardware.</p>${sourceLink(reference?.source_url, 'View upstream outcomes')}</aside>
    </div>
    <dl class="provenance">
      <div><dt>Data mode</dt><dd>${escape(data.data_mode)}</dd><dd>Completed, recorded experiment</dd></div>
      <div><dt>Verified at</dt><dd><time datetime="${escape(data.verified_at)}">${timestamp(data.verified_at)}</time></dd><dd>Evidence time; not page-refresh time</dd></div>
      <div><dt>Hardware / precision</dt><dd>${escape(data.runtime.hardware)}</dd><dd>${escape(data.runtime.precision?.toUpperCase())}. Same runtime for both models.</dd></div>
    </dl>
    <details class="evidence"><summary>Method, checkpoint identities & limitations</summary><div class="evidence-body">
      <p>No official JevBench rank or composite score is available: private and sealed tests were not run. Hosted cost was not measured. Other experiment suites are documented separately and cannot form an improvement line with this comparison.</p>
      <dl><div><dt>Experiment / collection started</dt><dd>${escape(data.id)} / ${timestamp(data.started_at)}</dd></div><div><dt>Fez checkpoint SHA-256</dt><dd><code>${escape(fez.checkpoint_sha256)}</code></dd></div><div><dt>Published Kev checkpoint SHA-256</dt><dd><code>${escape(kev.checkpoint_sha256)}</code></dd></div><div><dt>Public dataset SHA-256</dt><dd><code>${escape(data.benchmark.dataset_sha256)}</code></dd></div><div><dt>Harness revision</dt><dd><code>${escape(data.benchmark.harness_commit)}</code></dd></div><div><dt>Latency scope</dt><dd>${escape(data.runtime.latency_scope)}.</dd></div><div><dt>Saved temperatures</dt><dd>Fez: ${decimal(fez.temperature)}. Kev: ${decimal(kev.temperature)}.</dd></div></dl>
      <ul>${(Array.isArray(data.limitations) ? data.limitations : ['Limitations unavailable; consult the methodology.']).map(item => `<li>${escape(item)}</li>`).join('')}</ul>
      <div class="evidence-links"><a href="https://github.com/ooo-hq/fez/blob/main/docs/jevbench-public.md">Full methodology</a>${sourceLink(data.benchmark.upstream_url, 'Pinned benchmark harness')}<a href="https://github.com/ooo-hq/fez/blob/main/docs/experiments.md">Other experiment suites</a></div>
    </div></details>`;
}

async function loadBenchmark(restoreFocus = false) {
  benchmark.setAttribute('aria-busy', 'true');
  benchmark.innerHTML = '<div class="load-state" role="status"><span class="loading-symbol" aria-hidden="true">◌</span><h3>Loading the recorded benchmark</h3><p>Reading the public experiment file.</p></div>';
  try {
    const response = await fetch('./data/jevbench-public-001.json', { signal: AbortSignal.timeout(10000) });
    if (!response.ok) throw new Error('Benchmark request failed');
    const data = await response.json();
    const { fez, kev } = validateBenchmark(data);
    benchmark.innerHTML = renderBenchmark(data, fez, kev);
    candidate.textContent = `${fez.checkpoint_sha256.slice(0, 16)}…${fez.checkpoint_sha256.slice(-8)}`;
    candidate.title = fez.checkpoint_sha256;
    if (restoreFocus) {
      const heading = document.querySelector('#quality-title');
      heading.setAttribute('tabindex', '-1');
      heading.focus({ preventScroll: true });
    }
  } catch {
    candidate.textContent = 'Unavailable';
    candidate.removeAttribute('title');
    benchmark.innerHTML = '<div class="load-state"><span class="loading-symbol" aria-hidden="true">!</span><h3 role="alert">Benchmark unavailable</h3><p>The recorded data could not be loaded or validated. Retry the request, or read the documented results.</p><button class="button primary" type="button" id="retry-benchmark">Retry loading</button><a href="https://github.com/ooo-hq/fez/blob/main/docs/jevbench-public.md">Read methodology and results</a></div>';
    if (restoreFocus) document.querySelector('#retry-benchmark').focus({ preventScroll: true });
  } finally {
    benchmark.setAttribute('aria-busy', 'false');
  }
}

benchmark.addEventListener('click', event => {
  if (event.target.closest('#retry-benchmark')) loadBenchmark(true);
});

const navLinks = [...document.querySelectorAll('nav a')];
const observer = new IntersectionObserver(entries => {
  for (const entry of entries) {
    if (!entry.isIntersecting) continue;
    for (const link of navLinks) {
      if (link.hash === `#${entry.target.id}`) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
  }
}, { rootMargin: '0px 0px -65% 0px' });
document.querySelectorAll('main > section').forEach(section => observer.observe(section));
loadBenchmark();
