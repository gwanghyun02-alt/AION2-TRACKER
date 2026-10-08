# -*- coding: utf-8 -*-
"""index.html 생성. 데이터를 페이지에 그대로 박아 넣는 단일 파일(외부 라이브러리 없음)."""
import json
import os
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


SRC_LABEL = {'reddit': 'Reddit', 'dc': 'DC', 'steamforum': 'Steam 토론'}


def build(base, cfg, sources, steam, runs, labels, out_path=None, public=False):
    """public=True: 외부 공개용 — 담당자가 적은 판단 이유·사용자 사전을 빼고 검색엔진 노출 차단(noindex)."""
    if public:
        labels = {k: v for k, v in labels.items() if k not in ('reasons', 'user_lex')}
    data = {
        'generated': datetime.now(KST).strftime('%Y-%m-%d %H:%M'),
        'game': cfg.get('game', '게임'),
        'sources': [[s, SRC_LABEL[s]] for s in sources],
        'source_desc': {'reddit': f"Reddit r/{cfg.get('reddit_sub')}", 'dc': f"DC {cfg.get('dc_id')} 갤",
                        'steamforum': 'Steam 토론'},
        'steam': steam,
        'runs': runs,
        'labels': labels,
        'public': public,
    }
    js = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    import html as _h
    html = TEMPLATE.replace('/*__DATA__*/null', js).replace('__GAME__', _h.escape(cfg.get('game', '게임')))
    if public:
        html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex,nofollow">', 1)
    out_path = out_path or os.path.join(base, 'index.html')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write(html)
    os.replace(tmp, out_path)


TEMPLATE = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>__GAME__ 반응 트래커</title>
<style>
:root{
  color-scheme:light;
  --bg:#f4f3ef; --surface:#fcfcfb; --surface-2:#f0efec; --border:#e2e0da;
  --text:#0b0b0b; --text-2:#52514e; --muted:#8a8984;
  --pos:#2a78d6; --neg:#e34948; --neu:#c9c7c0;
  --reddit:#1baf7a; --dc:#4a3aa7; --steamforum:#eda100; --line:#2a78d6;
  --grid:#e8e6e0; --chip-bg:#ecebe6; --warn-bg:#fff4cc; --warn-ink:#6b4b00;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --bg:#111110; --surface:#1a1a19; --surface-2:#232321; --border:#33332f;
    --text:#ffffff; --text-2:#c3c2b7; --muted:#8f8e86;
    --pos:#3987e5; --neg:#e66767; --neu:#4a4a46;
    --reddit:#199e70; --dc:#9085e9; --steamforum:#c98500; --line:#3987e5;
    --grid:#2b2b28; --chip-bg:#2a2a27; --warn-bg:#3a3014; --warn-ink:#f2d58a;
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#111110; --surface:#1a1a19; --surface-2:#232321; --border:#33332f;
  --text:#ffffff; --text-2:#c3c2b7; --muted:#8f8e86;
  --pos:#3987e5; --neg:#e66767; --neu:#4a4a46;
  --reddit:#199e70; --dc:#9085e9; --steamforum:#c98500; --line:#3987e5;
  --grid:#2b2b28; --chip-bg:#2a2a27; --warn-bg:#3a3014; --warn-ink:#f2d58a;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 "Pretendard","Malgun Gothic",system-ui,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:20px 16px 60px}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 16px;margin-bottom:16px}
h1{font-size:22px;margin:0}
h2{font-size:16px;margin:0 0 4px}
.sub{color:var(--text-2);font-size:13px}
.muted{color:var(--muted)}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:16px;min-width:0}
.grid{display:grid;gap:16px}
.kpis{grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin-bottom:16px}
.kpi .lbl{color:var(--text-2);font-size:12px}
.kpi .val{font-size:28px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.2}
.kpi .det{font-size:12px;color:var(--text-2)}
.two{grid-template-columns:repeat(auto-fit,minmax(min(100%,520px),1fr))}
.three{grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr))}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;margin-bottom:8px}
.btns{display:flex;gap:4px;flex-wrap:wrap}
.btns button,.theme{border:1px solid var(--border);background:var(--surface-2);color:var(--text-2);border-radius:6px;padding:3px 10px;font:inherit;font-size:12px;cursor:pointer}
.btns button.on{background:var(--text);color:var(--surface);border-color:var(--text)}
.theme{margin-left:auto}
svg{display:block;width:100%;height:auto;overflow:visible}
svg text{fill:var(--text-2);font-size:11px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--text-2);margin:4px 0 6px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.tip{position:fixed;pointer-events:none;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:8px 10px;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.15);z-index:10;display:none;max-width:320px}
.tip b{color:var(--text)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--border);vertical-align:top}
th{color:var(--text-2);font-weight:600;font-size:12px;position:sticky;top:0;background:var(--surface)}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.scroll{max-height:560px;overflow:auto}
.chip{display:inline-block;border-radius:999px;padding:0 8px;font-size:11px;background:var(--chip-bg);color:var(--text-2);margin-right:4px;white-space:nowrap}
.chip.pos::before,.chip.neg::before,.chip.neu::before{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:4px;vertical-align:0}
.chip.pos::before{background:var(--pos)}.chip.neg::before{background:var(--neg)}.chip.neu::before{background:var(--muted)}
.t3{margin:0 0 6px;padding:0;list-style:none}
.t3 li{margin-bottom:5px}
.t3 a{color:var(--text);text-decoration:none}
.t3 a:hover{text-decoration:underline}
.t3 .m{font-size:11px;color:var(--muted)}
.t3 .ko{font-size:12px;color:var(--text-2);margin-top:1px}
.bar{display:flex;height:10px;border-radius:3px;overflow:hidden;gap:2px;background:var(--surface)}
.bar span{display:block;height:100%}
.hbar{display:grid;grid-template-columns:110px 1fr 44px;gap:6px;align-items:center;font-size:12px;margin:3px 0}
.hbar .tr{background:var(--surface-2);border-radius:3px;height:12px;overflow:hidden}
.hbar .tr span{display:block;height:100%;border-radius:0 3px 3px 0}
.warn{background:var(--warn-bg);color:var(--warn-ink);border-radius:8px;padding:8px 12px;font-size:13px;margin-bottom:16px}
.note{font-size:12px;color:var(--muted);margin-top:6px}
.empty{color:var(--muted);padding:24px;text-align:center}
@media (max-width:600px){.kpi .val{font-size:22px}.hbar{grid-template-columns:84px 1fr 40px}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>__GAME__ 유저 반응 트래커</h1>
  <span class="sub" id="gen"></span>
  <button class="theme" id="theme" type="button">테마 전환</button>
</header>
<div id="warn"></div>
<div class="grid kpis" id="kpis"></div>

<section class="card">
  <div class="row"><div><h2>SteamDB Rating</h2><div class="sub">15분마다 기록 · SteamDB 공식 산식(긍정비율을 리뷰 수로 보정)</div></div>
  <div class="btns" data-for="steam"><button data-r="1">24시간</button><button data-r="7" class="on">7일</button><button data-r="30">30일</button><button data-r="0">전체</button></div></div>
  <div id="steam-chart"></div>
  <h2 style="margin-top:14px;font-size:14px">15분 신규 리뷰</h2>
  <div class="legend"><span><i style="background:var(--pos)"></i>추천</span><span><i style="background:var(--neg)"></i>비추천</span></div>
  <div id="steam-new"></div>
</section>

<section class="card">
  <div class="row"><div><h2>커뮤니티 긍정 비중</h2><div class="sub">30분 창마다 게시글+댓글을 하나하나 분류 · 긍정 ÷ (긍정+부정)</div></div>
  <div class="btns" data-for="comm"><button data-r="1">24시간</button><button data-r="7" class="on">7일</button><button data-r="30">30일</button><button data-r="0">전체</button></div></div>
  <div class="legend src-legend"></div>
  <div id="share-chart"></div>
</section>

<section class="card">
  <div class="row"><div><h2>커뮤니티별 수집량</h2><div class="sub">30분 창마다 수집해 분류한 건수 · 선이 끊긴 곳은 PC가 꺼져 있거나 절전이라 수집하지 못한 창</div></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <div class="btns" data-for="volm"><button data-r="0" class="on">전체</button><button data-r="1">게시글</button><button data-r="2">댓글</button></div>
    <div class="btns" data-for="vol"><button data-r="1">24시간</button><button data-r="7" class="on">7일</button><button data-r="30">30일</button><button data-r="0">전체</button></div>
  </div></div>
  <div class="legend src-legend"></div>
  <div id="vol-chart"></div>
  <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px;margin-top:10px" id="vol-stats"></div>
</section>

<section class="card">
  <div class="row"><div><h2>시간대별 게시물 수</h2><div class="sub">하루 중 몇 시에 많이 올라오나 · 시간대별 1시간 평균 건수 (실제로 수집한 창만으로 평균)</div></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <div class="btns" data-for="hrm"><button data-r="1" class="on">게시글</button><button data-r="2">댓글</button><button data-r="0">전체</button></div>
    <div class="btns" data-for="hr"><button data-r="7" class="on">최근 7일</button><button data-r="30">30일</button><button data-r="0">전체</button></div>
  </div></div>
  <div class="legend src-legend"></div>
  <div id="hour-chart"></div>
  <div class="note" id="hour-note"></div>
</section>

<div class="grid three" id="stacks"></div>

<section class="card">
  <h2>Top 3 게시물 성격 — 누적</h2>
  <div class="sub">DC는 30분 창에 올라온 글 중 조회수 순. Reddit·Steam 토론은 조회수를 공개하지 않아 <b>30분간 새 댓글 수</b> 순(동점이면 Reddit은 Hot 순위, Steam은 누적 댓글 수).</div>
  <div class="grid three" style="margin-top:12px" id="t3-summary"></div>
</section>

<section class="card">
  <div class="row"><div><h2>Top 3 논조 추이</h2><div class="sub">선: 수집 시작부터 누적한 긍정 ÷ (긍정+부정) · 막대: 각 30분 창의 Top 3 구성</div></div>
  <div style="display:flex;gap:8px;flex-wrap:wrap">
    <div class="btns" data-for="t3m"><button data-r="0" class="on">게시글 논조</button><button data-r="1">달린 댓글 반응</button></div>
    <div class="btns" data-for="t3"><button data-r="1">24시간</button><button data-r="7" class="on">7일</button><button data-r="30">30일</button><button data-r="0">전체</button></div>
  </div></div>
  <div class="legend src-legend"></div>
  <div id="t3-trend"></div>
  <div class="legend" style="margin-top:12px"><span><i style="background:var(--pos)"></i>긍정</span><span><i style="background:var(--neu)"></i>중립</span><span><i style="background:var(--neg)"></i>부정</span></div>
  <div class="grid three" id="t3-stacks"></div>
  <div class="note" id="t3-note"></div>
</section>

<section class="card">
  <div class="row"><h2>Top 3 타임라인</h2><span class="sub">최신 창이 위</span></div>
  <div class="scroll"><table style="table-layout:fixed;min-width:760px"><thead><tr><th style="width:96px">창</th><th id="t3-heads" style="display:none"></th></tr></thead><tbody id="t3-body"></tbody></table></div>
</section>

<div class="grid two">
<section class="card">
  <h2>정확도 개선(라벨링)</h2>
  <div class="sub">라벨링 폴더의 엑셀 '내 판단' 칸을 채워 저장하면 다음 실행부터 학습에 반영</div>
  <div id="labels"></div>
</section>
<section class="card">
  <h2>수집 로그</h2>
  <div class="scroll" style="max-height:340px"><table><thead><tr><th>창</th><th id="log-heads" style="display:none"></th><th>검토 엑셀</th></tr></thead><tbody id="runlog"></tbody></table></div>
</section>
</div>
<div class="tip" id="tip"></div>
</div>
<script>
const D = /*__DATA__*/null;
const $ = s => document.querySelector(s);
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const NS = 'http://www.w3.org/2000/svg';
const fmt = (v, d=1) => v == null ? '–' : (+v).toFixed(d);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const P = s => new Date(s + '+09:00');
const hm = d => `${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
const range = {steam: 7, comm: 7, t3: 7, t3m: 0, vol: 7, volm: 0, hr: 7, hrm: 1};

// 0~23시 묶음 막대 (소스별 나란히). series: [{name,color,vals:[24], n:[24]}]
function hourChart(box, series, label){
  box.innerHTML = '';
  if (!series.some(s => s.vals.some(v => v != null))){ box.innerHTML = '<div class="empty">아직 데이터가 없습니다</div>'; return; }
  const W = Math.max(320, box.clientWidth || 800), H = 240, m = {l:44, r:12, t:10, b:26};
  const svg = el('svg', {viewBox:`0 0 ${W} ${H}`, role:'img', 'aria-label': label}, box);
  const hi = Math.max(1, ...series.flatMap(s => s.vals.map(v => v || 0)));
  const y = v => m.t + (1 - v / hi) * (H - m.t - m.b);
  for (let i = 0; i <= 4; i++){ const v = hi * i / 4;
    el('line', {x1:m.l, x2:W-m.r, y1:y(v), y2:y(v), stroke:css(i ? '--grid' : '--muted')}, svg);
    const tx = el('text', {x:m.l-6, y:y(v)+4, 'text-anchor':'end'}, svg); tx.textContent = v >= 10 ? Math.round(v) : v.toFixed(1); }
  const gw = (W - m.l - m.r) / 24, k = series.length, bw = Math.max(2, Math.min(10, (gw - 4) / k - 2));
  for (let h = 0; h < 24; h++){
    const gx = m.l + h * gw;
    if (h % 3 === 0){ const tx = el('text', {x:gx + gw/2, y:H-8, 'text-anchor':'middle'}, svg); tx.textContent = h + '시'; }
    series.forEach((s, i) => { const v = s.vals[h]; if (v == null) return;
      const x = gx + (gw - k * (bw + 2)) / 2 + i * (bw + 2);
      el('rect', {x, y:y(v), width:bw, height:Math.max(0, y(0) - y(v)), fill:css(s.color), rx:Math.min(2, bw/2)}, svg); });
    const hit = el('rect', {x:gx, y:m.t, width:gw, height:H-m.t-m.b, fill:'transparent'}, svg);
    hit.addEventListener('mousemove', e => showTip(e, `<b>${h}시~${h+1}시</b> 1시간 평균<br>` + series.map(s =>
      `<div><b style="color:var(${s.color})">●</b> ${s.name}: <b>${s.vals[h] == null ? '–' : (s.vals[h] >= 10 ? Math.round(s.vals[h]) : s.vals[h].toFixed(1))}건</b> <span class="muted">(${s.n[h]}개 창)</span></div>`).join('')));
    hit.addEventListener('mouseleave', hideTip);
  }
}
const SRCS = D.sources;
// 소스 목록에 맞춰 범례·표 머리글을 만든다
document.querySelectorAll('.src-legend').forEach(e => e.innerHTML = SRCS.map(([s]) => `<span><i style="background:var(--${s})"></i>${esc(D.source_desc[s])}</span>`).join(''));
$('#t3-heads').outerHTML = SRCS.map(([s, nm]) => `<th style="width:${Math.floor(90/SRCS.length)}%">${nm} Top 3</th>`).join('');
$('#log-heads').outerHTML = SRCS.map(([s, nm]) => `<th class="num">${nm}</th>`).join('');
const NAME = Object.fromEntries(SRCS);

// ---- 테마
(function(){
  let t = null; try { t = localStorage.getItem('tracker-theme'); } catch(e) {}
  if (t) document.documentElement.dataset.theme = t;
  $('#theme').onclick = () => {
    const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    const n = dark ? 'light' : 'dark';
    document.documentElement.dataset.theme = n;
    try { localStorage.setItem('tracker-theme', n); } catch(e) {}
    render();
  };
})();

// ---- 툴팁
const tip = $('#tip');
function showTip(e, html){ tip.innerHTML = html; tip.style.display = 'block';
  const r = tip.getBoundingClientRect(); let x = e.clientX + 14, y = e.clientY + 14;
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 14; if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 14;
  tip.style.left = x + 'px'; tip.style.top = y + 'px'; }
function hideTip(){ tip.style.display = 'none'; }
function el(tag, attrs, parent){ const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; }

function filt(arr, key, days){ if (!days) return arr; const last = arr.length ? P(arr[arr.length-1][key]) : new Date(); const t0 = last - days*864e5; return arr.filter(r => P(r[key]) >= t0); }

// ---- 꺾은선 (공통)  series: [{name,color,pts:[{t,v,html}]}]
function lineChart(box, series, opt){
  box.innerHTML = '';
  const all = series.flatMap(s => s.pts);
  if (!all.length){ box.innerHTML = '<div class="empty">아직 데이터가 없습니다</div>'; return; }
  const W = Math.max(320, box.clientWidth || 800), H = opt.h || 240, m = {l:40, r: 16, t: 10, b: 24};
  const svg = el('svg', {viewBox:`0 0 ${W} ${H}`, role:'img', 'aria-label': opt.label || ''}, box);
  const ts = all.map(p => p.t), t0 = Math.min(...ts), t1 = Math.max(...ts) || t0 + 1;
  let lo = opt.min ?? Math.min(...all.map(p => p.v)), hi = opt.max ?? Math.max(...all.map(p => p.v));
  if (opt.pad){ const p = Math.max((hi - lo) * 0.15, opt.pad); lo -= p; hi += p; }
  if (hi === lo){ hi += 1; lo -= 1; }
  const x = t => m.l + (t1 === t0 ? (W-m.l-m.r)/2 : (t - t0) / (t1 - t0) * (W - m.l - m.r));
  const y = v => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  for (let i = 0; i <= 4; i++){ const v = lo + (hi - lo) * i / 4, yy = y(v);
    el('line', {x1:m.l, x2:W-m.r, y1:yy, y2:yy, stroke:css('--grid'), 'stroke-width':1}, svg);
    const tx = el('text', {x:m.l-6, y:yy+4, 'text-anchor':'end'}, svg); tx.textContent = (opt.ytick || (v => v.toFixed(1)))(v); }
  const nx = t1 === t0 ? 1 : Math.min(6, Math.max(2, Math.floor(W / 140)));
  for (let i = 0; i < nx; i++){ const t = nx === 1 ? t0 : t0 + (t1 - t0) * i / (nx - 1); const tx = el('text', {x:x(t), y:H-6, 'text-anchor': nx==1?'middle':i==0?'start':i==nx-1?'end':'middle'}, svg); tx.textContent = hm(new Date(t)); }
  if (opt.ref != null && opt.ref > lo && opt.ref < hi){ el('line', {x1:m.l, x2:W-m.r, y1:y(opt.ref), y2:y(opt.ref), stroke:css('--muted'), 'stroke-dasharray':'3 3'}, svg); }
  for (const s of series){
    if (!s.pts.length) continue;
    const gapMs = opt.gap || 3*36e5; let d = '';
    s.pts.forEach((p, i) => { const brk = i == 0 || p.t - s.pts[i-1].t > gapMs; d += `${brk?'M':'L'}${x(p.t).toFixed(1)},${y(p.v).toFixed(1)}`; });
    el('path', {d, fill:'none', stroke:css(s.color), 'stroke-width':2, 'stroke-linejoin':'round', 'stroke-linecap':'round'}, svg);
    if (s.pts.length < 60) s.pts.forEach(p => el('circle', {cx:x(p.t), cy:y(p.v), r:3, fill:css(s.color), stroke:css('--surface'), 'stroke-width':2}, svg));
    const lp = s.pts[s.pts.length-1];
    if (series.length > 1){ const tx = el('text', {x:Math.min(x(lp.t)+6, W-m.r), y:y(lp.v)-6, 'text-anchor':'end'}, svg); tx.textContent = s.name; tx.style.fill = css('--text'); }
  }
  const cross = el('line', {y1:m.t, y2:H-m.b, stroke:css('--muted'), 'stroke-width':1, visibility:'hidden'}, svg);
  const dots = series.map(s => el('circle', {r:5, fill:css(s.color), stroke:css('--surface'), 'stroke-width':2, visibility:'hidden'}, svg));
  const hit = el('rect', {x:m.l, y:m.t, width:W-m.l-m.r, height:H-m.t-m.b, fill:'transparent'}, svg);
  hit.addEventListener('mousemove', e => {
    const r = svg.getBoundingClientRect(); const px = (e.clientX - r.left) * W / r.width;
    const t = t0 + (px - m.l) / (W - m.l - m.r) * (t1 - t0);
    let html = '', cx = null;
    series.forEach((s, i) => { if (!s.pts.length){ return; }
      let b = s.pts[0]; for (const p of s.pts) if (Math.abs(p.t - t) < Math.abs(b.t - t)) b = p;
      cx = cx ?? x(b.t); dots[i].setAttribute('cx', x(b.t)); dots[i].setAttribute('cy', y(b.v)); dots[i].setAttribute('visibility','visible');
      html += b.html; });
    cross.setAttribute('x1', cx); cross.setAttribute('x2', cx); cross.setAttribute('visibility','visible');
    showTip(e, html);
  });
  hit.addEventListener('mouseleave', () => { hideTip(); cross.setAttribute('visibility','hidden'); dots.forEach(d => d.setAttribute('visibility','hidden')); });
}

// ---- 막대(위/아래 또는 100% 누적)
function barChart(box, bars, opt){
  box.innerHTML = '';
  if (!bars.length){ box.innerHTML = '<div class="empty">아직 데이터가 없습니다</div>'; return; }
  const W = Math.max(320, box.clientWidth || 800), H = opt.h || 160, m = {l:40, r:16, t:8, b:24};
  const svg = el('svg', {viewBox:`0 0 ${W} ${H}`, role:'img', 'aria-label': opt.label || ''}, box);
  const n = bars.length, bw = (W - m.l - m.r) / n, w = Math.max(1, Math.min(bw - 2, 28));
  let lo, hi;
  if (opt.stack){ lo = 0; hi = 100; } else { hi = Math.max(1, ...bars.map(b => b.up)); lo = -Math.max(1, ...bars.map(b => b.down)); }
  const y = v => m.t + (1 - (v - lo) / (hi - lo)) * (H - m.t - m.b);
  const ticks = opt.stack ? [0, 50, 100] : [lo, 0, hi];
  ticks.forEach(v => { el('line', {x1:m.l, x2:W-m.r, y1:y(v), y2:y(v), stroke:css(v===0&&!opt.stack?'--muted':'--grid')}, svg);
    const tx = el('text', {x:m.l-6, y:y(v)+4, 'text-anchor':'end'}, svg); tx.textContent = opt.stack ? v + '%' : Math.abs(Math.round(v)); });
  const nx = Math.min(6, n);
  for (let i = 0; i < nx; i++){ const k = Math.round((n-1) * i / Math.max(1, nx-1)); const tx = el('text', {x: m.l + bw*k + bw/2, y:H-6, 'text-anchor': nx==1?'middle':i==0?'start':i==nx-1?'end':'middle'}, svg); tx.textContent = bars[k].label; }
  bars.forEach((b, i) => {
    const x0 = m.l + i * bw + (bw - w) / 2, g = el('g', {}, svg);
    if (opt.stack){
      let acc = 0; const tot = b.segs.reduce((a, s) => a + s.v, 0) || 1;
      b.segs.forEach((s, k) => { const h = s.v / tot * 100; if (h <= 0) return;
        const y1 = y(acc + h), y0 = y(acc); el('rect', {x:x0, y:y1 + (k ? 0 : 0), width:w, height:Math.max(0, y0 - y1 - (acc + h < 100 ? 1 : 0)), fill:css(s.c)}, g); acc += h; });
    } else {
      if (b.up) el('rect', {x:x0, y:y(b.up), width:w, height:y(0)-y(b.up)-1, fill:css('--pos'), rx: Math.min(2, w/2)}, g);
      if (b.down) el('rect', {x:x0, y:y(0)+1, width:w, height:y(-b.down)-y(0)-1, fill:css('--neg'), rx: Math.min(2, w/2)}, g);
    }
    const hit = el('rect', {x:m.l + i*bw, y:m.t, width:bw, height:H-m.t-m.b, fill:'transparent'}, g);
    hit.addEventListener('mousemove', e => showTip(e, b.html)); hit.addEventListener('mouseleave', hideTip);
  });
}

function render(){
  $('#gen').textContent = `마지막 갱신 ${D.generated} KST · 5분마다 자동 새로고침`;
  const steam = D.steam || [], runs = D.runs || [];
  const last = steam[steam.length - 1];
  // ---- 경고: 최근 실행 누락
  const warn = [];
  if (last && (Date.now() - P(last.ts)) > 45*6e4) warn.push(`Steam 기록이 ${hm(P(last.ts))} 이후 멈췄습니다 (15분 주기).`);
  const lr = runs[runs.length - 1];
  if (lr && (Date.now() - P(lr.slot_end)) > 75*6e4) warn.push(`커뮤니티 분석이 ${hm(P(lr.slot_end))} 창 이후 멈췄습니다 (30분 주기).`);
  if (lr) for (const [s] of SRCS) if (lr.sources[s] && !lr.sources[s].ok) warn.push(`최근 창 ${NAME[s]} 수집 실패: ${esc(lr.sources[s].error)}`);
  if (lr) for (const [s] of SRCS) if (lr.sources[s]?.meta?.partial) warn.push(`최근 창 ${NAME[s]}는 요청 제한으로 일부만 수집됐습니다(글 제목은 모두 집계, 일부 본문·댓글 누락).`);
  $('#warn').innerHTML = warn.map(w => `<div class="warn">⚠ ${w}</div>`).join('');

  // ---- KPI
  const day = last ? steam.filter(r => P(r.ts) >= P(last.ts) - 864e5)[0] : null;
  const dlt = last && day ? last.steamdb_rating - day.steamdb_rating : null;
  const k = [];
  k.push(`<div class="card kpi"><div class="lbl">SteamDB Rating</div><div class="val">${last ? fmt(last.steamdb_rating, 2) + '%' : '–'}</div><div class="det">${last ? `24시간 ${dlt == null ? '–' : (dlt >= 0 ? '▲ ' : '▼ ') + Math.abs(dlt).toFixed(2) + '%p'} · ${esc(last.desc || '')}` : '수집 전'}</div></div>`);
  k.push(`<div class="card kpi"><div class="lbl">Steam 긍정 비율(원값)</div><div class="val">${last ? fmt(last.steam_pct, 1) + '%' : '–'}</div><div class="det">${last ? `추천 ${last.positive.toLocaleString()} · 비추천 ${last.negative.toLocaleString()}` : ''}</div></div>`);
  for (const [s, nm] of SRCS){
    const r = [...runs].reverse().find(r => r.sources[s] && r.sources[s].ok);
    const o = r && r.sources[s];
    k.push(`<div class="card kpi"><div class="lbl">${nm} 최근 30분 · 긍정 / 부정</div><div class="val">${o && o.n ? `${fmt(o.pos_pct,0)}% / ${fmt(o.neg_pct,0)}%` : '–'}</div><div class="det">${o ? `${hm(P(r.slot_start)).slice(6)}~${hm(P(r.slot_end)).slice(6)} · 글 ${o.posts} · 댓글 ${o.comments} · 중립 ${fmt(100 - o.pos_pct - o.neg_pct, 0)}%` : '수집 전'}</div></div>`);
  }
  $('#kpis').innerHTML = k.join('');

  // ---- Steam
  const sv = filt(steam, 'ts', range.steam);
  lineChart($('#steam-chart'), [{name:'SteamDB', color:'--line', pts: sv.map(r => ({t:+P(r.ts), v:r.steamdb_rating,
    html:`<b>${hm(P(r.ts))}</b><br>SteamDB Rating <b>${fmt(r.steamdb_rating,2)}%</b><br>Steam 원값 ${fmt(r.steam_pct,2)}% · 리뷰 ${r.total.toLocaleString()}`}))}],
    {h:240, pad:0.3, ytick:v => v.toFixed(1)+'%', gap: 2*36e5, label:'SteamDB Rating 추이'});
  barChart($('#steam-new'), sv.filter(r => r.new_pos != null).map(r => ({label:hm(P(r.ts)), up:Math.max(0,r.new_pos), down:Math.max(0,r.new_neg),
    html:`<b>${hm(P(r.ts))}</b> 직전 기록 이후<br>추천 +${r.new_pos} · 비추천 +${r.new_neg}`})), {h:130, label:'15분 신규 리뷰'});

  // ---- 커뮤니티
  const rv = filt(runs, 'slot_end', range.comm);
  const share = s => rv.filter(r => r.sources[s] && r.sources[s].ok && r.sources[s].pos_share != null).map(r => { const o = r.sources[s];
    return {t:+P(r.slot_end), v:o.pos_share, html:`<div><b style="color:var(--${s})">●</b> <b>${NAME[s]}</b> ${hm(P(r.slot_start)).slice(6)}~${hm(P(r.slot_end)).slice(6)}: 긍정 비중 <b>${fmt(o.pos_share)}%</b> (긍 ${o.pos} · 중 ${o.neu} · 부 ${o.neg})${o.orig && o.orig.pos_share !== o.pos_share ? ` <span class="muted">· 수집 당시 ${fmt(o.orig.pos_share)}%</span>` : ''}</div>`}; });
  lineChart($('#share-chart'), SRCS.map(([s, nm]) => ({name:nm, color:'--' + s, pts:share(s)})),
    {h:240, min:0, max:100, ref:50, ytick:v => v.toFixed(0)+'%', gap: 2*36e5, label:'커뮤니티 긍정 비중'});
  $('#stacks').innerHTML = SRCS.map(([s, nm]) => `<section class="card"><h2>${nm} 30분 창 구성</h2><div class="sub">막대 높이 = 100% · 긍정 / 중립 / 부정</div>
    <div class="legend"><span><i style="background:var(--pos)"></i>긍정</span><span><i style="background:var(--neu)"></i>중립</span><span><i style="background:var(--neg)"></i>부정</span></div>
    <div id="stack-${s}"></div></section>`).join('');
  for (const [s] of SRCS){
    barChart($('#stack-' + s), rv.filter(r => r.sources[s] && r.sources[s].ok && r.sources[s].n).map(r => { const o = r.sources[s];
      return {label:hm(P(r.slot_end)), segs:[{v:o.pos, c:'--pos'}, {v:o.neu, c:'--neu'}, {v:o.neg, c:'--neg'}],
        html:`<b>${hm(P(r.slot_start))}~${hm(P(r.slot_end)).slice(6)}</b><br>긍정 ${o.pos} (${fmt(o.pos_pct)}%)<br>중립 ${o.neu}<br>부정 ${o.neg} (${fmt(o.neg_pct)}%)<br><span class="muted">글 ${o.posts} · 댓글 ${o.comments}</span>`}; }),
      {stack:true, h:170, label:s + ' 창 구성'});
  }

  // ---- 커뮤니티별 수집량 (30분 창)
  const volKey = ['n', 'posts', 'comments'][range.volm], volName = ['게시글+댓글', '게시글', '댓글'][range.volm];
  const vr = filt(runs, 'slot_end', range.vol);
  lineChart($('#vol-chart'), SRCS.map(([s, nm]) => ({name: nm, color: '--' + s,
    pts: vr.filter(r => r.sources[s] && r.sources[s].ok).map(r => { const o = r.sources[s];
      return {t: +P(r.slot_end), v: o[volKey] || 0, html: `<div><b style="color:var(--${s})">●</b> <b>${nm}</b> ${hm(P(r.slot_start)).slice(6)}~${hm(P(r.slot_end)).slice(6)}: ${volName} <b>${(o[volKey] || 0).toLocaleString()}건</b> <span class="muted">(글 ${o.posts} · 댓글 ${o.comments})</span></div>`}; })})),
    {h: 220, min: 0, pad: 0, ytick: v => Math.round(v).toLocaleString(), gap: 35 * 6e4, label: '커뮤니티별 수집량'});
  // 누적·평균·빠진 창 (수집 시작 이후 전체 기준)
  const first = runs.length ? +P(runs[0].slot_end) : 0, lastT = runs.length ? +P(runs[runs.length - 1].slot_end) : 0;
  const expected = runs.length ? Math.round((lastT - first) / 18e5) + 1 : 0;
  const missing = Math.max(0, expected - runs.length);
  $('#vol-stats').innerHTML = SRCS.map(([s, nm]) => {
    const ok = runs.filter(r => r.sources[s] && r.sources[s].ok);
    const tot = ok.reduce((a, r) => a + (r.sources[s][volKey] || 0), 0);
    const fail = runs.filter(r => r.sources[s] && !r.sources[s].ok).length;
    return `<div><div class="sub"><b style="color:var(--${s})">●</b> ${nm} · 누적 ${volName}</div><div style="font-size:20px;font-weight:700">${tot.toLocaleString()}건</div>
      <div class="note">창당 평균 ${ok.length ? Math.round(tot / ok.length).toLocaleString() : '–'}건 · 수집 ${ok.length}창${fail ? ` · 실패 ${fail}창` : ''}</div></div>`;
  }).join('') + `<div><div class="sub">수집 기간</div><div style="font-size:20px;font-weight:700">${runs.length}창</div>
      <div class="note">${runs.length ? `${hm(P(runs[0].slot_start))} 부터` : ''}${missing ? ` · <b>빠진 창 ${missing}개</b>` : ' · 빠진 창 없음'}</div></div>`;

  // ---- 시간대별 게시물 수: 창 시작 시각의 '시'로 묶어 창당 평균 × 2 (= 1시간 평균)
  const hrKey = ['n', 'posts', 'comments'][range.hrm], hrName = ['게시글+댓글', '게시글', '댓글'][range.hrm];
  const hrRuns = filt(runs, 'slot_end', range.hr);
  hourChart($('#hour-chart'), SRCS.map(([s, nm]) => {
    const sum = Array(24).fill(0), n = Array(24).fill(0);
    hrRuns.forEach(r => { const o = r.sources[s]; if (!o || !o.ok) return; const h = P(r.slot_start).getHours(); sum[h] += o[hrKey] || 0; n[h]++; });
    return {name: nm, color: '--' + s, n, vals: sum.map((v, h) => n[h] ? v / n[h] * 2 : null)};
  }), '시간대별 ' + hrName);
  const days = hrRuns.length ? ((+P(hrRuns[hrRuns.length-1].slot_end) - +P(hrRuns[0].slot_start)) / 864e5).toFixed(1) : 0;
  const peak = SRCS.map(([s, nm]) => { const sum = Array(24).fill(0), n = Array(24).fill(0);
    hrRuns.forEach(r => { const o = r.sources[s]; if (!o || !o.ok) return; const h = P(r.slot_start).getHours(); sum[h] += o[hrKey] || 0; n[h]++; });
    const av = sum.map((v, h) => n[h] ? v / n[h] : -1); const ph = av.indexOf(Math.max(...av));
    return ph >= 0 && av[ph] > 0 ? `${nm} ${ph}시` : null; }).filter(Boolean);
  $('#hour-note').textContent = `${hrName} 기준 · ${hrRuns.length}개 창(약 ${days}일)으로 계산` + (peak.length ? ` · 가장 많은 시간대: ${peak.join(', ')}` : '') + ' · 수집 기간이 짧으면 시간대별 표본이 적어 들쭉날쭉할 수 있습니다.';

  // ---- Top3 누적
  const sum = $('#t3-summary'); sum.innerHTML = '';
  for (const [s, nm] of SRCS){
    const all = runs.filter(r => r.sources[s] && r.sources[s].ok).flatMap(r => r.sources[s].top3 || []);
    const lastDay = runs.filter(r => r.sources[s] && r.sources[s].ok && P(r.slot_end) >= (runs.length ? P(runs[runs.length-1].slot_end) - 864e5 : 0)).flatMap(r => r.sources[s].top3 || []);
    const cnt = (arr, f) => arr.reduce((m, x) => (m[f(x)] = (m[f(x)] || 0) + 1, m), {});
    const lab = cnt(all, x => x.label), top = cnt(all, x => x.topic), top24 = cnt(lastDay, x => x.topic);
    const n = all.length || 1, n24 = lastDay.length || 1;
    const topics = Object.entries(top).sort((a, b) => b[1] - a[1]);
    sum.insertAdjacentHTML('beforeend', `<div><h2 style="font-size:14px">${nm} <span class="muted" style="font-weight:400">· 누적 ${all.length}건</span></h2>
      <div class="bar" style="margin:8px 0 4px" title="긍정 ${lab['긍정']||0} · 중립 ${lab['중립']||0} · 부정 ${lab['부정']||0}">
        <span style="width:${(lab['긍정']||0)/n*100}%;background:var(--pos)"></span><span style="width:${(lab['중립']||0)/n*100}%;background:var(--neu)"></span><span style="width:${(lab['부정']||0)/n*100}%;background:var(--neg)"></span></div>
      <div class="sub" style="margin-bottom:10px">게시글 논조 · 긍정 ${lab['긍정']||0} · 중립 ${lab['중립']||0} · 부정 ${lab['부정']||0}</div>
      <div class="sub" style="margin-bottom:4px">주제 비중 — 막대: 누적 / 숫자 옆 괄호: 최근 24시간</div>
      ${topics.length ? topics.map(([t, c]) => `<div class="hbar"><span>${esc(t)}</span><div class="tr"><span style="width:${c/n*100}%;background:var(--${s})"></span></div><span class="muted" style="text-align:right">${Math.round(c/n*100)}% <span style="font-size:10px">(${Math.round((top24[t]||0)/n24*100)})</span></span></div>`).join('') : '<div class="empty">아직 없음</div>'}</div>`);
  }

  // ---- Top3 논조 추이 (누적은 전체 기간으로 계산한 뒤 표시 구간만 자른다)
  const byCmt = range.t3m === 1;
  const t0show = runs.length ? +P(runs[runs.length-1].slot_end) - (range.t3 ? range.t3*864e5 : Infinity) : 0;
  const t3series = SRCS.map(([s, nm]) => {
    let cp = 0, cn = 0; const pts = [], bars = [];
    for (const r of runs){
      const o = r.sources[s]; if (!o || !o.ok || !(o.top3||[]).length) continue;
      let p = 0, u = 0, n = 0;
      for (const t of o.top3){
        if (byCmt){ p += t.cmt_pos||0; n += t.cmt_neg||0; u += t.cmt_neu||0; }
        else { t.label === '긍정' ? p++ : t.label === '부정' ? n++ : u++; }
      }
      cp += p; cn += n;
      const t = +P(r.slot_end); if (t < t0show) continue;
      const when = `${hm(P(r.slot_start))}~${hm(P(r.slot_end)).slice(6)}`;
      const titles = o.top3.map(x => `[${x.label}] ${esc((x.title_ko || x.title).slice(0, 40))}`).join('<br>');
      if (cp + cn) pts.push({t, v: cp/(cp+cn)*100, html:`<div><b style="color:var(--${s})">●</b> <b>${nm}</b> ~${hm(P(r.slot_end)).slice(6)} 누적 긍정 비중 <b>${fmt(cp/(cp+cn)*100)}%</b> <span class="muted">(누적 긍 ${cp} · 부 ${cn})</span></div>`});
      bars.push({label: hm(P(r.slot_end)), segs:[{v:p, c:'--pos'}, {v:u, c:'--neu'}, {v:n, c:'--neg'}],
        html:`<b>${nm} ${when}</b><br>${byCmt ? `Top 3 글에 달린 댓글 — 긍 ${p} · 중 ${u} · 부 ${n}` : `Top 3 게시글 — 긍 ${p} · 중 ${u} · 부 ${n}`}<br><span class="muted">${titles}</span>`});
    }
    return {s, nm, pts, bars};
  });
  lineChart($('#t3-trend'), t3series.map(x => ({name:x.nm, color:'--' + x.s, pts:x.pts})),
    {h:220, min:0, max:100, ref:50, ytick:v => v.toFixed(0)+'%', gap: 2*36e5, label:'Top 3 누적 긍정 비중'});
  $('#t3-stacks').innerHTML = t3series.map(x => `<div><div class="sub" style="margin:4px 0">${x.nm}</div><div id="t3s-${x.s}"></div></div>`).join('');
  t3series.forEach(x => barChart($('#t3s-' + x.s), x.bars, {stack:true, h:130, label:x.nm + ' Top 3 구성'}));
  $('#t3-note').textContent = byCmt ? 'Top 3 글에 그 30분 동안 달린 댓글을 하나하나 분류해 합산합니다.' : 'Top 3 각 글(제목+본문)의 논조 3건을 창마다 셉니다. 엑셀 라벨이 반영되면 과거 창까지 다시 계산됩니다.';

  // ---- Top3 타임라인
  const chip = l => `<span class="chip ${l==='긍정'?'pos':l==='부정'?'neg':'neu'}">${l}</span>`;
  const t3html = (o, s) => !o ? '<span class="muted">–</span>' : !o.ok ? `<span class="muted">수집 실패</span>` : !(o.top3||[]).length ? '<span class="muted">게시물 없음</span>' :
    '<ol class="t3">' + o.top3.map(t => `<li>${chip(t.label)}<span class="chip">${esc(t.topic)}</span><a href="${esc(t.url)}" target="_blank" rel="noopener">${esc(t.title)}</a>${t.title_ko ? `<div class="ko">↳ ${esc(t.title_ko)}</div>` : ''}
      <div class="m">${s==='dc' ? `조회 ${t.views ?? '–'} · 추천 ${t.reco ?? 0} · ` : s==='steamforum' ? (t.total_replies != null ? `누적 댓글 ${t.total_replies} · ` : '') : (t.hot_rank ? `Hot ${t.hot_rank}위 · ` : '')}30분 댓글 ${t.win_comments}${t.win_comments ? ` (긍 ${t.cmt_pos} · 부 ${t.cmt_neg})` : ''}</div></li>`).join('') + '</ol>';
  $('#t3-body').innerHTML = [...runs].reverse().slice(0, 200).map(r => `<tr><td>${hm(P(r.slot_start))}<br><span class="muted">~${hm(P(r.slot_end)).slice(6)}</span></td>${SRCS.map(([s]) => `<td>${t3html(r.sources[s], s)}</td>`).join('')}</tr>`).join('') || '<tr><td colspan="9" class="empty">아직 없음</td></tr>';

  // ---- 라벨링
  const L = D.labels || {}; const cv = L.cv;
  const files = (L.files || []).slice().reverse();
  const done = files.filter(f => f.labeled > 0);
  const agree = done.reduce((a, f) => a + f.agree, 0), lab = done.reduce((a, f) => a + f.labeled, 0);
  $('#labels').innerHTML = `
    <div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px;margin:10px 0">
      <div><div class="sub">라벨 누적</div><div style="font-size:22px;font-weight:700">${L.labeled || 0}건</div><div class="note">긍 ${L.class_n?.['긍정']||0} · 중 ${L.class_n?.['중립']||0} · 부 ${L.class_n?.['부정']||0}</div></div>
      <div><div class="sub">학습 반영</div><div style="font-size:22px;font-weight:700">${L.usable ? '학습 모델' : (L.labeled >= 30 ? '사전 채택' : '대기')}</div><div class="note">${L.usable ? '교차검증에서 사전보다 나아 채택' : (L.labeled >= 30 ? '교차검증 결과 사전이 더 정확' : '30건·긍/부 각 5건 이상부터')}</div></div>
      <div><div class="sub">애매한 건 당시 일치율</div><div style="font-size:22px;font-weight:700">${lab ? fmt(agree/lab*100,0)+'%' : '–'}</div><div class="note">라벨 vs 엑셀의 프로그램 판단</div></div>
      <div><div class="sub">5-fold 정확도</div><div style="font-size:22px;font-weight:700">${cv ? fmt(cv.model,0)+'%' : '–'}</div><div class="note">${cv ? `사전만 ${fmt(cv.lexicon,0)}% → 학습 ${fmt(cv.model,0)}%` : '라벨 30건부터'}</div></div>
    </div>
    <div class="note" style="margin:0 0 8px">${L.pending ? '⏳ 새 라벨이 감지됐습니다 — 다음 커뮤니티 실행(최대 30분 내)에 과거 수집분 전체를 다시 계산합니다. 바로 반영하려면 라벨반영_재계산.bat' :
      L.state && L.state.rescored_at ? `✓ 과거 수집분 ${(L.state.items||0).toLocaleString()}건 · ${L.state.runs}개 창을 라벨 ${L.state.labeled}건 기준으로 재계산함 (${L.state.rescored_at.replace('T',' ').slice(5,16)})` : ''}</div>
    <div class="scroll" style="max-height:220px"><table><thead><tr><th>검토 파일</th><th class="num">라벨</th><th class="num">일치</th></tr></thead><tbody>
    ${files.slice(0, 100).map(f => `<tr><td>${esc(f.file)}</td><td class="num">${f.labeled}</td><td class="num">${f.labeled ? Math.round(f.agree/f.labeled*100)+'%' : '–'}</td></tr>`).join('') || '<tr><td colspan="3" class="empty">아직 없음</td></tr>'}
    </tbody></table></div>
    ${aiHtml(L)}
    ${reasonsHtml(L)}
    <div class="note">파일 위치: 트래커 폴더\\라벨링\\ — 판단·이유를 바꾸면 다음 커뮤니티 실행 때 과거 수치까지 자동 재계산 (바로 하려면 라벨반영_재계산.bat)</div>`;

  // ---- 로그
  const cell = o => !o ? '–' : o.ok ? `${o.n}건` : '<span style="color:var(--neg)">실패</span>';
  $('#runlog').innerHTML = [...runs].reverse().slice(0, 100).map(r => `<tr><td>${hm(P(r.slot_start))}~${hm(P(r.slot_end)).slice(6)}</td>${SRCS.map(([s]) => `<td class="num">${cell(r.sources[s])}</td>`).join('')}<td>${esc(r.review_file || '–')}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">아직 없음</td></tr>';
}

// AI 분류 자동 재시험 현황 (라벨이 ai_every 건 늘 때마다 5-fold, '사전 + 5%p' 넘으면 켜짐)
function aiHtml(L){
  const A = L.ai || {}, hist = (A.history || []).filter(h => h.ok).slice(-6).reverse();
  const names = {ai_only:'AI만', h_only:'AI 분명함만', hm:'AI h·m', neutral_hm:'사전 중립→AI(h·m)', neutral_h:'사전 중립→AI(h)'};
  const next = (A.last_eval_n || 0) + (L.ai_every || 100);
  const mode = A.enabled ? `<b style="color:var(--pos)">AI 분류 사용 중</b> · ${esc(names[A.variant] || A.variant)} (${esc((A.enabled_at || '').replace('T',' ').slice(5,16))}부터)`
                         : `<b>사전 방식</b> · AI는 기준 미달로 대기`;
  return `<h2 style="font-size:14px;margin-top:14px">AI 분류 자동 재시험</h2>
    <div class="note" style="margin:2px 0 6px">${mode} · 다음 시험: 라벨 <b>${next}건</b> 도달 시 (현재 ${L.labeled || 0}건)</div>
    ${hist.length ? `<table><thead><tr><th>시험</th><th class="num">라벨</th><th class="num">사전</th><th class="num">AI 최고</th><th class="num">기준</th><th>결과</th></tr></thead><tbody>
      ${hist.map(h => `<tr><td>${esc((h.ts || '').replace('T',' ').slice(5,16))}</td><td class="num">${h.n}</td><td class="num">${fmt(h.lexicon)}%</td>
        <td class="num">${fmt(h.best_score)}% <span class="muted" style="font-size:11px">${esc(names[h.best] || '')}</span></td><td class="num">${fmt(h.threshold)}%</td>
        <td>${h.passed ? '<span class="chip pos">통과</span>' : '<span class="chip neg">미달</span>'}</td></tr>`).join('')}</tbody></table>` : ''}`;
}

// 엑셀 '이유 유형/이유 설명' 요약 + 이유에서 배운 사용자 사전
function reasonsHtml(L){
  if (D.public) return '';  // 공개용 페이지: 담당자 판단 이유는 싣지 않음
  const rs = L.reasons || [], lex = L.user_lex || {};
  if (!rs.length && !Object.keys(lex).length) return `<div class="note" style="margin-top:10px">아직 적힌 판단 이유가 없습니다. 엑셀의 '이유 유형'·'이유 설명' 칸에 적으면 여기에 모이고, 설명에 따옴표로 적은 표현은 사전에 추가됩니다.</div>`;
  const by = {};
  rs.forEach(r => { const k = r.reason_type || '(유형 없음)'; by[k] = by[k] || {긍정:0, 부정:0, 중립:0}; by[k][r.label]++; });
  const rows = Object.entries(by).sort((a, b) => (b[1]['부정'] + b[1]['긍정']) - (a[1]['부정'] + a[1]['긍정']));
  const mx = Math.max(1, ...rows.map(([, c]) => c['긍정'] + c['부정'] + c['중립']));
  const lexChips = Object.entries(lex).sort((a, b) => a[1] - b[1]).map(([t, w]) =>
    `<span class="chip ${w > 0 ? 'pos' : w < 0 ? 'neg' : 'neu'}" title="${w > 0 ? '긍정' : w < 0 ? '부정' : '판단 근거 아님'} ${w}">${esc(t)} ${w > 0 ? '+' : ''}${w}</span>`).join(' ');
  const recent = rs.slice(-8).reverse().map(r => `<li>${`<span class="chip ${r.label==='긍정'?'pos':r.label==='부정'?'neg':'neu'}">${r.label}</span>`}${r.reason_type ? `<span class="chip">${esc(r.reason_type)}</span>` : ''}${esc(r.reason || '')}${r.pred && r.pred !== r.label ? ` <span class="muted">(프로그램: ${esc(r.pred)})</span>` : ''}</li>`).join('');
  return `<h2 style="font-size:14px;margin-top:14px">판단 이유</h2>
    ${rows.map(([k, c]) => `<div class="hbar"><span>${esc(k)}</span><div class="tr" style="display:flex;gap:2px;background:none">
      <span style="width:${c['부정']/mx*100}%;background:var(--neg);border-radius:0"></span><span style="width:${c['긍정']/mx*100}%;background:var(--pos);border-radius:0"></span><span style="width:${c['중립']/mx*100}%;background:var(--neu);border-radius:0"></span></div>
      <span class="muted" style="text-align:right">부${c['부정']}·긍${c['긍정']}</span></div>`).join('')}
    ${Object.keys(lex).length ? `<div class="sub" style="margin:10px 0 4px">이유에서 배운 표현 ★ (분류에 바로 반영)</div><div>${lexChips}</div>` : ''}
    <div class="sub" style="margin:10px 0 4px">최근 적은 이유</div><ul class="t3" style="font-size:12px">${recent}</ul>`;
}

document.querySelectorAll('.btns').forEach(g => g.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  g.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
  range[g.dataset.for] = +b.dataset.r; render();
}));
let rt; addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(render, 150); });
render();
</script>
</body>
</html>
'''
