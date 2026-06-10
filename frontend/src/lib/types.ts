// Shared domain types for the DWCOA Financials frontend. These mirror the API
// payloads exactly as they exist today — the visual redesign does not change any
// data shape (visual-redesign-009).

export type Role = "admin" | "viewer";

export interface Unit {
  number: string;
  ownership_pct: number;
}

export interface Account {
  name: string;
  masked_number?: string;
}

export interface Category {
  id?: number;
  name: string;
  type?: string;
}

export interface Reference {
  units: Unit[];
  accounts: Account[];
  categories: Category[];
}

export interface Rule {
  id: number;
  pattern: string;
  category_id: number;
  category: string | null;
  account: string | null;
  amount_min: number | null;
  amount_max: number | null;
  priority: number;
  confidence: number;
  active: number | boolean;
}

export interface Transaction {
  id: number;
  account_number: string;
  account_name: string;
  post_date: string;
  check_number: string | null;
  description: string;
  debit: number | null;
  credit: number | null;
  status: string;
  balance: number;
  category: string | null;
  needs_review?: number | boolean;
}

export interface TransactionsResponse {
  transactions: Transaction[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadSummary {
  added: number;
  skipped_duplicate: number;
  unknown_account_count: number;
  unknown_accounts: string[];
  total: number;
}

export interface BudgetLine {
  category_id: number;
  category_name: string;
  category_type: string;
  annual_amount: number;
  timing: string | null;
  category_default_timing: string;
  effective_timing: string;
}

export interface BudgetResponse {
  year: number;
  locked: boolean;
  locked_at: string | null;
  budgets: BudgetLine[];
}

export interface SummaryLine {
  category_id: number;
  name: string;
  annual_budget: number;
  prorated_budget: number;
  actual: number;
  remaining: number;
}

export interface Summary {
  annual_budget: number;
  prorated_budget: number;
  actual: number;
  remaining: number;
  categories: SummaryLine[];
}

export interface AccountBalance {
  name: string;
  balance: number;
  beginning_balance: number;
}

export interface ReserveFund {
  budget: number;
  contributions: number;
  expenses: number;
  net: number;
  beginning_balance: number;
}

export interface MonthlyCashflow {
  month: number;
  income: number;
  expenses: number;
}

export interface DashboardData {
  as_of_date: string;
  year: number;
  accounts: AccountBalance[];
  total_cash: number;
  income_summary: Summary;
  expense_summary: Summary;
  reserve_fund: ReserveFund;
  monthly_cashflow: MonthlyCashflow[];
}

export interface DuesUnit {
  unit: string;
  ownership_per_mille: number;
  carryover: number;
  annual_dues: number;
  expected_total: number;
  paid: number;
  outstanding: number;
}

export interface DuesTotals {
  carryover: number;
  annual_dues: number;
  expected_total: number;
  paid: number;
  outstanding: number;
}

export interface DuesData {
  as_of_date: string;
  year: number;
  dues_tracked: boolean;
  operating_budget: number;
  units: DuesUnit[];
  totals: DuesTotals;
}

export interface AccountCurrentYear {
  year: number;
  carryover: number;
  annual_dues: number;
  total_due: number;
  paid_ytd: number;
  remaining_balance: number;
}

export interface AccountPriorYear {
  year: number;
  data_available: boolean;
  annual_dues_budgeted: number | null;
  total_paid: number | null;
  balance_carried_forward: number;
}

export interface PaymentGuidance {
  standard_monthly: number;
  months_remaining: number;
  suggested_monthly: number | null;
  status: "owes" | "paid_in_full" | "credit" | "due_by_year_end";
}

export interface RecentPayment {
  date: string;
  amount: number;
}

export interface AccountData {
  unit: string;
  ownership_per_mille: number;
  as_of_date: string;
  year: number;
  dues_tracked: boolean;
  current_year: AccountCurrentYear | null;
  prior_year: AccountPriorYear | null;
  payment_guidance: PaymentGuidance | null;
  recent_payments: RecentPayment[];
}

export type AuthState =
  | { status: "loading" }
  | { status: "unauthenticated" }
  | { status: "authenticated"; role: Role };

// The primary navigation destinations. Exactly one screen is mounted at a time.
export type Page =
  | "overview"
  | "transactions"
  | "dues"
  | "budget"
  | "account"
  | "review"
  | "rules"
  | "import";
