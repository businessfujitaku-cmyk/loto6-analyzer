/* LOTO6 Simulator - app.js */

const API = '';

async function fetchJSON(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// --- Status ---
async function loadStatus() {
  try {
    const data = await fetchJSON('/api/status');
    const badge = document.getElementById('statusBadge');
    if (data.last_fetch_ok) {
      const dt = data.last_fetch_at ? data.last_fetch_at.replace('T', ' ') : '';
      badge.innerHTML = `&#10003; 自動取得済 ${data.rows}件 | ${dt}`;
      badge.className = 'text-xs px-3 py-1.5 rounded-full bg-emerald-900/40 border border-emerald-700/50 text-emerald-400';
    } else if (data.rows > 0) {
      badge.innerHTML = `&#9888; ${data.rows}件読込済`;
      badge.className = 'text-xs px-3 py-1.5 rounded-full bg-yellow-900/40 border border-yellow-700/50 text-yellow-400';
    }
    document.getElementById('totalRows').textContent = data.rows ? data.rows.toLocaleString() + '件' : '---';
    document.getElementById('latestRound').textContent = data.latest_round ? '第' + data.latest_round + '回' : '---';
    document.getElementById('lastFetch').textContent = data.last_fetch_at ? data.last_fetch_at.replace('T', ' ') : '---';
  } catch (e) {
    console.error('status error:', e);
  }
}

// --- Latest draw ---
async function loadLatest() {
  try {
    const data = await fetchJSON('/api/latest');
    if (data.numbers) {
      document.getElementById('latestNumbers').textContent = data.numbers.join(' - ');
    }
  } catch (e) {
    console.error('latest error:', e);
  }
}

// --- Predictions ---
async function loadPredictions() {
  const grid = document.getElementById('ticketsGrid');
  grid.innerHTML = Array(5).fill('<div class="skeleton-card"></div>').join('');
  try {
    const data = await fetchJSON('/api/predictions');
    if (!data.ready || !data.tickets || data.tickets.length === 0) {
      grid.innerHTML = '<div class="syncing-placeholder col-span-full"><span class="spin">&#8635;</span> データ同期中です。しばらくお待ちください...</div>';
      return;
    }
    grid.innerHTML = data.tickets.map((t, i) => {
      const balls = t.numbers.map((n, j) =>
        `<span class="ball" style="animation-delay:${j * 0.05}s">${n}</span>`
      ).join('');
      const stats = t.stats || {};
      return `<div class="ticket-card">
        <span class="ticket-badge">口${t.ticket}</span>
        <div class="flex flex-wrap justify-center">${balls}</div>
        <div class="ticket-stats">
          <span>合計 ${stats.sum || '?'}</span>
          <span>奇偶 ${stats.odd || '?'}-${stats.even || '?'}</span>
          <span>連続 ${stats.consec_pairs || 0}</span>
          <span>期待度 ${stats.avg_score || '?'}</span>
        </div>
      </div>`;
    }).join('');
  } catch (e) {
    console.error('predictions error:', e);
    grid.innerHTML = '<div class="syncing-placeholder col-span-full">データの取得に失敗しました。</div>';
  }
}

// --- Heatmap ---
async function loadHeatmap() {
  const grid = document.getElementById('heatmapGrid');
  // skeleton
  grid.innerHTML = Array(43).fill(0).map((_, i) =>
    `<div class="hm-cell lv1-bg" style="opacity:0.3"><span class="hm-num">${i+1}</span></div>`
  ).join('');

  try {
    const data = await fetchJSON('/api/expectation');
    if (!data.ready || !data.items || data.items.length === 0) {
      grid.innerHTML = Array(43).fill(0).map((_, i) =>
        `<div class="hm-cell lv1-bg" style="opacity:0.3;animation:pulse 1.5s ease-in-out infinite"><span class="hm-num">${i+1}</span></div>`
      ).join('');
      return;
    }
    grid.innerHTML = data.items.map(item => {
      const lv = item.level || 1;
      const c = item.components || {};
      return `<div class="hm-cell lv${lv}-bg"
        data-tip="スコア ${item.score} | 出現 ${c.freq || 0}回 | 未出 ${c.gap || 0}回 | 直近 ${c.recent || 0}回"
        onmouseenter="showTip(event)" onmouseleave="hideTip()">
        <span class="hm-num">${item.number}</span>
        <span class="hm-lv">Lv${lv}</span>
      </div>`;
    }).join('');
  } catch (e) {
    console.error('heatmap error:', e);
  }
}

// --- Tooltip ---
function showTip(e) {
  const tip = document.getElementById('tooltip');
  tip.textContent = e.currentTarget.dataset.tip;
  tip.classList.remove('hidden');
  const rect = e.currentTarget.getBoundingClientRect();
  tip.style.left = rect.left + 'px';
  tip.style.top = (rect.bottom + 6) + 'px';
}
function hideTip() {
  document.getElementById('tooltip').classList.add('hidden');
}

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
  loadStatus();
  loadLatest();
  loadPredictions();
  loadHeatmap();
});
