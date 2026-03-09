/* ── BA DASHBOARD JS ── */
const BA = { navy: '#003366', blue: '#00509E', light: '#E8EFF8', gold: '#C4930A' };

function gradient(ctx, c1, c2) {
  const g = ctx.createLinearGradient(0, 0, 0, 400);
  g.addColorStop(0, c1); g.addColorStop(1, c2); return g;
}

const chartDefaults = {
  responsive: true, maintainAspectRatio: false,
  plugins: { legend: { labels: { font: { family: 'Inter', size: 12 }, color: '#64748b' } } },
};

/* Tab switching */
function initTabs() {
  document.querySelectorAll('[data-tab]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      document.querySelectorAll('[data-tab]').forEach(b => {
        b.classList.remove('bg-ba-navy', 'text-white', 'shadow-md');
        b.classList.add('bg-white', 'text-slate-600');
      });
      btn.classList.remove('bg-white', 'text-slate-600');
      btn.classList.add('bg-ba-navy', 'text-white', 'shadow-md');
      document.querySelectorAll('.tab-content').forEach(tc => tc.classList.add('hidden'));
      document.getElementById(target).classList.remove('hidden');
      if (target === 'dashboardTab') loadDashboard();
    });
  });
}

let dashboardLoaded = false;

async function loadDashboard() {
  if (dashboardLoaded) { refreshMetrics(); refreshPredictions(); return; }
  dashboardLoaded = true;
  try {
    const [analytics, fi, cohort] = await Promise.all([
      fetch('/api/analytics').then(r => r.json()),
      fetch('/api/feature-importance').then(r => r.json()),
      fetch('/api/cohort').then(r => r.json()),
    ]);
    renderKPIs(analytics);
    renderFeatureImportance(fi);
    renderChannelChart(analytics);
    renderTripChart(analytics);
    renderDayChart(analytics);
    renderHourChart(analytics);
    renderTopRoutes(analytics);
    renderTopCountries(analytics);
    renderCohortTable(cohort);
    renderExtrasChart(cohort);
    refreshMetrics();
    refreshPredictions();
  } catch (e) { console.error('Dashboard load error:', e); }
}

/* KPI Cards */
function renderKPIs(d) {
  const el = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
  el('kpi-total', d.total.toLocaleString('tr-TR'));
  el('kpi-rate', '%' + d.completion_rate);
  el('kpi-stay', d.avg_stay + ' gün');
  el('kpi-lead', d.avg_lead + ' gün');
  el('kpi-duration', d.avg_duration + ' saat');
  el('kpi-passengers', d.avg_passengers);
}

/* Feature Importance */
function renderFeatureImportance(d) {
  const ctx = document.getElementById('fiChart');
  if (!ctx) return;
  const features = d.features.slice(0, 14);
  new Chart(ctx, {
    type: 'bar', data: {
      labels: features.map(f => f.label),
      datasets: [{ label: 'Önem Skoru', data: features.map(f => f.importance),
        backgroundColor: features.map((_, i) => {
          const ratio = i / features.length;
          return `rgba(${Math.round(0 + ratio * 196)}, ${Math.round(51 - ratio * 51 + ratio * 147)}, ${Math.round(102 - ratio * 102 + ratio * 10)}, 0.85)`;
        }),
        borderColor: BA.navy, borderWidth: 1, borderRadius: 4,
      }]
    }, options: { ...chartDefaults, indexAxis: 'y',
      plugins: { ...chartDefaults.plugins, legend: { display: false } },
      scales: { x: { grid: { color: '#f1f5f9' }, ticks: { font: { family: 'Inter' } } },
        y: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 } } } }
    }
  });
}

/* Channel Doughnut */
function renderChannelChart(d) {
  const ctx = document.getElementById('channelChart');
  if (!ctx) return;
  const labels = Object.keys(d.channel_distribution);
  const data = Object.values(d.channel_distribution);
  new Chart(ctx, {
    type: 'doughnut', data: {
      labels, datasets: [{ data, backgroundColor: [BA.navy, BA.blue, BA.gold, '#64748b', '#94a3b8'],
        borderWidth: 2, borderColor: '#fff' }]
    }, options: { ...chartDefaults, cutout: '65%',
      plugins: { ...chartDefaults.plugins, legend: { position: 'bottom' } } }
  });
}

/* Trip Type Doughnut */
function renderTripChart(d) {
  const ctx = document.getElementById('tripChart');
  if (!ctx) return;
  const labels = Object.keys(d.trip_distribution);
  const data = Object.values(d.trip_distribution);
  new Chart(ctx, {
    type: 'doughnut', data: {
      labels, datasets: [{ data, backgroundColor: [BA.gold, BA.navy, BA.blue, '#94a3b8'],
        borderWidth: 2, borderColor: '#fff' }]
    }, options: { ...chartDefaults, cutout: '65%',
      plugins: { ...chartDefaults.plugins, legend: { position: 'bottom' } } }
  });
}

/* Day Completion Bar */
function renderDayChart(d) {
  const ctx = document.getElementById('dayChart');
  if (!ctx) return;
  const dayLabels = { Mon: 'Pzt', Tue: 'Sal', Wed: 'Çar', Thu: 'Per', Fri: 'Cum', Sat: 'Cmt', Sun: 'Paz' };
  const labels = Object.keys(d.day_completion).map(k => dayLabels[k] || k);
  new Chart(ctx, {
    type: 'bar', data: {
      labels, datasets: [{ label: 'Tamamlanma %', data: Object.values(d.day_completion),
        backgroundColor: BA.blue + 'cc', borderColor: BA.navy, borderWidth: 1, borderRadius: 6 }]
    }, options: { ...chartDefaults,
      plugins: { ...chartDefaults.plugins, legend: { display: false } },
      scales: { y: { beginAtZero: true, max: 100, grid: { color: '#f1f5f9' } }, x: { grid: { display: false } } } }
  });
}

/* Hour Completion Line */
function renderHourChart(d) {
  const ctx = document.getElementById('hourChart');
  if (!ctx) return;
  const labels = Object.keys(d.hour_completion).map(h => h + ':00');
  new Chart(ctx, {
    type: 'line', data: {
      labels, datasets: [{ label: 'Tamamlanma %', data: Object.values(d.hour_completion),
        borderColor: BA.navy, backgroundColor: BA.light + '80', fill: true, tension: 0.4,
        pointBackgroundColor: BA.navy, pointRadius: 3, pointHoverRadius: 6 }]
    }, options: { ...chartDefaults,
      plugins: { ...chartDefaults.plugins, legend: { display: false } },
      scales: { y: { beginAtZero: true, max: 100, grid: { color: '#f1f5f9' } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } } } }
  });
}

/* Top Routes Horizontal Bar */
function renderTopRoutes(d) {
  const ctx = document.getElementById('routeChart');
  if (!ctx) return;
  const labels = Object.keys(d.top_routes).map(r => r.slice(0,3) + '→' + r.slice(3));
  new Chart(ctx, {
    type: 'bar', data: {
      labels, datasets: [{ label: 'Rezervasyon', data: Object.values(d.top_routes),
        backgroundColor: BA.gold + 'cc', borderColor: BA.gold, borderWidth: 1, borderRadius: 4 }]
    }, options: { ...chartDefaults, indexAxis: 'y',
      plugins: { ...chartDefaults.plugins, legend: { display: false } },
      scales: { x: { grid: { color: '#f1f5f9' } }, y: { grid: { display: false } } } }
  });
}

/* Top Countries Bar */
function renderTopCountries(d) {
  const ctx = document.getElementById('countryChart');
  if (!ctx) return;
  new Chart(ctx, {
    type: 'bar', data: {
      labels: Object.keys(d.top_countries),
      datasets: [{ label: 'Rezervasyon', data: Object.values(d.top_countries),
        backgroundColor: BA.navy + 'cc', borderColor: BA.navy, borderWidth: 1, borderRadius: 4 }]
    }, options: { ...chartDefaults, indexAxis: 'y',
      plugins: { ...chartDefaults.plugins, legend: { display: false } },
      scales: { x: { grid: { color: '#f1f5f9' } }, y: { grid: { display: false } } } }
  });
}

/* Cohort Table */
function renderCohortTable(d) {
  const table = document.getElementById('cohortBody');
  if (!table) return;
  table.innerHTML = '';
  d.channels.forEach(ch => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td class="px-4 py-3 font-medium text-sm text-slate-700 border-b border-slate-100">${ch}</td>`;
    d.trip_types.forEach(tt => {
      const rate = d.matrix[ch]?.[tt] ?? '-';
      const count = d.counts[ch]?.[tt] ?? 0;
      const bgClass = rate > 20 ? 'bg-emerald-50 text-emerald-700' : rate > 10 ? 'bg-yellow-50 text-yellow-700' : 'bg-red-50 text-red-600';
      tr.innerHTML += `<td class="px-4 py-3 text-center border-b border-slate-100">
        <span class="inline-block px-2 py-1 rounded-lg text-xs font-bold ${bgClass}">%${rate}</span>
        <p class="text-[10px] text-slate-400 mt-0.5">${count.toLocaleString()} kayıt</p></td>`;
    });
    table.appendChild(tr);
  });
}

/* Extras (Baggage/Seat/Meal) Chart */
function renderExtrasChart(d) {
  const ctx = document.getElementById('extrasChart');
  if (!ctx) return;
  const labels = ['Bagaj Yok', 'Bagaj Var', 'Koltuk Yok', 'Koltuk Var', 'Yemek Yok', 'Yemek Var'];
  const data = [
    d.extras.baggage['0'] || 0, d.extras.baggage['1'] || 0,
    d.extras.seat['0'] || 0, d.extras.seat['1'] || 0,
    d.extras.meal['0'] || 0, d.extras.meal['1'] || 0,
  ];
  const colors = [BA.navy+'99', BA.navy, BA.blue+'99', BA.blue, BA.gold+'99', BA.gold];
  new Chart(ctx, {
    type: 'bar', data: {
      labels, datasets: [{ label: 'Tamamlanma %', data, backgroundColor: colors, borderRadius: 6, borderWidth: 0 }]
    }, options: { ...chartDefaults,
      plugins: { ...chartDefaults.plugins, legend: { display: false } },
      scales: { y: { beginAtZero: true, max: 100, grid: { color: '#f1f5f9' } }, x: { grid: { display: false } } } }
  });
}

/* Live Metrics */
async function refreshMetrics() {
  try {
    const d = await fetch('/api/metrics').then(r => r.json());
    const el = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
    el('lm-total', d.total_predictions);
    el('lm-rate', '%' + d.completion_rate);
    el('lm-avg', '%' + d.avg_probability);
    el('lm-route', d.top_route);
    el('lm-yes', d.completed);
    el('lm-no', d.not_completed);
  } catch (e) { console.error('Metrics error:', e); }
}

/* Recent Predictions */
async function refreshPredictions() {
  try {
    const d = await fetch('/api/predictions/recent').then(r => r.json());
    const tbody = document.getElementById('predBody');
    if (!tbody) return;
    if (!d.predictions.length) { tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-slate-400 text-sm">Henüz tahmin yapılmadı</td></tr>'; return; }
    tbody.innerHTML = d.predictions.map(p => {
      const cls = p.prediction === 1 ? 'text-emerald-600' : 'text-red-500';
      const badge = p.prediction === 1
        ? '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700">✓ Evet</span>'
        : '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-600">✗ Hayır</span>';
      const probBar = `<div class="flex items-center gap-2"><div class="w-16 bg-slate-100 rounded-full h-2 overflow-hidden"><div class="h-2 rounded-full ${p.probability >= 0.5 ? 'bg-emerald-400' : 'bg-red-400'}" style="width:${Math.round(p.probability*100)}%"></div></div><span class="text-xs font-semibold ${cls}">%${Math.round(p.probability*100)}</span></div>`;
      return `<tr class="hover:bg-slate-50 transition-colors">
        <td class="px-4 py-3 text-xs text-slate-400 border-b border-slate-50">${p.timestamp}</td>
        <td class="px-4 py-3 text-sm font-mono font-semibold text-ba-navy border-b border-slate-50">${p.route.slice(0,3)} → ${p.route.slice(3)}</td>
        <td class="px-4 py-3 text-sm text-slate-600 border-b border-slate-50">${p.origin}</td>
        <td class="px-4 py-3 text-sm text-slate-600 border-b border-slate-50">${p.passengers} kişi · ${p.channel}</td>
        <td class="px-4 py-3 border-b border-slate-50">${probBar}</td>
        <td class="px-4 py-3 border-b border-slate-50">${badge}</td></tr>`;
    }).join('');
  } catch (e) { console.error('Predictions error:', e); }
}

/* Auto-refresh every 10s */
setInterval(() => {
  if (!document.getElementById('dashboardTab')?.classList.contains('hidden')) {
    refreshMetrics(); refreshPredictions();
  }
}, 10000);

document.addEventListener('DOMContentLoaded', initTabs);
