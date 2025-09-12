R// --- constants & helpers ---
const GAL_PER_FT3 = 7.48052;
const GAL_PER_M3  = 264.172;
const FT_PER_M    = 3.28084;
const PI = Math.PI;

function matchNumUnit(re, s) {
  return [...s.matchAll(re)].map(m => ({ v: +m[1], u: m[3].toLowerCase(), i: m.index }));
}

function toGPM(flow) {
  if (!flow) return null;
  const { v, u } = flow;
  if (u === 'gpm') return v;
  if (u === 'l/min' || u === 'lpm') return v / 3.78541;
  if (u === 'm3/h' || u === 'm³/h') return (v * GAL_PER_M3) / 60;
  return null;
}

function galFrom(vol) {
  if (!vol) return null;
  const { v, u } = vol;
  if (u === 'gal') return v;
  if (u === 'ft3' || u === 'ft³') return v * GAL_PER_FT3;
  if (u === 'm3'  || u === 'm³')  return v * GAL_PER_M3;
  return null;
}

function feet(v, u) {
  if (u === 'ft') return v;
  if (u === 'in') return v / 12;
  if (u === 'm')  return v * FT_PER_M;
  return v;
}

// --- parsing ---
function parseMsg(msgRaw) {
  const msg = msgRaw.toLowerCase();

  // flow: gpm, l/min(lpm), m3/h
  const flow = matchNumUnit(/(\d+(\.\d+)?)\s*(gpm|l\/min|lpm|m3\/h|m³\/h)/g, msg)[0];

  // volume: gal, ft3/ft³, m3/m³
  const vol  = matchNumUnit(/(\d+(\.\d+)?)\s*(gal|ft3|ft³|m3|m³)/g, msg)[0];

  // dimensions: ft, m, in (우선 두 개를 D,H로 해석)
  const dims = matchNumUnit(/(\d+(\.\d+)?)\s*(ft|m|in)/g, msg);

  const hints = {
    hasEBCT: /ebct|empty bed|contact time|접촉|베드/.test(msg),
    hasDia:  /dia|diameter|지름|d\b/.test(msg),
    hasHt:   /height|bed|베드|h\b/.test(msg),
  };

  return { flow, vol, dims, hints, raw: msgRaw };
}

// --- compute ---
function computeEBCT(inputText) {
  const { flow, vol, dims } = parseMsg(inputText);

  const gpm = toGPM(flow);

  // path 1) volume + flow
  if (vol && gpm) {
    const gal = galFrom(vol);
    const minutes = gal / gpm;
    return {
      ok: true,
      via: 'volume+flow',
      minutes,
      detail: {
        inputs: { flow, volume: vol },
        formula: 'EBCT(min) = Volume(gal) / Flow(gal/min)'
      }
    };
  }

  // path 2) dimensions + flow (assume cylinder)
  if (dims.length >= 2 && gpm) {
    const D = feet(dims[0].v, dims[0].u);
    const H = feet(dims[1].v, dims[1].u);
    const ft3 = PI * (D / 2) ** 2 * H;
    const gal = ft3 * GAL_PER_FT3;
    const minutes = gal / gpm;
    return {
      ok: true,
      via: 'dims+flow (assume cylinder)',
      minutes,
      detail: {
        inputs: { flow, D_ft: D, H_ft: H },
        formula: 'V(ft³)=π*(D/2)²*H; EBCT(min)=V(gal)/Flow(gpm); 1 ft³=7.48052 gal'
      }
    };
  }

  // need more info
  const need = [];
  if (!flow) need.push('유량 (예: 800 gpm / 3.5 m3/h / 120 L/min)');
  if (!vol && dims.length < 2) need.push('베드부피(예: 9600 gal) 또는 탱크 치수(지름·베드높이)');
  return { ok: false, need };
}

// --- UI wiring ---
const $q = document.getElementById('q');
const $go = document.getElementById('go');
const $out = document.getElementById('out');

$go.onclick = () => {
  const r = computeEBCT($q.value);
  if (r.ok) {
    const mins = r.minutes.toFixed(2);
    $out.textContent =
`EBCT ≈ ${mins} minutes
via: ${r.via}

inputs:
${JSON.stringify(r.detail.inputs, null, 2)}

formula:
${r.detail.formula}`;
  } else {
    $out.textContent = `부족한 값: ${r.need.join(' · ')}`;
  }
};