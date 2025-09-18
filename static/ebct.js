// static/ebct.js (v17): persona + text-first + kg + markdown + loading (no bubble)
document.addEventListener('DOMContentLoaded', () => {
  const $chat = document.getElementById('chat');
  const $q    = document.getElementById('q');
  const $send = document.getElementById('send');
  const $roleHint = document.getElementById('roleHint');
  const $roleBtns = document.querySelectorAll('.rolebtn');
  const $dbBtn = document.getElementById('db-btn');
  const $graphContainer = document.getElementById('graph-container');

  let state = { role: null, used: null };
  let messages = [];
  
  const converter = new showdown.Converter();

  const esc = (s) => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  
  const bubble = (role, text) => { 
    const b = document.createElement('div'); 
    b.className = `bubble ${role === 'user' ? 'user' : 'bot'}`; 
    b.innerHTML = converter.makeHtml(text);
    $chat.appendChild(b); 
    $chat.scrollTop = $chat.scrollHeight; 
    return b; 
  };
  
  const plainText = (text, className) => {
    const p = document.createElement('div');
    p.className = className;
    p.textContent = text;
    $chat.appendChild(p);
    $chat.scrollTop = $chat.scrollHeight;
    return p;
  };

  $roleBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const role = btn.dataset.role;
      if (!role) return; // Should not happen for role buttons
      state.role = role;
      $roleHint.textContent = state.role === 'designer' ? 'Designer mode – plain language, alternatives first.' : 'Engineer mode – numbers, units, assumptions.';

      // Update button styles
      $roleBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      bubble('bot', state.role === 'designer' ? 'Designer mode activated. How can I help you today?' : 'Engineer mode activated. Please provide the baseline parameters.');
      $q.focus();
    });
  });

  let graphVisible = false;
  $dbBtn.addEventListener('click', async () => {
    graphVisible = !graphVisible;
    $dbBtn.setAttribute('aria-pressed', graphVisible);
    $dbBtn.classList.toggle('active', graphVisible);
    
    $chat.style.display = graphVisible ? 'none' : 'flex';
    $graphContainer.style.display = graphVisible ? 'block' : 'none';

    if (graphVisible) {
      $q.placeholder = 'Drag the graph to explore.';
      renderGraph();
    } else {
      $q.placeholder = 'Ask a question…';
    }
  });

  async function send() {
    const text = ($q.value || '').trim();
    if (!text) return;
    if (!state.role) { 
        bubble('bot', 'Please select your role (Designer / Engineer) first.');
        return; 
    }

    $q.value = '';
    messages.push({ role: 'user', content: text });
    bubble('user', esc(text));

    const loadingText = plainText('Generating response...', 'loading-text');

    try {
      const res = await fetch('/api/chat', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ messages, state })
      });
      const raw = await res.text();
      let data; 
      try { data = JSON.parse(raw); } catch { data = { reply: raw }; }

      loadingText.classList.add('fade-out');
      loadingText.addEventListener('transitionend', () => {
        loadingText.remove();
      });

      if (!res.ok) { 
        bubble('bot', `Error: ${esc(data.error || 'Server error')}`); 
        return; 
      }

      const reply = data.reply || '(no reply)';
      bubble('bot', reply);
      if (data.rationale) {
          const rationaleHtml = converter.makeHtml(data.rationale);
          const rationaleBubble = document.createElement('div');
          rationaleBubble.className = 'bubble bot';
          rationaleBubble.innerHTML = `<span class="muted">${rationaleHtml}</span>`;
          $chat.appendChild(rationaleBubble);
          $chat.scrollTop = $chat.scrollHeight;
      }

      if (data.calc && data.calc.used) state.used = data.calc.used;
      messages.push({ role: 'assistant', content: reply });
    } catch (e) {
      loadingText.classList.add('fade-out');
      loadingText.addEventListener('transitionend', () => {
        loadingText.remove();
      });
      console.error(e); 
      bubble('bot', 'Request failed. See Console.');
    }
  }

  $send.addEventListener('click', send);
  $q.addEventListener('keydown', (e)=>{ if(e.key==='Enter') send(); });

  async function renderGraph() {
    try {
      const res = await fetch('/api/knowledge-graph');
      if (!res.ok) throw new Error('Failed to fetch knowledge graph');
      const graphData = await res.json();
      
      const width = $graphContainer.offsetWidth;
      const height = $graphContainer.offsetHeight || 600;
      const svg = d3.select("#knowledge-graph").html("").attr("width", width).attr("height", height);

      const simulation = d3.forceSimulation(graphData.nodes)
        .force("link", d3.forceLink(graphData.links).id(d => d.id).distance(100))
        .force("charge", d3.forceManyBody().strength(-300))
        .force("center", d3.forceCenter(width / 2, height / 2));

      const link = svg.append("g")
        .attr("stroke", "#999")
        .attr("stroke-opacity", 0.6)
        .selectAll("line")
        .data(graphData.links)
        .join("line");

      const node = svg.append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 1.5)
        .selectAll("circle")
        .data(graphData.nodes)
        .join("circle")
        .attr("r", 8)
        .attr("fill", d => {
          if (d.type === 'concept') return '#2563eb';
          if (d.type === 'risk') return '#dc2626';
          if (d.type === 'advice') return '#facc15';
          return '#64748b';
        })
        .style("cursor", "pointer")
        .call(d3.drag()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended));

      const text = svg.append("g")
        .selectAll("text")
        .data(graphData.nodes)
        .join("text")
        .attr("x", 12)
        .attr("y", "0.31em")
        .style("font-size", "14px")
        .style("fill", "#333")
        .text(d => d.id)
        .clone(true).lower()
        .attr("stroke-linejoin", "round")
        .attr("stroke-width", 3)
        .attr("stroke", "white");

      simulation.on("tick", () => {
        link
          .attr("x1", d => d.source.x)
          .attr("y1", d => d.source.y)
          .attr("x2", d => d.target.x)
          .attr("y2", d => d.target.y);
        node
          .attr("cx", d => d.x)
          .attr("cy", d => d.y);
        text
          .attr("x", d => d.x + 12)
          .attr("y", d => d.y);
      });

      function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      }

      function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
      }

      function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      }

    } catch (e) {
      console.error(e);
      const svg = d3.select("#knowledge-graph");
      const width = $graphContainer.offsetWidth;
      const height = $graphContainer.offsetHeight || 600;
      svg.html("").attr("width", width).attr("height", height);
      svg.append("text")
         .attr("x", width / 2)
         .attr("y", height / 2)
         .attr("text-anchor", "middle")
         .attr("font-size", "16px")
         .attr("fill", "#dc2626")
         .text("Failed to load knowledge graph.");
    }
  }

  bubble('bot', "나는 디자이너/엔지니어 중 무엇인가요? 상단에서 선택해 주세요.\n기준 예) 'flow 800 gpm, bed volume 9600 gal'\n질문 예) '이거 10% 올려도 돼?', 'what flow for 15 min'");
});