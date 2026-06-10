// charts.jsx — SVG chart + small UI primitives. Exported to window.
const { useState, useRef, useEffect } = React;
const II = (name, props) => { const C = window.Icon[name]; return C ? <C {...props} /> : null; };

// ---------- Delta pill ----------
function Delta({ value, suffix = '%', invert = false }) {
  const up = value > 0, flat = value === 0;
  const good = invert ? !up : up;
  const cls = flat ? 'flat' : good ? 'up' : 'down';
  return (
    <span className={`delta ${cls}`}>
      {!flat && II(up ? 'up' : 'down', {})}
      {value > 0 ? '+' : ''}{value}{suffix}
    </span>
  );
}

// ---------- Meter ----------
function Meter({ value, max = 100, tone = 'brand', thin = false, animate = true }) {
  const pctv = Math.max(0, Math.min(100, (value / max) * 100));
  const over = value > max;
  const color = tone === 'over' || over ? 'var(--neg)'
    : tone === 'pos' ? 'var(--pos)' : tone === 'amber' ? 'var(--amber)'
    : tone === 'info' ? 'var(--info)' : 'var(--brand)';
  return (
    <div className={`meter ${thin ? 'thin' : ''}`}>
      <i style={{ width: `${Math.min(100,pctv)}%`, background: color, transition: 'width .6s cubic-bezier(.2,.8,.2,1)' }} />
    </div>
  );
}

// ---------- Progress ring (donut) ----------
function Ring({ value, max = 100, size = 132, stroke = 12, tone = 'brand', children, track }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pctv = Math.max(0, Math.min(1, value / max));
  const color = tone === 'pos' ? 'var(--pos)' : tone === 'amber' ? 'var(--amber)' : tone === 'info' ? 'var(--info)' : 'var(--brand)';
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={track || 'var(--surface-3)'} strokeWidth={stroke} />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - pctv)}
          style={{ transition: 'stroke-dashoffset 1s cubic-bezier(.2,.8,.2,1)' }} />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', textAlign: 'center' }}>{children}</div>
    </div>
  );
}

// ---------- Grouped bar chart: income vs expense ----------
function BarChart({ data, height = 220, format = (v)=>v }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(...data.flatMap(d => [d.income, d.expenses]), 1);
  const niceMax = Math.ceil(max / 2000) * 2000;
  const pad = { t: 12, r: 8, b: 26, l: 44 };
  const W = 720, H = height;
  const iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
  const n = data.length;
  const groupW = iw / n;
  const barW = Math.min(13, groupW / 3.2);
  const gap = 4;
  const y = (v) => pad.t + ih - (v / niceMax) * ih;
  const ticks = 4;
  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block', overflow: 'visible' }}>
        {Array.from({ length: ticks + 1 }).map((_, i) => {
          const v = (niceMax / ticks) * i; const yy = y(v);
          return (<g key={i}>
            <line x1={pad.l} x2={W - pad.r} y1={yy} y2={yy} stroke="var(--hairline)" strokeWidth="1" />
            <text x={pad.l - 8} y={yy + 3.5} textAnchor="end" fontSize="9.5" fill="var(--ink-3)" className="tnum">{window.DW.compact(v)}</text>
          </g>);
        })}
        {data.map((d, i) => {
          const gx = pad.l + groupW * i + groupW / 2;
          const active = hover === i;
          const empty = d.income === 0 && d.expenses === 0;
          return (
            <g key={i} onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)}>
              <rect x={pad.l + groupW * i} y={pad.t} width={groupW} height={ih} fill={active ? 'var(--surface-3)' : 'transparent'} rx="5" style={{ transition: 'fill .12s' }} />
              {!empty && <>
                <rect x={gx - barW - gap/2} y={y(d.income)} width={barW} height={Math.max(0, pad.t + ih - y(d.income))} rx="3"
                  fill="var(--brand)" opacity={active ? 1 : .92} style={{ transition: 'opacity .12s' }} />
                <rect x={gx + gap/2} y={y(d.expenses)} width={barW} height={Math.max(0, pad.t + ih - y(d.expenses))} rx="3"
                  fill="var(--ink-3)" opacity={active ? 1 : .55} style={{ transition: 'opacity .12s' }} />
              </>}
              <text x={gx} y={H - 9} textAnchor="middle" fontSize="9.5" fontWeight={active ? 700 : 500} fill={active ? 'var(--ink)' : 'var(--ink-3)'}>{d.m}</text>
            </g>
          );
        })}
      </svg>
      {hover !== null && (data[hover].income || data[hover].expenses) ? (
        <div style={{ position: 'absolute', top: 4, right: 4, background: 'var(--ink)', color: 'var(--ink-inv)', borderRadius: 10, padding: '8px 11px', fontSize: 12, boxShadow: 'var(--shadow-md)', pointerEvents: 'none' }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>{data[hover].m} {window.DW.YEAR}</div>
          <div className="row gap-2" style={{ justifyContent: 'space-between' }}><span style={{ color: 'var(--green-300)' }}>● Income</span><b className="tnum">{format(data[hover].income)}</b></div>
          <div className="row gap-2" style={{ justifyContent: 'space-between' }}><span style={{ opacity: .6 }}>● Expense</span><b className="tnum">{format(data[hover].expenses)}</b></div>
        </div>
      ) : null}
    </div>
  );
}

// ---------- Stacked horizontal bar (dues collection) ----------
function StackBar({ segments, height = 12 }) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  return (
    <div style={{ display: 'flex', height, borderRadius: 999, overflow: 'hidden', background: 'var(--surface-3)' }}>
      {segments.map((s, i) => (
        <div key={i} title={`${s.label}: ${window.DW.usd(s.value)}`}
          style={{ width: `${(s.value/total)*100}%`, background: s.color, transition: 'width .7s cubic-bezier(.2,.8,.2,1)' }} />
      ))}
    </div>
  );
}

// ---------- Legend ----------
function Legend({ items }) {
  return (
    <div className="row gap-4" style={{ flexWrap: 'wrap' }}>
      {items.map((it, i) => (
        <span key={i} className="row gap-2" style={{ fontSize: 12, color: 'var(--ink-2)', fontWeight: 500 }}>
          <span style={{ width: 9, height: 9, borderRadius: 3, background: it.color }} />{it.label}
        </span>
      ))}
    </div>
  );
}

// ---------- Stat card ----------
function StatCard({ icon, iconTone = 'brand', label, value, sub, delta, big }) {
  const toneBg = { brand: 'var(--brand-soft)', pos: 'var(--pos-soft)', info: 'var(--info-soft)', amber: 'var(--amber-soft)', neutral: 'var(--surface-3)' }[iconTone];
  const toneFg = { brand: 'var(--brand)', pos: 'var(--pos)', info: 'var(--info)', amber: 'var(--amber)', neutral: 'var(--ink-2)' }[iconTone];
  return (
    <div className="card stat">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <span className="label">{icon && <span className="stat-ico" style={{ background: toneBg, color: toneFg }}>{II(icon, {})}</span>}{label}</span>
        {delta !== undefined && delta}
      </div>
      <div className={`value tnum ${big ? 'lg' : ''}`} style={{ marginTop: icon ? 14 : 8 }}>{value}</div>
      {sub && <div className="meta">{sub}</div>}
    </div>
  );
}

Object.assign(window, { Delta, Meter, Ring, BarChart, StackBar, Legend, StatCard, II });
