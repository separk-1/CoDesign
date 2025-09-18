// static/ebct.js (v14): persona + text-first
document.addEventListener('DOMContentLoaded', () => {
  const $chat = document.getElementById('chat');
  const $q    = document.getElementById('q');
  const $send = document.getElementById('send');
  const $roleHint = document.getElementById('roleHint');
  const $roleBtns = document.querySelectorAll('.rolebtn');

  let state = { role: null, used: null };
  let messages = [];

  const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const bubble = (role, html) => { const b=document.createElement('div'); b.className=`bubble ${role==='user'?'user':'bot'}`; b.innerHTML=html; $chat.appendChild(b); $chat.scrollTop=$chat.scrollHeight; return b; };

  // role select
  $roleBtns.forEach(btn=>{
    btn.addEventListener('click', ()=>{
      state.role = btn.dataset.role; // 'designer' | 'engineer'
      $roleHint.textContent = state.role === 'designer' ? 'Designer mode – plain language, alternatives first.' : 'Engineer mode – numbers, units, assumptions.';
      bubble('bot', state.role==='designer' ? '디자이너 모드로 도와드릴게요. 무엇이 걱정되세요?' : '엔지니어 모드입니다. 기준/가정부터 알려주세요.');
      $q.focus();
    });
  });

  async function send() {
    const text = ($q.value || '').trim();
    if (!text) return;
    if (!state.role) { bubble('bot','먼저 상단에서 역할을 선택해 주세요 (Designer / Engineer).'); return; }

    $q.value = '';
    messages.push({ role: 'user', content: text });
    bubble('user', esc(text));

    try {
      const res = await fetch('/api/chat', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ messages, state })
      });
      const raw = await res.text();
      let data; try { data = JSON.parse(raw); } catch { data = { reply: raw }; }

      if (!res.ok) { bubble('bot', `Error: ${esc(data.error || 'Server error')}`); return; }

      const reply = data.reply || '(no reply)';
      bubble('bot', esc(reply));
      if (data.rationale) bubble('bot', `<span class="muted">${esc(data.rationale)}</span>`);

      if (data.calc && data.calc.used) state.used = data.calc.used;
      messages.push({ role: 'assistant', content: reply });
    } catch (e) {
      console.error(e); bubble('bot', 'Request failed. See Console.');
    }
  }

  $send.addEventListener('click', send);
  $q.addEventListener('keydown', (e)=>{ if(e.key==='Enter') send(); });

  bubble('bot', "나는 디자이너/엔지니어 중 무엇인가요? 상단에서 선택해 주세요.\n기준 예) 'flow 800 gpm, bed volume 9600 gal'\n질문 예) '이거 10% 올려도 돼?', 'what flow for 15 min'");
});
