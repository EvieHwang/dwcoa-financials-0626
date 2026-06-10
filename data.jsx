// data.jsx — DWCOA mock financial data + format helpers. Exported to window.DW
// Amounts are stored in whole dollars for readability; helpers format to USD.

// ---------- format helpers ----------
const usd = (n, opts = {}) => {
  const { cents = true, sign = false } = opts;
  if (n === null || n === undefined || n === '') return '—';
  const v = Number(n);
  const s = v.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 });
  return sign && v > 0 ? '+' + s : s;
};
const usd0 = (n) => usd(n, { cents: false });
const compact = (n) => {
  const a = Math.abs(n);
  if (a >= 1000) return '$' + (n / 1000).toFixed(a >= 10000 ? 0 : 1) + 'k';
  return '$' + n.toFixed(0);
};
const pct = (n, d = 1) => (n).toFixed(d) + '%';
const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const fmtDate = (iso) => {
  const [y,m,d] = iso.split('-').map(Number);
  return `${MONTHS[m-1]} ${d}, ${y}`;
};
const fmtDateShort = (iso) => { const [y,m,d] = iso.split('-').map(Number); return `${MONTHS[m-1]} ${d}`; };

// ---------- the association ----------
const YEAR = 2026;
const AS_OF = '2026-06-09';
const dayOfYear = (() => { const d = new Date('2026-06-09'); const s = new Date('2026-01-01'); return Math.round((d-s)/864e5)+1; })(); // 160
const PRO = dayOfYear / 365; // proration factor ≈ 0.438
const MONTHS_ELAPSED = 6; // Jan–Jun billed

// 9 units, ownership in per-mille (sums to 1000)
const UNITS = [
  { number: '101', mille: 96 },
  { number: '102', mille: 102 },
  { number: '103', mille: 110 },
  { number: '201', mille: 108 },
  { number: '202', mille: 112 },
  { number: '203', mille: 120 },
  { number: '301', mille: 116 },
  { number: '302', mille: 118 },
  { number: '303', mille: 118 },
];

const ACCOUNTS = [
  { name: 'Operating Checking', mask: '4021', bank: 'Sound Community Bank', balance: 38420.55, begin: 24110.00, kind: 'checking' },
  { name: 'Reserve Savings',    mask: '8807', bank: 'Sound Community Bank', balance: 112640.18, begin: 98200.00, kind: 'savings' },
  { name: 'Money Market',       mask: '2293', bank: 'Sound Community Bank', balance: 26015.00, begin: 25000.00, kind: 'mm' },
];
const TOTAL_CASH = ACCOUNTS.reduce((s,a)=>s+a.balance,0);
const TOTAL_BEGIN = ACCOUNTS.reduce((s,a)=>s+a.begin,0);

// ---------- budget categories ----------
const ANNUAL_DUES = 96000;
const incomeCats = [
  { id: 1, name: 'Homeowner Dues', icon: 'coins', annual: 96000, actual: 48000, timing: 'Monthly' },
  { id: 2, name: 'Interest Income', icon: 'percent', annual: 1800, actual: 842, timing: 'Monthly' },
  { id: 3, name: 'Late Fees', icon: 'alert', annual: 400, actual: 150, timing: 'As incurred' },
];
const expenseCats = [
  { id: 10, name: 'Master Insurance', icon: 'umbrella', annual: 21600, actual: 10800, timing: 'Quarterly' },
  { id: 11, name: 'Water & Sewer', icon: 'drop', annual: 9600, actual: 4180, timing: 'Monthly' },
  { id: 12, name: 'Electricity — Common', icon: 'bolt', annual: 3000, actual: 1290, timing: 'Monthly' },
  { id: 13, name: 'Natural Gas', icon: 'flame', annual: 2400, actual: 1340, timing: 'Monthly' },
  { id: 14, name: 'Landscaping & Grounds', icon: 'leaf', annual: 7200, actual: 3000, timing: 'Monthly' },
  { id: 15, name: 'Janitorial', icon: 'sparkle', annual: 4800, actual: 2000, timing: 'Monthly' },
  { id: 16, name: 'Repairs & Maintenance', icon: 'wrench', annual: 8400, actual: 5120, timing: 'As incurred' },
  { id: 17, name: 'Elevator Service', icon: 'building', annual: 3600, actual: 1500, timing: 'Monthly' },
  { id: 18, name: 'Management Fee', icon: 'briefcase', annual: 7200, actual: 3600, timing: 'Monthly' },
  { id: 19, name: 'Trash & Recycling', icon: 'truck', annual: 3000, actual: 1250, timing: 'Monthly' },
  { id: 20, name: 'Professional & Legal', icon: 'shield', annual: 2000, actual: 450, timing: 'As incurred' },
  { id: 21, name: 'Reserve Contribution', icon: 'bank', annual: 18000, actual: 9000, timing: 'Monthly' },
  { id: 22, name: 'Bank & Admin Fees', icon: 'receipt', annual: 600, actual: 268, timing: 'Monthly' },
];
const allCats = [...incomeCats, ...expenseCats];

function summarize(cats) {
  const rows = cats.map(c => {
    const prorated = c.annual * PRO;
    return { ...c, annual_budget: c.annual, prorated_budget: prorated, remaining: c.annual - c.actual };
  });
  const annual = rows.reduce((s,r)=>s+r.annual_budget,0);
  const prorated = rows.reduce((s,r)=>s+r.prorated_budget,0);
  const actual = rows.reduce((s,r)=>s+r.actual,0);
  return { annual_budget: annual, prorated_budget: prorated, actual, remaining: annual-actual, categories: rows };
}
const incomeSummary = summarize(incomeCats);
const expenseSummary = summarize(expenseCats);

const RESERVE = {
  budget: 18000 * PRO, contributions: 9000, expenses: 2360, net: 9000 - 2360,
  beginning_balance: 98200, current: 112640.18,
};

// monthly income vs expense (actuals Jan–Jun, lighter projection after)
const monthlyCashflow = [
  { m: 'Jan', income: 8120, expenses: 7240 },
  { m: 'Feb', income: 8000, expenses: 6980 },
  { m: 'Mar', income: 8240, expenses: 8610 },
  { m: 'Apr', income: 8000, expenses: 7120 },
  { m: 'May', income: 8160, expenses: 7460 },
  { m: 'Jun', income: 8080, expenses: 6890 },
  { m: 'Jul', income: 0, expenses: 0 },
  { m: 'Aug', income: 0, expenses: 0 },
  { m: 'Sep', income: 0, expenses: 0 },
  { m: 'Oct', income: 0, expenses: 0 },
  { m: 'Nov', income: 0, expenses: 0 },
  { m: 'Dec', income: 0, expenses: 0 },
];

// ---------- per-unit dues ----------
// carryover (prior balance), annual dues by ownership, paid YTD, outstanding
const carryovers = { '101': 0, '102': 0, '103': 220, '201': 0, '202': 0, '203': -180, '301': 0, '302': 480, '303': 0 };
const paidPattern = { // fraction of expected-to-date actually paid
  '101': 1, '102': 1, '103': 0.83, '201': 1, '202': 1, '203': 1, '301': 1, '302': 0.6, '303': 1,
};
function buildDues() {
  const units = UNITS.map(u => {
    const annual = ANNUAL_DUES * u.mille / 1000;
    const monthly = annual / 12;
    const carry = carryovers[u.number] || 0;
    const expectedToDate = monthly * MONTHS_ELAPSED + carry;
    const paid = Math.round((monthly * MONTHS_ELAPSED) * (paidPattern[u.number] ?? 1));
    const outstanding = expectedToDate - paid;
    return {
      unit: u.number, mille: u.mille, monthly,
      carryover: carry, annual_dues: annual,
      expected_total: expectedToDate, paid, outstanding,
    };
  });
  const totals = units.reduce((t,u) => ({
    carryover: t.carryover + u.carryover, annual_dues: t.annual_dues + u.annual_dues,
    expected_total: t.expected_total + u.expected_total, paid: t.paid + u.paid, outstanding: t.outstanding + u.outstanding,
  }), { carryover:0, annual_dues:0, expected_total:0, paid:0, outstanding:0 });
  return { units, totals };
}
const DUES = buildDues();

// per-unit account statement detail (My Account)
function accountFor(unitNo) {
  const u = DUES.units.find(x => x.unit === unitNo);
  if (!u) return null;
  const monthsRemaining = 12 - MONTHS_ELAPSED;
  const totalDue = u.annual_dues + u.carryover;
  const paidYtd = u.paid;
  const remaining = totalDue - paidYtd;
  let status = 'owes';
  if (remaining <= 0 && u.carryover < 0) status = 'credit';
  else if (remaining <= 0) status = 'paid_in_full';
  const suggested = remaining > 0 ? remaining / monthsRemaining : null;
  // recent payments (last 3 months)
  const recents = [];
  const base = ['2026-06-02','2026-05-01','2026-04-01'];
  base.forEach((d,i) => { if (paidPattern[unitNo] >= 1 || i > 0) recents.push({ date: d, amount: u.monthly }); });
  return {
    unit: unitNo, mille: u.mille, monthly: u.monthly,
    carryover: u.carryover, annual_dues: u.annual_dues, total_due: totalDue,
    paid_ytd: paidYtd, remaining_balance: remaining,
    standard_monthly: u.monthly, months_remaining: monthsRemaining, suggested_monthly: suggested,
    status, recent_payments: recents,
  };
}

// ---------- transactions ----------
let _tid = 1000;
const T = (post_date, account, desc, debit, credit, balance, category, status='Posted') =>
  ({ id: ++_tid, post_date, account_name: account, account_mask: ACCOUNTS.find(a=>a.name===account)?.mask, description: desc, debit, credit, balance, category, status });

const TXNS = [
  T('2026-06-08','Operating Checking','PUGET SOUND ENERGY  AUTOPAY', 412.18, null, 38420.55, 'Natural Gas'),
  T('2026-06-05','Operating Checking','SEATTLE PUBLIC UTIL  BILLPAY', 698.40, null, 38832.73, 'Water & Sewer'),
  T('2026-06-03','Operating Checking','MOBILE DEPOSIT — UNIT 202 DUES', null, 1075.20, 39531.13, 'Homeowner Dues'),
  T('2026-06-02','Operating Checking','MOBILE DEPOSIT — UNIT 101 DUES', null, 921.60, 38455.93, 'Homeowner Dues'),
  T('2026-06-02','Operating Checking','GREENSCAPE NW LLC  INV 4821', 600.00, null, 37534.33, 'Landscaping & Grounds'),
  T('2026-06-01','Operating Checking','PAYPAL *PRIORITYWASTE', 250.00, null, 38134.33, null, 'Posted'),
  T('2026-05-30','Operating Checking','OTIS ELEVATOR CO  SVC AGRMT', 300.00, null, 38384.33, 'Elevator Service'),
  T('2026-05-28','Operating Checking','CHECK 1048', 1420.00, null, 38684.33, 'Repairs & Maintenance'),
  T('2026-05-27','Operating Checking','ABM JANITORIAL SVCS', 400.00, null, 40104.33, 'Janitorial'),
  T('2026-05-22','Operating Checking','SQ *NORTHWEST GLASS REPAIR', 845.00, null, 40504.33, null, 'Posted'),
  T('2026-05-20','Operating Checking','MOBILE DEPOSIT — UNIT 303 DUES', null, 1132.80, 41349.33, 'Homeowner Dues'),
  T('2026-05-18','Operating Checking','COMCAST BUSINESS  9821', 189.00, null, 40216.53, null, 'Posted'),
  T('2026-05-15','Operating Checking','XFER TO RESERVE SAVINGS', 1500.00, null, 40405.53, 'Reserve Contribution'),
  T('2026-05-12','Operating Checking','STATE FARM — MASTER POLICY', 1800.00, null, 41905.53, 'Master Insurance'),
  T('2026-05-10','Operating Checking','PINNACLE MGMT  MGMT FEE MAY', 600.00, null, 43705.53, 'Management Fee'),
  T('2026-05-05','Operating Checking','MOBILE DEPOSIT — UNIT 201 DUES', null, 1036.80, 44305.53, 'Homeowner Dues'),
  T('2026-05-03','Operating Checking','SEATTLE CITY LIGHT  COMMON', 214.60, null, 43268.73, 'Electricity — Common'),
  T('2026-05-01','Operating Checking','MONTHLY SERVICE CHARGE', 18.00, null, 43483.33, 'Bank & Admin Fees'),
  T('2026-04-30','Reserve Savings','INTEREST PAYMENT', null, 142.30, 112640.18, 'Interest Income'),
  T('2026-04-28','Operating Checking','XFER TO RESERVE SAVINGS', 1500.00, null, 43501.33, 'Reserve Contribution'),
  T('2026-04-26','Operating Checking','ROTO-ROOTER PLUMBING', 1280.00, null, 45001.33, 'Repairs & Maintenance'),
  T('2026-04-20','Operating Checking','MOBILE DEPOSIT — UNIT 302 DUES', null, 680.00, 46281.33, 'Homeowner Dues'),
  T('2026-04-15','Operating Checking','AMZN MKTP — SUPPLIES', 78.42, null, 45601.33, null, 'Posted'),
  T('2026-04-12','Operating Checking','STATE FARM — MASTER POLICY', 1800.00, null, 45679.75, 'Master Insurance'),
  T('2026-04-10','Operating Checking','PINNACLE MGMT  MGMT FEE APR', 600.00, null, 47479.75, 'Management Fee'),
  T('2026-04-05','Operating Checking','GREENSCAPE NW LLC  INV 4760', 600.00, null, 48079.75, 'Landscaping & Grounds'),
  T('2026-04-02','Operating Checking','SEATTLE PUBLIC UTIL  BILLPAY', 712.10, null, 48679.75, 'Water & Sewer'),
  T('2026-03-31','Money Market','INTEREST PAYMENT', null, 21.50, 26015.00, 'Interest Income'),
  T('2026-03-28','Operating Checking','CINTAS FIRE PROTECTION', 415.00, null, 49391.85, null, 'Posted'),
  T('2026-03-22','Operating Checking','CHECK 1045  ARBORIST', 950.00, null, 49806.85, 'Landscaping & Grounds'),
  T('2026-03-15','Operating Checking','PUGET SOUND ENERGY  AUTOPAY', 388.74, null, 50756.85, 'Natural Gas'),
  T('2026-03-10','Operating Checking','PINNACLE MGMT  MGMT FEE MAR', 600.00, null, 51145.59, 'Management Fee'),
  T('2026-03-05','Operating Checking','MOBILE DEPOSIT — UNIT 203 DUES', null, 1152.00, 51745.59, 'Homeowner Dues'),
  T('2026-02-27','Operating Checking','ABM JANITORIAL SVCS', 400.00, null, 50593.59, 'Janitorial'),
  T('2026-02-14','Operating Checking','LATE FEE — UNIT 302', null, 25.00, 50993.59, 'Late Fees'),
  T('2026-02-10','Operating Checking','WA STATE DEPT REVENUE', 90.00, null, 50968.59, null, 'Posted'),
  T('2026-01-31','Reserve Savings','INTEREST PAYMENT', null, 138.90, 99200.00, 'Interest Income'),
  T('2026-01-15','Operating Checking','XFER TO RESERVE SAVINGS', 1500.00, null, 51058.59, 'Reserve Contribution'),
  T('2026-01-12','Operating Checking','ROOF PRO NW — INSPECTION', 1850.00, null, 52558.59, 'Repairs & Maintenance'),
  T('2026-01-05','Operating Checking','MOBILE DEPOSIT — UNIT 102 DUES', null, 979.20, 54408.59, 'Homeowner Dues'),
];

const REVIEW = TXNS.filter(t => !t.category);

// ---------- categorization rules ----------
const RULES = [
  { id: 1, pattern: 'PUGET SOUND ENERGY', category: 'Natural Gas', account: 'Operating Checking', amount_min: null, amount_max: null, priority: 10, confidence: 0.98, active: true },
  { id: 2, pattern: 'SEATTLE PUBLIC UTIL', category: 'Water & Sewer', account: null, amount_min: null, amount_max: null, priority: 10, confidence: 0.97, active: true },
  { id: 3, pattern: 'STATE FARM', category: 'Master Insurance', account: null, amount_min: null, amount_max: null, priority: 20, confidence: 0.99, active: true },
  { id: 4, pattern: 'MOBILE DEPOSIT — UNIT', category: 'Homeowner Dues', account: null, amount_min: null, amount_max: null, priority: 30, confidence: 0.95, active: true },
  { id: 5, pattern: 'PINNACLE MGMT', category: 'Management Fee', account: null, amount_min: null, amount_max: null, priority: 10, confidence: 0.99, active: true },
  { id: 6, pattern: 'GREENSCAPE', category: 'Landscaping & Grounds', account: null, amount_min: null, amount_max: null, priority: 10, confidence: 0.96, active: true },
  { id: 7, pattern: 'XFER TO RESERVE', category: 'Reserve Contribution', account: null, amount_min: null, amount_max: null, priority: 10, confidence: 1.0, active: true },
  { id: 8, pattern: 'INTEREST PAYMENT', category: 'Interest Income', account: null, amount_min: null, amount_max: null, priority: 10, confidence: 0.99, active: true },
  { id: 9, pattern: 'ABM JANITORIAL', category: 'Janitorial', account: null, amount_min: null, amount_max: null, priority: 10, confidence: 0.97, active: false },
];

const categoryNames = allCats.map(c => c.name);

window.DW = {
  usd, usd0, compact, pct, fmtDate, fmtDateShort, MONTHS,
  YEAR, AS_OF, PRO, MONTHS_ELAPSED, dayOfYear,
  UNITS, ACCOUNTS, TOTAL_CASH, TOTAL_BEGIN,
  incomeCats, expenseCats, allCats, incomeSummary, expenseSummary,
  RESERVE, monthlyCashflow, DUES, accountFor,
  TXNS, REVIEW, RULES, categoryNames, ANNUAL_DUES,
};
