// screens-admin.jsx — Transactions, Budget, Review, Rules, Import. Exported to window.
const { useState: useS, useMemo: useM } = React;

// ---------- Transactions ----------
function Transactions() {
  const D = window.DW;
  const [year, setYear] = useS('2026');
  const [account, setAccount] = useS('');
  const [q, setQ] = useS('');
  const [page, setPage] = useS(0);
  const per = 12;
  const filtered = useM(() => D.TXNS.filter(t => {
    if (year && !t.post_date.startsWith(year)) return false;
    if (account && t.account_name !== account) return false;
    if (q && !t.description.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  }), [year, account, q]);
  const total = filtered.length;
  const pageRows = filtered.slice(page*per, page*per+per);
  React.useEffect(()=>{ setPage(0); }, [year, account, q]);

  return (
    <div className="content wide" style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div className="card">
        <div className="card-head" style={{ flexWrap:'wrap', gap:10 }}>
          <h3>Transactions</h3>
          <div className="head-actions" style={{ flexWrap:'wrap' }}>
            <div className="row" style={{ position:'relative' }}>
              <span style={{ position:'absolute', left:11, color:'var(--ink-3)', display:'inline-flex' }}>{II('search',{width:15,height:15})}</span>
              <input className="input" style={{ paddingLeft:34, width:200, height:34 }} placeholder="Search description…" value={q} onChange={e=>setQ(e.target.value)} />
            </div>
            <select className="select" style={{ width:110, height:34 }} value={year} onChange={e=>setYear(e.target.value)}>
              <option value="">All years</option>
              {['2026','2025','2024'].map(y=><option key={y} value={y}>{y}</option>)}
            </select>
            <select className="select" style={{ width:170, height:34 }} value={account} onChange={e=>setAccount(e.target.value)}>
              <option value="">All accounts</option>
              {D.ACCOUNTS.map(a=><option key={a.name} value={a.name}>{a.name}</option>)}
            </select>
            <button className="btn sm">{II('download',{width:15,height:15})} Export</button>
          </div>
        </div>
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr>
              <th>Date</th><th>Account</th><th>Description</th><th>Category</th><th className="num">Debit</th><th className="num">Credit</th><th className="num">Balance</th>
            </tr></thead>
            <tbody>
              {pageRows.map(t => (
                <tr key={t.id}>
                  <td className="nowrap muted">{D.fmtDateShort(t.post_date)}</td>
                  <td><span className="cell-mono">••{t.account_mask}</span></td>
                  <td><span style={{ fontWeight:500 }}>{t.description}</span></td>
                  <td>{t.category ? <span className="badge neutral">{t.category}</span> : <span className="badge amber"><span className="dot"/>Needs review</span>}</td>
                  <td className="num neg">{t.debit?D.usd(t.debit):'—'}</td>
                  <td className="num pos">{t.credit?D.usd(t.credit):'—'}</td>
                  <td className="num muted">{D.usd(t.balance)}</td>
                </tr>
              ))}
              {pageRows.length===0 && <tr><td colSpan="7"><div className="empty">{II('search',{})}<div>No transactions match your filters.</div></div></td></tr>}
            </tbody>
          </table>
        </div>
        <div className="row card-pad" style={{ justifyContent:'space-between', borderTop:'1px solid var(--hairline)', paddingTop:14, paddingBottom:14 }}>
          <span className="muted" style={{ fontSize:12.5 }}>{total===0?'No transactions':`Showing ${page*per+1}–${Math.min((page+1)*per,total)} of ${total}`}</span>
          <div className="row gap-2">
            <button className="btn icon sm" disabled={page===0} onClick={()=>setPage(p=>p-1)}>{II('chevL',{width:16,height:16})}</button>
            <button className="btn icon sm" disabled={(page+1)*per>=total} onClick={()=>setPage(p=>p+1)}>{II('chevR',{width:16,height:16})}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- Budget editor ----------
function Budget({ role, notify }) {
  const D = window.DW;
  const isAdmin = role === 'admin';
  const [year, setYear] = useS(2026);
  const [locked, setLocked] = useS(false);
  const [edits, setEdits] = useS({});
  const [dirty, setDirty] = useS(false);
  const [showCopy, setShowCopy] = useS(false);

  const cats = [...D.incomeCats.map(c=>({...c,type:'Income'})), ...D.expenseCats.map(c=>({...c,type:'Expense'}))];
  const val = (c) => edits[c.id] !== undefined ? edits[c.id] : c.annual;
  const incomeTot = D.incomeCats.reduce((s,c)=>s+ (edits[c.id]!==undefined?+edits[c.id]||0:c.annual),0);
  const expenseTot = D.expenseCats.reduce((s,c)=>s+ (edits[c.id]!==undefined?+edits[c.id]||0:c.annual),0);

  function setVal(id,v){ setEdits(e=>({...e,[id]:v})); setDirty(true); }
  function save(){ setDirty(false); setEdits({}); notify('Budget saved', 'check'); }
  function toggleLock(){ setLocked(l=>!l); notify(locked?'Year unlocked — editing enabled':'Budget locked for '+year, locked?'unlock':'lock'); }

  return (
    <div className="content" style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div className="grid c3">
        <StatCard icon="coins" iconTone="pos" label="Budgeted income" value={D.usd0(incomeTot)} sub={<span className="faint">{D.incomeCats.length} categories</span>} />
        <StatCard icon="receipt" iconTone="brand" label="Budgeted expense" value={D.usd0(expenseTot)} sub={<span className="faint">{D.expenseCats.length} categories</span>} />
        <StatCard icon="trend" iconTone={incomeTot-expenseTot>=0?'pos':'amber'} label="Planned surplus" value={D.usd0(incomeTot-expenseTot)} sub={<span className="faint">{D.pct(((incomeTot-expenseTot)/incomeTot)*100,1)} of income</span>} />
      </div>
      <div className="card">
        <div className="card-head" style={{ flexWrap:'wrap', gap:10 }}>
          <div className="row gap-3">
            <h3>Annual budget</h3>
            <select className="select" style={{ width:104, height:34 }} value={year} onChange={e=>setYear(+e.target.value)}>
              {[2026,2025,2024].map(y=><option key={y} value={y}>{y}</option>)}
            </select>
            {locked && <span className="badge neutral">{II('lock',{width:12,height:12})} Locked</span>}
          </div>
          {isAdmin && (
            <div className="head-actions">
              <button className="btn sm" onClick={()=>setShowCopy(true)} disabled={locked}>{II('copy',{width:15,height:15})} Copy {year-1}</button>
              <button className={`btn sm ${locked?'':'ghost'}`} onClick={toggleLock}>{II(locked?'unlock':'lock',{width:15,height:15})} {locked?'Unlock':'Lock year'}</button>
              <button className="btn primary sm" onClick={save} disabled={locked||!dirty}>{II('check',{width:15,height:15})} Save{dirty?' changes':''}</button>
            </div>
          )}
        </div>
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr><th>Category</th><th>Type</th><th>Timing</th><th className="num">Annual budget</th>{isAdmin&&<th className="num" style={{width:160}}>Edit (USD)</th>}</tr></thead>
            <tbody>
              {cats.map(c => (
                <tr key={c.id}>
                  <td><span className="row gap-2" style={{fontWeight:500}}><span style={{color:'var(--ink-3)',display:'inline-flex'}}>{II(c.icon,{width:15,height:15})}</span>{c.name}</span></td>
                  <td><span className={`badge ${c.type==='Income'?'green':'neutral'}`} style={{fontSize:10.5}}>{c.type}</span></td>
                  <td className="muted" style={{fontSize:12.5}}>{c.timing}</td>
                  <td className="num strong">{D.usd0(+val(c)||0)}</td>
                  {isAdmin && <td className="num">
                    <div className="row" style={{ position:'relative', justifyContent:'flex-end' }}>
                      <span style={{ position:'absolute', left:10, color:'var(--ink-3)', fontSize:13 }}>$</span>
                      <input className="input tnum" type="number" step="100" disabled={locked} value={val(c)}
                        style={{ height:32, paddingLeft:20, textAlign:'right', opacity:locked?.5:1 }}
                        onChange={e=>setVal(c.id, e.target.value)} />
                    </div>
                  </td>}
                </tr>
              ))}
              <tr className="total-row"><td>Net operating budget</td><td></td><td></td><td className="num" style={{color: incomeTot-expenseTot>=0?'var(--pos)':'var(--neg)'}}>{D.usd0(incomeTot-expenseTot)}</td>{isAdmin&&<td></td>}</tr>
            </tbody>
          </table>
        </div>
      </div>

      {showCopy && (
        <div className="scrim" onClick={()=>setShowCopy(false)}>
          <div className="modal" onClick={e=>e.stopPropagation()}>
            <div className="card-pad">
              <div className="row gap-3" style={{ marginBottom:8 }}>
                <span className="stat-ico" style={{ width:38, height:38, background:'var(--amber-soft)', color:'var(--amber)' }}>{II('copy',{width:18,height:18})}</span>
                <div><div style={{fontWeight:700, fontSize:15}}>Copy {year-1} budget into {year}?</div></div>
              </div>
              <p className="muted" style={{ fontSize:13.5, lineHeight:1.5, margin:'4px 0 18px' }}>This overwrites every category amount for {year} with last year's figures. You can still edit afterward before locking.</p>
              <div className="row gap-2" style={{ justifyContent:'flex-end' }}>
                <button className="btn" onClick={()=>setShowCopy(false)}>Cancel</button>
                <button className="btn primary" onClick={()=>{ setShowCopy(false); notify(`Copied ${year-1} budget into ${year}`, 'copy'); }}>Overwrite {year}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------- Review queue ----------
function ReviewQueue({ notify }) {
  const D = window.DW;
  const [queue, setQueue] = useS(() => D.REVIEW.map(t=>({ ...t, cat: '' })));
  const [ruleFor, setRuleFor] = useS(null);
  function setCat(id, v){ setQueue(q=>q.map(t=>t.id===id?{...t,cat:v}:t)); }
  function saveFix(t){
    if(!t.cat){ notify('Pick a category first', 'alert'); return; }
    setQueue(q=>q.filter(x=>x.id!==t.id));
    notify(`Categorized as ${t.cat}`, 'check');
  }
  return (
    <div className="content" style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div className="grid c3">
        <StatCard icon="inbox" iconTone={queue.length?'amber':'pos'} label="Awaiting review" value={queue.length} sub={<span className="faint">uncategorized transactions</span>} />
        <StatCard icon="rules" iconTone="brand" label="Active rules" value={D.RULES.filter(r=>r.active).length} sub={<span className="faint">auto-categorizing imports</span>} />
        <StatCard icon="checkCircle" iconTone="pos" label="Auto-matched" value="92%" sub={<span className="faint">of this month's imports</span>} />
      </div>
      <div className="card">
        <CardHead title="Review queue" sub="Transactions no rule matched — categorize or teach a rule">
          <span className={`badge ${queue.length?'amber':'green'}`}>{queue.length} pending</span>
        </CardHead>
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr><th>Date</th><th>Description</th><th className="num">Amount</th><th style={{width:200}}>Category</th><th className="num" style={{width:200}}>Actions</th></tr></thead>
            <tbody>
              {queue.map(t => (
                <tr key={t.id}>
                  <td className="nowrap muted">{D.fmtDateShort(t.post_date)}</td>
                  <td style={{ fontWeight:500 }}>{t.description}</td>
                  <td className={`num ${t.debit?'neg':'pos'}`}>{D.usd(t.debit ?? t.credit)}</td>
                  <td>
                    <select className="select" style={{ height:32 }} value={t.cat} onChange={e=>setCat(t.id, e.target.value)}>
                      <option value="">Choose…</option>
                      {D.categoryNames.map(c=><option key={c} value={c}>{c}</option>)}
                    </select>
                  </td>
                  <td className="num">
                    <div className="row gap-2" style={{ justifyContent:'flex-end' }}>
                      <button className="btn primary sm" onClick={()=>saveFix(t)}>Save</button>
                      <button className="btn sm" onClick={()=>setRuleFor(t)}>{II('plus',{width:14,height:14})} Rule</button>
                    </div>
                  </td>
                </tr>
              ))}
              {queue.length===0 && <tr><td colSpan="5"><div className="empty">{II('checkCircle',{})}<div>Inbox zero — every transaction is categorized.</div></div></td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      {ruleFor && <RuleModal txn={ruleFor} onClose={()=>setRuleFor(null)} notify={notify} />}
    </div>
  );
}

function RuleModal({ txn, onClose, notify }) {
  const D = window.DW;
  // suggest a pattern: trim trailing tokens
  const suggest = txn.description.replace(/\s+\d.*$/,'').replace(/\s+(LLC|INV|AUTOPAY|BILLPAY).*$/i,'').trim().slice(0,28);
  const [pattern, setPattern] = useS(suggest);
  const [cat, setCat] = useS('');
  return (
    <div className="scrim" onClick={onClose}>
      <div className="modal" onClick={e=>e.stopPropagation()} style={{ maxWidth: 480 }}>
        <div className="card-head"><h3>Create categorization rule</h3><button className="btn icon sm ghost" style={{marginLeft:'auto'}} onClick={onClose}>{II('x',{width:16,height:16})}</button></div>
        <div className="card-pad col gap-4">
          <div className="muted" style={{ fontSize:12.5, padding:'10px 12px', background:'var(--inset)', borderRadius:8 }}>From: <b style={{color:'var(--ink)'}}>{txn.description}</b></div>
          <div className="field"><label>When description contains</label><input className="input mono" value={pattern} onChange={e=>setPattern(e.target.value)} /></div>
          <div className="field"><label>Categorize as</label>
            <select className="select" value={cat} onChange={e=>setCat(e.target.value)}>
              <option value="">Choose category…</option>
              {D.categoryNames.map(c=><option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="row gap-2" style={{ justifyContent:'flex-end', marginTop:4 }}>
            <button className="btn" onClick={onClose}>Cancel</button>
            <button className="btn primary" disabled={!pattern||!cat} onClick={()=>{ onClose(); notify('Rule created — re-running on imports', 'rules'); }}>Create rule</button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- Rules editor ----------
function Rules({ notify }) {
  const D = window.DW;
  const [rules, setRules] = useS(() => D.RULES.map(r=>({...r})));
  const [pattern, setPattern] = useS('');
  const [cat, setCat] = useS('');
  function create(){ if(!pattern||!cat) return;
    setRules(rs=>[{ id:Date.now(), pattern, category:cat, account:null, amount_min:null, amount_max:null, priority:10, confidence:1, active:true }, ...rs]);
    setPattern(''); setCat(''); notify('Rule created', 'rules');
  }
  function del(id){ setRules(rs=>rs.filter(r=>r.id!==id)); notify('Rule deleted', 'trash'); }
  function toggle(id){ setRules(rs=>rs.map(r=>r.id===id?{...r,active:!r.active}:r)); }
  return (
    <div className="content" style={{ display:'flex', flexDirection:'column', gap:16 }}>
      <div className="card">
        <CardHead title="New rule" sub="Patterns are matched against transaction descriptions, highest priority first" />
        <div className="card-pad row gap-3" style={{ flexWrap:'wrap', alignItems:'flex-end' }}>
          <div className="field grow" style={{ minWidth:220 }}><label>When description contains</label><input className="input mono" placeholder="e.g. PUGET SOUND ENERGY" value={pattern} onChange={e=>setPattern(e.target.value)} /></div>
          <div className="field" style={{ minWidth:200 }}><label>Categorize as</label>
            <select className="select" value={cat} onChange={e=>setCat(e.target.value)}><option value="">Choose…</option>{D.categoryNames.map(c=><option key={c} value={c}>{c}</option>)}</select>
          </div>
          <button className="btn primary" style={{height:38}} disabled={!pattern||!cat} onClick={create}>{II('plus',{width:16,height:16})} Add rule</button>
        </div>
      </div>
      <div className="card">
        <CardHead title="Categorization rules"><span className="badge neutral">{rules.filter(r=>r.active).length} active</span></CardHead>
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr><th>Pattern</th><th>Category</th><th>Conditions</th><th className="num">Priority</th><th>Active</th><th></th></tr></thead>
            <tbody>
              {rules.map(r => (
                <tr key={r.id} style={{ opacity: r.active?1:.55 }}>
                  <td><span className="cell-mono" style={{ fontSize:12.5, color:'var(--ink)' }}>{r.pattern}</span></td>
                  <td><span className="badge brand">{r.category}</span></td>
                  <td className="muted" style={{ fontSize:12 }}>{[r.account&&`acct ••${D.ACCOUNTS.find(a=>a.name===r.account)?.mask}`].filter(Boolean).join(', ')||'—'}</td>
                  <td className="num">{r.priority}</td>
                  <td>
                    <button className={`seg`} onClick={()=>toggle(r.id)} style={{ padding:2, cursor:'pointer' }} title="Toggle active">
                      <span style={{ width:32, height:18, borderRadius:999, background: r.active?'var(--brand)':'var(--border-2)', position:'relative', transition:'background .15s', display:'block' }}>
                        <span style={{ position:'absolute', top:2, left: r.active?16:2, width:14, height:14, borderRadius:999, background:'#fff', transition:'left .15s', boxShadow:'0 1px 2px rgba(0,0,0,.3)' }} />
                      </span>
                    </button>
                  </td>
                  <td className="num"><button className="btn icon sm danger" onClick={()=>del(r.id)}>{II('trash',{width:15,height:15})}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ---------- Import (CSV upload) ----------
function Import({ notify }) {
  const D = window.DW;
  const [drag, setDrag] = useS(false);
  const [file, setFile] = useS(null);
  const [summary, setSummary] = useS(null);
  const inputRef = React.useRef(null);
  function choose(f){ if(f){ setFile(f); setSummary(null); } }
  function upload(){
    if(!file) return;
    setTimeout(()=>{
      setSummary({ added: 23, skipped_duplicate: 4, unknown_account_count: 1, unknown_accounts:['••5567'], total: 28 });
      notify('Imported 23 transactions', 'check');
    }, 350);
  }
  return (
    <div className="content" style={{ maxWidth: 820, display:'flex', flexDirection:'column', gap:16 }}>
      <div className="card">
        <CardHead title="Import transactions" sub="Upload a CSV exported from online banking. Duplicates are skipped automatically." />
        <div className="card-pad col gap-4">
          <div
            onDragOver={e=>{e.preventDefault(); setDrag(true);}} onDragLeave={()=>setDrag(false)}
            onDrop={e=>{e.preventDefault(); setDrag(false); choose(e.dataTransfer.files?.[0]);}}
            onClick={()=>inputRef.current?.click()}
            style={{ border:`2px dashed ${drag?'var(--brand)':'var(--border-2)'}`, background: drag?'var(--brand-soft)':'var(--inset)', borderRadius:'var(--r-card)', padding:'40px 24px', textAlign:'center', cursor:'pointer', transition:'.15s' }}>
            <span className="stat-ico" style={{ width:48, height:48, margin:'0 auto 12px', background:'var(--surface)', color:'var(--brand)', borderRadius:14, boxShadow:'var(--shadow-sm)' }}>{II('upload',{width:24,height:24})}</span>
            <div style={{ fontWeight:700, fontSize:15 }}>{file ? file.name : 'Drop your CSV here or click to browse'}</div>
            <div className="muted" style={{ fontSize:12.5, marginTop:4 }}>{file ? `${(file.size/1024).toFixed(1)} KB · ready to import` : 'Accepts .csv up to 5 MB'}</div>
            <input ref={inputRef} type="file" accept=".csv" hidden onChange={e=>choose(e.target.files?.[0])} />
          </div>
          <div className="row gap-2" style={{ justifyContent:'flex-end' }}>
            {file && <button className="btn" onClick={()=>{setFile(null);setSummary(null);}}>Clear</button>}
            <button className="btn primary" disabled={!file} onClick={upload}>{II('upload',{width:16,height:16})} Import transactions</button>
          </div>
          {summary && (
            <div style={{ animation:'fadeUp .3s ease both', border:'1px solid var(--border)', borderRadius:'var(--r-card)', overflow:'hidden' }}>
              <div className="row gap-2 card-pad" style={{ background:'var(--pos-soft)', color:'var(--pos)', padding:'12px 18px', fontWeight:600, fontSize:13.5 }}>{II('checkCircle',{width:18,height:18})} Import complete — {summary.total} rows read</div>
              <div className="grid" style={{ gridTemplateColumns:'repeat(3,1fr)', gap:0 }}>
                {[['Added', summary.added, 'pos'],['Duplicates skipped', summary.skipped_duplicate, 'muted'],['Unknown account', summary.unknown_account_count, 'amber']].map(([l,v,c],i)=>(
                  <div key={i} style={{ padding:'18px 20px', borderRight: i<2?'1px solid var(--hairline)':'none', borderTop:'1px solid var(--hairline)' }}>
                    <div className="tnum" style={{ fontSize:26, fontWeight:700, color: c==='pos'?'var(--pos)':c==='amber'?'var(--amber)':'var(--ink)' }}>{v}</div>
                    <div className="muted" style={{ fontSize:12.5, marginTop:2 }}>{l}</div>
                  </div>
                ))}
              </div>
              {summary.unknown_accounts.length>0 && <div className="muted" style={{ fontSize:12.5, padding:'12px 20px', borderTop:'1px solid var(--hairline)' }}>Unmatched account number: <span className="mono">{summary.unknown_accounts.join(', ')}</span> — add it under Accounts to map these rows.</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Transactions, Budget, ReviewQueue, Rules, Import });
