// --- UI wiring ---
const $q = document.getElementById('q');
const $go = document.getElementById('go');
const $out = document.getElementById('out');

$go.onclick = async () => {
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
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query }),
    });

    const result = await response.json();

    if (response.ok) {
      const mins = result.minutes.toFixed(2);
      $out.textContent =
`EBCT ≈ ${mins} minutes
Calculation based on: ${result.via}

Inputs:
${JSON.stringify(result.detail.inputs, null, 2)}

Formula:
${result.detail.formula}`;
    } else {
      $out.textContent = `Error: ${result.error}\n\n${result.need ? 'Missing information: ' + result.need.join(' · ') : ''}`;
    }
  } catch (err) {
    console.error('Fetch error:', err);
    $out.textContent = 'An unexpected error occurred. Please check the console and make sure the server is running.';
  } finally {
    $go.disabled = false;
  }
};