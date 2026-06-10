// screens-finance.jsx — Overview, Dues by unit, My Account. Exported to window.
const { useState: useStateF, useMemo: useMemoF } = React;

function CardHead({ title, sub, children, icon }) {
  return (
    <div className="card-head">
      <div>
        <h3>{title}</h3>
        {sub && <div className="sub">{sub}</div>}
      </div>
      {children && <div className="head-actions">{children}</div>}
    </div>
  );
}

// ---- budget vs actual card (income or expense) ----
function BudgetVsActual({ title, summary, tone, kind }) {
  const D = window.DW;
  const totalPct = summary.annual_budget ? (summary.actual / summary.annual_budget) * 100 : 0;
  return (
    <div className="card">
      <CardHead title={title} sub={`${D.usd0(summary.actual)} of ${D.usd0(summary.annual_budget)} annual · ${D.pct(totalPct,0)}`}>
        <span className="badge neutral">YTD</span>
      </CardHead>
      <div className="card-pad" style={{ display: 'flex', flexDirection: 'column', gap: 15 }}>
        {summary.categories.map((c, i) => {
          const overPace = kind === 'expense' && c.actual > c.prorated_budget * 1.08;
          return (
            <div key={c.id}>
              <div className="row" style={{ justifyContent: 'space-between', marginBottom: 6, gap: 12 }}>
                <span className="row gap-2" style={{ fontSize: 13, fontWeight: 500, minWidth: 0, flex: '1 1 auto' }}>
                  <span style={{ color: 'var(--ink-3)', display: 'inline-flex', flex: 'none' }}>{II(c.icon, { width: 15, height: 15 })}</span>
                  <span style={{ whiteSpace: 'nowrap' }}>{c.name}</span>
                  {overPace && <span className="badge amber" style={{ fontSize: 10.5, padding: '1px 7px', flex: 'none' }}>over pace</span>}
                </span>
                <span className="tnum nowrap" style={{ fontSize: 13, flex: 'none' }}>
                  <b>{D.usd0(c.actual)}</b>
                  <span className="faint"> / {D.usd0(c.annual_budget)}</span>
                </span>
              </div>
              <div style={{ position: 'relative' }}>
                <Meter value={c.actual} max={c.annual_budget} tone={overPace ? 'amber' : tone} thin />
                {/* pace marker */}
                <span title="Budget pace to date" style={{ position: 'absolute', top: -3, left: `${Math.min(100,(c.prorated_budget/c.annual_budget)*100)}%`, width: 2, height: 12, background: 'var(--ink-3)', borderRadius: 2, transform: 'translateX(-50%)' }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Overview({ go, role }) {
  const D = window.DW;
  const cashDelta = +(((D.TOTAL_CASH - D.TOTAL_BEGIN) / D.TOTAL_BEGIN) * 100).toFixed(1);
  const reserveDelta = +(((D.RESERVE.current - D.RESERVE.beginning_balance) / D.RESERVE.beginning_balance) * 100).toFixed(1);
  const ytdIncome = D.incomeSummary.actual, ytdExpense = D.expenseSummary.actual;
  const ytdNet = ytdIncome - ytdExpense;
  const collected = D.DUES.totals.paid, outstanding = D.DUES.totals.outstanding;
  const collRate = (collected / (collected + outstanding)) * 100;
  const unitsBehind = D.DUES.units.filter(u => u.outstanding > 1).length;

  return (
    <div className="content" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      {/* KPI row */}
      <div className="grid kpi">
        <StatCard icon="wallet" iconTone="brand" label="Total cash on hand" big
          value={D.usd(D.TOTAL_CASH)}
          delta={<Delta value={cashDelta} />}
          sub={<><span className="faint">across 3 accounts</span></>} />
        <StatCard icon="bank" iconTone="info" label="Reserve fund"
          value={D.usd(D.RESERVE.current)}
          delta={<Delta value={reserveDelta} />}
          sub={<span className="faint">{D.pct((D.RESERVE.current/D.TOTAL_CASH)*100,0)} of total cash</span>} />
        <StatCard icon="trend" iconTone={ytdNet>=0?'pos':'amber'} label="Net income YTD"
          value={D.usd(ytdNet)}
          sub={<><span className="badge green" style={{fontSize:10.5}}>{D.usd0(ytdIncome)} in</span><span className="badge red" style={{fontSize:10.5}}>{D.usd0(ytdExpense)} out</span></>} />
        <StatCard icon="coins" iconTone={unitsBehind?'amber':'pos'} label="Dues collected YTD"
          value={D.usd(collected)}
          sub={<span className="faint">{D.pct(collRate,0)} of expected · {unitsBehind} unit{unitsBehind!==1?'s':''} behind</span>} />
      </div>

      {/* cashflow + reserve */}
      <div className="grid" style={{ gridTemplateColumns: '1.9fr 1fr' }}>
        <div className="card">
          <CardHead title="Cash flow" sub={`Monthly income vs. expense · ${D.YEAR}`}>
            <Legend items={[{ color: 'var(--brand)', label: 'Income' }, { color: 'var(--ink-3)', label: 'Expense' }]} />
          </CardHead>
          <div className="card-pad"><BarChart data={D.monthlyCashflow} format={(v)=>D.usd0(v)} /></div>
        </div>
        <div className="card">
          <CardHead title="Reserve fund" sub={`${D.YEAR} contributions`} />
          <div className="card-pad col gap-4" style={{ alignItems: 'center' }}>
            <Ring value={D.RESERVE.contributions} max={18000} tone="info" size={150} stroke={13}>
              <div>
                <div className="tnum" style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-.02em' }}>{D.pct((D.RESERVE.contributions/18000)*100,0)}</div>
                <div className="faint" style={{ fontSize: 11.5, marginTop: 2 }}>of annual plan</div>
              </div>
            </Ring>
            <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
              {[['Contributed', D.RESERVE.contributions, 'var(--info)'],['Reserve spend', -D.RESERVE.expenses, 'var(--neg)'],['Net to reserve', D.RESERVE.net, 'var(--ink)']].map(([l,v,c],i)=>(
                <div key={i} className="row" style={{ justifyContent: 'space-between', padding: '9px 0', borderTop: i?'1px solid var(--hairline)':'none' }}>
                  <span className="muted" style={{ fontSize: 12.5 }}>{l}</span>
                  <span className="tnum" style={{ fontSize: 13.5, fontWeight: i===2?700:600, color: c }}>{v<0?'−':''}{D.usd(Math.abs(v))}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* budget vs actual */}
      <div className="grid c2">
        <BudgetVsActual title="Income" summary={D.incomeSummary} tone="pos" kind="income" />
        <BudgetVsActual title="Operating expenses" summary={D.expenseSummary} tone="brand" kind="expense" />
      </div>

      {/* accounts + dues snapshot */}
      <div className="grid c2">
        <div className="card">
          <CardHead title="Account balances" sub={`as of ${D.fmtDate(D.AS_OF)}`}>
            <button className="btn ghost sm" onClick={()=>go('transactions')}>View transactions {II('chevR',{width:14,height:14})}</button>
          </CardHead>
          <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>Account</th><th className="num">Beginning</th><th className="num">Current</th><th className="num">Change</th></tr></thead>
              <tbody>
                {D.ACCOUNTS.map(a => {
                  const ch = a.balance - a.begin;
                  return (
                    <tr key={a.name}>
                      <td>
                        <div className="row gap-3">
                          <span className="stat-ico" style={{ background:'var(--brand-soft)', color:'var(--brand)', width:30, height:30 }}>{II(a.kind==='checking'?'wallet':a.kind==='savings'?'bank':'coins',{width:15,height:15})}</span>
                          <div><div style={{ fontWeight:600, fontSize:13 }}>{a.name}</div><div className="cell-mono">••{a.mask}</div></div>
                        </div>
                      </td>
                      <td className="num muted">{D.usd(a.begin)}</td>
                      <td className="num strong">{D.usd(a.balance)}</td>
                      <td className={`num ${ch>=0?'pos':'neg'}`} style={{fontWeight:600}}>{ch>=0?'+':'−'}{D.usd(Math.abs(ch))}</td>
                    </tr>
                  );
                })}
                <tr className="total-row"><td>Total cash</td><td className="num">{D.usd(D.TOTAL_BEGIN)}</td><td className="num">{D.usd(D.TOTAL_CASH)}</td><td className="num pos">+{D.usd(D.TOTAL_CASH-D.TOTAL_BEGIN)}</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <CardHead title="Dues collection" sub={`${D.MONTHS_ELAPSED} months billed · ${D.YEAR}`}>
            <button className="btn ghost sm" onClick={()=>go('dues')}>By unit {II('chevR',{width:14,height:14})}</button>
          </CardHead>
          <div className="card-pad col gap-5">
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div>
                <div className="faint" style={{ fontSize: 12, fontWeight: 600 }}>Collected of expected</div>
                <div className="tnum" style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-.02em', marginTop: 4 }}>{D.usd0(collected)}</div>
              </div>
              <span className={`badge ${unitsBehind?'amber':'green'}`} style={{ fontSize: 12 }}>{D.pct(collRate,0)} collected</span>
            </div>
            <StackBar segments={[{ label:'Paid', value: collected, color:'var(--brand)' },{ label:'Outstanding', value: Math.max(0,outstanding), color:'var(--amber)' }]} height={14} />
            <div className="row gap-4" style={{ fontSize: 12.5 }}>
              <span className="row gap-2"><span style={{width:9,height:9,borderRadius:3,background:'var(--brand)'}}/>Paid <b className="tnum">{D.usd0(collected)}</b></span>
              <span className="row gap-2"><span style={{width:9,height:9,borderRadius:3,background:'var(--amber)'}}/>Outstanding <b className="tnum">{D.usd0(outstanding)}</b></span>
            </div>
            <hr className="divider" />
            <div className="col gap-2">
              {D.DUES.units.filter(u=>u.outstanding>1).slice(0,3).map(u=>(
                <div key={u.unit} className="row" style={{ justifyContent:'space-between', fontSize:13 }}>
                  <span className="row gap-2"><span className="badge neutral mono" style={{fontSize:11}}>Unit {u.unit}</span></span>
                  <span className="tnum" style={{ color:'var(--amber)', fontWeight:600 }}>{D.usd(u.outstanding)} due</span>
                </div>
              ))}
              {unitsBehind===0 && <div className="row gap-2 muted" style={{fontSize:13}}>{II('checkCircle',{width:16,height:16})} All units current</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- Dues by unit ----------
function DuesPage() {
  const D = window.DW;
  const t = D.DUES.totals;
  const collRate = (t.paid / t.expected_total) * 100;
  return (
    <div className="content" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div className="grid c3">
        <StatCard icon="coins" iconTone="brand" label="Expected to date" value={D.usd(t.expected_total)} sub={<span className="faint">{D.MONTHS_ELAPSED} of 12 months billed</span>} />
        <StatCard icon="checkCircle" iconTone="pos" label="Collected" value={D.usd(t.paid)} sub={<span className="badge green" style={{fontSize:10.5}}>{D.pct(collRate,0)} of expected</span>} />
        <StatCard icon="alert" iconTone={t.outstanding>0?'amber':'pos'} label="Outstanding" value={D.usd(t.outstanding)} sub={<span className="faint">{D.DUES.units.filter(u=>u.outstanding>1).length} units behind</span>} />
      </div>
      <div className="card">
        <CardHead title="Dues by unit" sub={`Operating budget ${D.usd0(D.ANNUAL_DUES)} · allocated by ownership`} />
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr>
              <th>Unit</th><th className="num">Ownership</th><th className="num">Monthly</th><th className="num">Carryover</th><th className="num">Expected</th><th className="num">Paid</th><th className="num">Outstanding</th><th>Status</th>
            </tr></thead>
            <tbody>
              {D.DUES.units.map(u => {
                const behind = u.outstanding > 1;
                const credit = u.outstanding < -1;
                return (
                  <tr key={u.unit}>
                    <td><span style={{ fontWeight:700 }}>Unit {u.unit}</span></td>
                    <td className="num muted">{D.pct(u.mille/10)}</td>
                    <td className="num">{D.usd(u.monthly)}</td>
                    <td className={`num ${u.carryover<0?'pos':u.carryover>0?'neg':'muted'}`}>{u.carryover?(u.carryover<0?'−':'')+D.usd(Math.abs(u.carryover)):'—'}</td>
                    <td className="num">{D.usd(u.expected_total)}</td>
                    <td className="num">{D.usd(u.paid)}</td>
                    <td className={`num strong ${behind?'neg':''}`}>{D.usd(u.outstanding)}</td>
                    <td>{behind ? <span className="badge amber"><span className="dot"/>Behind</span> : credit ? <span className="badge info"><span className="dot"/>Credit</span> : <span className="badge green"><span className="dot"/>Current</span>}</td>
                  </tr>
                );
              })}
              <tr className="total-row">
                <td>9 units</td><td className="num">100.0%</td><td className="num">{D.usd(t.expected_total/D.MONTHS_ELAPSED)}</td>
                <td className="num">{t.carryover?D.usd(t.carryover):'—'}</td><td className="num">{D.usd(t.expected_total)}</td><td className="num">{D.usd(t.paid)}</td><td className="num">{D.usd(t.outstanding)}</td><td></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ---------- My Account ----------
function MyAccount() {
  const D = window.DW;
  const [unit, setUnit] = useStateF(() => localStorage.getItem('dwcoa.my-unit') || '202');
  const acct = useMemoF(() => D.accountFor(unit), [unit]);
  function pick(u){ setUnit(u); if(u) localStorage.setItem('dwcoa.my-unit', u); }
  const statusBadge = {
    owes: <span className="badge amber"><span className="dot"/>Balance due</span>,
    paid_in_full: <span className="badge green"><span className="dot"/>Paid in full</span>,
    credit: <span className="badge info"><span className="dot"/>Credit on account</span>,
  }[acct.status];
  return (
    <div className="content" style={{ maxWidth: 940, display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div className="card">
        <div className="card-pad row" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
          <div className="row gap-3">
            <span className="stat-ico" style={{ width: 44, height: 44, borderRadius: 13, background: 'var(--brand-soft)', color: 'var(--brand)' }}>{II('user',{width:22,height:22})}</span>
            <div>
              <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-.01em' }}>Unit {unit} statement</div>
              <div className="muted" style={{ fontSize: 12.5 }}>{D.pct(acct.mille/10)} ownership · as of {D.fmtDate(D.AS_OF)}</div>
            </div>
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>Viewing unit</label>
            <select className="select" value={unit} onChange={e=>pick(e.target.value)}>
              {D.UNITS.map(u => <option key={u.number} value={u.number}>Unit {u.number}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div className="grid c2">
        {/* This year */}
        <div className="card">
          <CardHead title={`This year (${D.YEAR})`}>{statusBadge}</CardHead>
          <div className="card-pad col">
            {[['Balance carried over', acct.carryover, acct.carryover<0],
              ['Annual dues', acct.annual_dues],
              ['Total due', acct.total_due, false, true],
              ['Paid year-to-date', -acct.paid_ytd, true]].map(([l,v,green,strong],i)=>(
              <div key={i} className="row" style={{ justifyContent:'space-between', padding:'11px 0', borderBottom: i<3?'1px solid var(--hairline)':'none' }}>
                <span className={strong?'':'muted'} style={{ fontSize:13.5, fontWeight: strong?700:500 }}>{l}</span>
                <span className={`tnum ${green?'pos':''}`} style={{ fontSize:14, fontWeight: strong?700:600 }}>{v<0?'−':''}{D.usd(Math.abs(v))}</span>
              </div>
            ))}
            <div className="row" style={{ justifyContent:'space-between', alignItems:'center', marginTop:14, padding:'16px', background:'var(--inset)', borderRadius:'var(--r-ctrl)' }}>
              <span style={{ fontSize:14, fontWeight:700 }}>Remaining balance</span>
              <span className="tnum" style={{ fontSize:22, fontWeight:700, color: acct.remaining_balance>0?'var(--amber)':'var(--pos)', letterSpacing:'-.02em' }}>{acct.remaining_balance<0?'−':''}{D.usd(Math.abs(acct.remaining_balance))}</span>
            </div>
          </div>
        </div>

        {/* Payment guidance + recent */}
        <div className="col gap-4">
          <div className="card">
            <CardHead title="Payment guidance" />
            <div className="card-pad col gap-3">
              <div className="row" style={{ justifyContent:'space-between' }}>
                <span className="muted" style={{ fontSize:13.5 }}>Standard monthly</span>
                <span className="tnum" style={{ fontSize:15, fontWeight:700 }}>{D.usd(acct.standard_monthly)}</span>
              </div>
              {acct.status==='owes' && acct.suggested_monthly ? (
                <div className="row" style={{ justifyContent:'space-between', alignItems:'center', padding:'13px 15px', background:'var(--brand-soft)', borderRadius:'var(--r-ctrl)' }}>
                  <span style={{ fontSize:13, color:'var(--brand-ink)', fontWeight:600, maxWidth:170 }}>Pay this monthly to stay current through Dec</span>
                  <span className="tnum" style={{ fontSize:19, fontWeight:700, color:'var(--brand-ink)' }}>{D.usd(acct.suggested_monthly)}</span>
                </div>
              ) : (
                <div className="row gap-2" style={{ padding:'13px 15px', background:'var(--pos-soft)', borderRadius:'var(--r-ctrl)', color:'var(--pos)', fontSize:13, fontWeight:600 }}>
                  {II('checkCircle',{width:18,height:18})} {acct.status==='credit'?'You have a credit on your account.':"You're paid in full for this year."}
                </div>
              )}
              <div className="faint" style={{ fontSize:12 }}>{acct.months_remaining} months remaining in {D.YEAR}.</div>
            </div>
          </div>
          <div className="card">
            <CardHead title="Recent payments" />
            <div className="card-pad col gap-1">
              {acct.recent_payments.length===0 ? <div className="muted" style={{fontSize:13}}>No recent payments.</div> :
                acct.recent_payments.map((p,i)=>(
                  <div key={i} className="row" style={{ justifyContent:'space-between', padding:'9px 0', borderBottom: i<acct.recent_payments.length-1?'1px solid var(--hairline)':'none' }}>
                    <span className="row gap-2" style={{ fontSize:13 }}><span className="stat-ico" style={{width:26,height:26,background:'var(--pos-soft)',color:'var(--pos)'}}>{II('check',{width:14,height:14})}</span>{D.fmtDate(p.date)}</span>
                    <span className="tnum pos" style={{ fontWeight:600 }}>+{D.usd(p.amount)}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Overview, DuesPage, MyAccount, CardHead, BudgetVsActual });
