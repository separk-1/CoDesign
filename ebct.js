document.addEventListener('DOMContentLoaded', () => {
  const $q = document.getElementById('q');
  const $go = document.getElementById('go');
  const $out = document.getElementById('out');

  if (!$q || !$go || !$out) {
    console.error('Missing #q, #go or #out element');
    return;
  }

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
        const mins = String(result.minutes);
        $out.textContent =
`EBCT = ${mins} minutes
Calculation based on: ${result.via}

Inputs (raw parse):
${JSON.stringify(result.detail.inputs, null, 2)}

Normalized units / intermediates:
${JSON.stringify(result.detail.units_normalized || {}, null, 2)}

Constants:
${JSON.stringify(result.detail.constants || {}, null, 2)}

Formula:
${result.detail.formula}

Derivation:
${result.detail.explanation}

Trace:
${JSON.stringify(result.detail.trace || {}, null, 2)}`;
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
