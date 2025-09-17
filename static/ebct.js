document.addEventListener('DOMContentLoaded', () => {
  const $q = document.getElementById('q');
  const $go = document.getElementById('go');
  const $out = document.getElementById('out');

  const esc = (s) =>
    String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

  const fmtNum = (x) => {
    if (typeof x !== 'number') return String(x);
    if (Number.isInteger(x)) return String(x);
    const s = String(x);
    return s.includes('.') ? s.replace(/(\.\d*?[1-9])0+$/,'$1').replace(/\.$/,'') : s;
  };

  const block = (title, body) =>
    `<details><summary>${esc(title)}</summary><pre>${body}</pre></details>`;

  const j = (obj) => esc(JSON.stringify(obj, null, 2));

  if (!$q || !$go || !$out) return;

  $go.addEventListener('click', async (e) => {
    e.preventDefault();

    const query = $q.value;
    if (!query) {
      $out.textContent = 'Please enter a query.';
      return;
    }

    $out.textContent = 'Calculating...';
    $go.disabled = true;

    try {
      const response = await fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const result = await response.json();

      if (response.ok) {
        const mins = Number(result.minutes).toFixed(4);
        const top =
`<div style="font-size:1.1rem;font-weight:600">EBCT = ${esc(mins)} minutes</div>
<div style="margin:2px 0 8px 0;color:#555">Based on: ${esc(result.via || '')}</div>`;

        const inputs = block('Inputs (raw parse)', j(result.detail?.inputs || {}));
        const normalized = block('Normalized units / intermediates', j(result.detail?.units_normalized || {}));
        const constants = block('Constants', j(result.detail?.constants || {}));
        const formula = block('Formula', esc(result.detail?.formula || ''));
        const deriv = block('Derivation', esc(result.detail?.explanation || ''));
        const trace = block('Trace', j(result.detail?.trace || {}));

        $out.innerHTML = top + inputs + normalized + constants + formula + deriv + trace;
      } else {
        $out.textContent = `Error: ${result.error}\n\n${result.need ? 'Missing information: ' + result.need.join(' · ') : ''}`;
      }
    } catch (err) {
      console.error(err);
      $out.textContent = 'Request failed. Open Console for details.';
    } finally {
      $go.disabled = false;
    }
  });
});
