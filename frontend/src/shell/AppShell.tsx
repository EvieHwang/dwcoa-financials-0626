import { useEffect, useState } from "react";
import type { Page, Reference, Role } from "@/lib/types";
import { todayIso } from "@/lib/format";
import {
  Building2,
  Calendar,
  Coins,
  Inbox,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Moon,
  PieChart,
  Receipt,
  Sun,
  Upload,
  User,
} from "@/icons";
import { Badge, Toast, cx } from "@/primitives";
import Overview from "@/screens/Overview";
import TransactionsScreen from "@/screens/TransactionsScreen";
import DuesScreen from "@/screens/DuesScreen";
import BudgetScreen from "@/screens/BudgetScreen";
import MyAccountScreen from "@/screens/MyAccountScreen";
import ReviewQueue from "@/screens/ReviewQueue";
import RulesScreen from "@/screens/RulesScreen";
import ImportScreen from "@/screens/ImportScreen";

interface NavItem {
  page: Page;
  label: string;
  icon: typeof LayoutDashboard;
  admin: boolean;
}

const PRIMARY_NAV: NavItem[] = [
  { page: "overview", label: "Overview", icon: LayoutDashboard, admin: false },
  { page: "transactions", label: "Transactions", icon: Receipt, admin: false },
  { page: "dues", label: "Dues", icon: Coins, admin: false },
  { page: "budget", label: "Budget", icon: PieChart, admin: false },
  { page: "account", label: "My account", icon: User, admin: false },
];

const ADMIN_NAV: NavItem[] = [
  { page: "review", label: "Review queue", icon: Inbox, admin: true },
  { page: "rules", label: "Rules", icon: ListChecks, admin: true },
  { page: "import", label: "Import", icon: Upload, admin: true },
];

const PAGE_META: Record<Page, { title: string; subtitle: string }> = {
  overview: { title: "Overview", subtitle: "The association's finances at a glance" },
  transactions: { title: "Transactions", subtitle: "All posted activity" },
  dues: { title: "Dues by unit", subtitle: "Expected, paid, and outstanding" },
  budget: { title: "Budget", subtitle: "Annual plan by category" },
  account: { title: "My account", subtitle: "Your unit's statement" },
  review: { title: "Review queue", subtitle: "Categorize flagged transactions" },
  rules: { title: "Categorization rules", subtitle: "Automatic categorization" },
  import: { title: "Import CSV", subtitle: "Load the bank export" },
};

// The authenticated app shell: a fixed sidebar (grouped, role-gated navigation),
// a topbar (page title/subtitle, the single app-level shared "As of" control, and
// the theme toggle), and a content area that mounts exactly one screen at a time.
// Role flows from auth into the shell, which decides nav/control visibility — no
// component derives role from anything client-settable (visual-redesign-009).
export default function AppShell({
  role,
  onLogout,
  isDark,
  onToggleTheme,
}: {
  role: Role;
  onLogout: () => void;
  isDark: boolean;
  onToggleTheme: () => void;
}) {
  const isAdmin = role === "admin";
  const [page, setPage] = useState<Page>("overview");
  const [asOf, setAsOf] = useState<string>(() => todayIso());
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [reviewCount, setReviewCount] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [reference, setReference] = useState<Reference | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const res = await fetch("/api/reference", { credentials: "include" });
      if (!res.ok) return;
      const data = (await res.json()) as Reference;
      if (active) setReference(data);
    })();
    return () => {
      active = false;
    };
  }, []);

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    onLogout();
  }

  function go(next: Page) {
    setPage(next);
    setDrawerOpen(false);
  }

  function renderScreen() {
    switch (page) {
      case "overview":
        return <Overview asOf={asOf} reference={reference} />;
      case "transactions":
        return <TransactionsScreen reference={reference} />;
      case "dues":
        return <DuesScreen asOf={asOf} />;
      case "budget":
        return <BudgetScreen role={role} onToast={setToast} />;
      case "account":
        return <MyAccountScreen asOf={asOf} reference={reference} />;
      case "review":
        return isAdmin ? (
          <ReviewQueue
            reference={reference}
            onCountChange={setReviewCount}
            onToast={setToast}
          />
        ) : null;
      case "rules":
        return isAdmin ? <RulesScreen reference={reference} onToast={setToast} /> : null;
      case "import":
        return isAdmin ? <ImportScreen onToast={setToast} /> : null;
      default:
        return null;
    }
  }

  const meta = PAGE_META[page];

  const NavButton = ({ item }: { item: NavItem }) => {
    const Icon = item.icon;
    const active = page === item.page;
    return (
      <button
        type="button"
        onClick={() => go(item.page)}
        aria-current={active ? "page" : undefined}
        className={cx(
          "flex w-full items-center gap-2.5 rounded-ctrl px-2.5 py-2 text-[13.5px] transition-colors",
          active
            ? "bg-brand-soft font-semibold text-brand-ink"
            : "text-ink-2 hover:bg-surface-3 hover:text-ink",
        )}
      >
        <Icon size={18} className="shrink-0" />
        <span className="grow text-left">{item.label}</span>
        {item.page === "review" && reviewCount > 0 ? (
          <Badge tone="amber">{reviewCount}</Badge>
        ) : null}
      </button>
    );
  };

  return (
    <div className="min-h-screen text-ink">
      {/* Sidebar */}
      <aside
        className={cx(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-surface px-3.5 py-4 transition-transform lg:translate-x-0",
          drawerOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center gap-2.5 px-1.5 pb-4">
          <span
            className="flex h-9 w-9 items-center justify-center rounded-[9px] text-white"
            style={{ background: "linear-gradient(135deg, #168A57, #0C402B)" }}
          >
            <Building2 size={18} />
          </span>
          <div className="leading-tight">
            <div className="text-[15px] font-bold text-ink">DWCOA</div>
            <div className="text-[11px] text-ink-3">Financials</div>
          </div>
        </div>

        <nav aria-label="Primary" className="flex flex-1 flex-col gap-1 overflow-y-auto">
          <div className="px-2 pb-1 pt-2 text-[10.5px] font-bold uppercase tracking-[0.09em] text-ink-3">
            Finances
          </div>
          {PRIMARY_NAV.map((item) => (
            <NavButton key={item.page} item={item} />
          ))}

          {isAdmin && (
            <div data-testid="admin-only" className="mt-2 flex flex-col gap-1">
              <div className="px-2 pb-1 pt-2 text-[10.5px] font-bold uppercase tracking-[0.09em] text-ink-3">
                Treasurer
              </div>
              {ADMIN_NAV.map((item) => (
                <NavButton key={item.page} item={item} />
              ))}
            </div>
          )}
        </nav>

        <div className="mt-2 flex items-center gap-2.5 border-t border-hairline px-1.5 pt-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-pill bg-surface-3 text-[12px] font-bold text-ink-2">
            {isAdmin ? "TR" : "HO"}
          </span>
          <div className="grow leading-tight">
            <div className="text-[12.5px] font-semibold text-ink">
              {isAdmin ? "Treasurer" : "Homeowner"}
            </div>
            <div className="text-[11px] text-ink-3">
              {isAdmin ? "Admin access" : "View only"}
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            aria-label="Log out"
            className="flex h-8 w-8 items-center justify-center rounded-ctrl text-ink-3 hover:bg-surface-3 hover:text-ink"
          >
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {drawerOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          role="presentation"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* Main column */}
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex items-center gap-3 border-b border-border bg-bg/80 px-5 py-3.5 backdrop-blur lg:px-7">
          <button
            type="button"
            aria-label="Open navigation menu"
            onClick={() => setDrawerOpen((o) => !o)}
            className="flex h-9 w-9 items-center justify-center rounded-ctrl text-ink-2 hover:bg-surface-3 lg:hidden"
          >
            <Menu size={18} />
          </button>

          <div className="min-w-0 grow">
            <h1 className="text-[18px] font-bold tracking-[-0.02em] text-ink">
              {meta.title}
            </h1>
            <p className="truncate text-[12.5px] font-medium text-ink-2">
              {meta.subtitle}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 rounded-ctrl border border-border-2 bg-surface px-2.5 py-1.5">
              <Calendar size={15} className="text-ink-3" />
              <label htmlFor="shell-as-of" className="text-[12px] font-medium text-ink-2">
                As of
              </label>
              <input
                id="shell-as-of"
                type="date"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
                className="bg-transparent text-[12.5px] text-ink outline-none tnum"
              />
            </div>

            <button
              type="button"
              onClick={onToggleTheme}
              aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
              className="flex h-9 w-9 items-center justify-center rounded-ctrl border border-border-2 bg-surface text-ink-2 hover:bg-surface-3"
            >
              {isDark ? <Sun size={16} /> : <Moon size={16} />}
            </button>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1280px] px-5 py-6 lg:px-7">
          {renderScreen()}
        </main>
      </div>

      <Toast message={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
