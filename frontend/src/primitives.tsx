import {
  type ButtonHTMLAttributes,
  type ReactNode,
  useEffect,
} from "react";
import { X } from "@/icons";

// Small classNames helper.
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

// ---- Card -----------------------------------------------------------------
export function Card({
  children,
  className,
  ...rest
}: { children: ReactNode; className?: string } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cx(
        "rounded-card border border-border bg-surface shadow-sm",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

export function CardHead({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-hairline px-[22px] py-[18px]">
      <div className="min-w-0">
        <h3 className="text-[14px] font-bold tracking-[-0.01em] text-ink">{title}</h3>
        {subtitle ? (
          <p className="mt-0.5 text-[12.5px] font-medium text-ink-2">{subtitle}</p>
        ) : null}
      </div>
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function CardBody({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cx("px-[22px] py-[18px]", className)}>{children}</div>;
}

// ---- StatCard -------------------------------------------------------------
export function StatCard({
  label,
  value,
  sub,
  icon,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  icon?: ReactNode;
  tone?: "default" | "pos" | "neg" | "amber" | "info";
}) {
  const toneRing: Record<string, string> = {
    default: "text-brand bg-brand-soft",
    pos: "text-pos bg-pos-soft",
    neg: "text-neg bg-neg-soft",
    amber: "text-amber bg-amber-soft",
    info: "text-info bg-info-soft",
  };
  return (
    <Card className="p-[22px]">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-[0.05em] text-ink-3">
          {label}
        </span>
        {icon ? (
          <span
            className={cx(
              "flex h-7 w-7 items-center justify-center rounded-ctrl",
              toneRing[tone],
            )}
            aria-hidden="true"
          >
            {icon}
          </span>
        ) : null}
      </div>
      <div className="tnum mt-2 text-[30px] font-bold leading-none tracking-[-0.025em] text-ink">
        {value}
      </div>
      {sub ? <div className="mt-2 text-[12.5px] text-ink-2">{sub}</div> : null}
    </Card>
  );
}

// ---- Badge ----------------------------------------------------------------
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "brand" | "pos" | "neg" | "amber" | "info";
}) {
  const tones: Record<string, string> = {
    neutral: "bg-surface-3 text-ink-2",
    brand: "bg-brand-soft text-brand-ink",
    pos: "bg-pos-soft text-pos",
    neg: "bg-neg-soft text-neg",
    amber: "bg-amber-soft text-amber",
    info: "bg-info-soft text-info",
  };
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1 rounded-pill px-2 py-0.5 text-[11.5px] font-semibold",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

// ---- Button ---------------------------------------------------------------
type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
};

export function Button({
  variant = "secondary",
  size = "md",
  className,
  type = "button",
  children,
  ...rest
}: ButtonProps) {
  const variants: Record<string, string> = {
    primary:
      "bg-brand text-on-brand border border-transparent hover:opacity-90 disabled:opacity-50",
    secondary:
      "bg-surface text-ink border border-border-2 hover:bg-surface-3 disabled:opacity-50",
    ghost: "bg-transparent text-ink-2 border border-transparent hover:bg-surface-3",
    danger:
      "bg-surface text-neg border border-border-2 hover:bg-neg-soft disabled:opacity-50",
  };
  const sizes: Record<string, string> = {
    sm: "h-8 px-3 text-[12.5px]",
    md: "h-10 px-4 text-[13.5px]",
  };
  return (
    <button
      type={type}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded-ctrl font-semibold transition-colors",
        variants[variant],
        sizes[size],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}

// ---- Table ----------------------------------------------------------------
export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full border-collapse text-[13px]">{children}</table>
    </div>
  );
}

export function Th({
  children,
  align = "left",
}: {
  children: ReactNode;
  align?: "left" | "right";
}) {
  return (
    <th
      scope="col"
      className={cx(
        "border-b border-border px-3 py-2 text-[11px] font-bold uppercase tracking-[0.05em] text-ink-3",
        align === "right" ? "text-right" : "text-left",
      )}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  align = "left",
  className,
}: {
  children: ReactNode;
  align?: "left" | "right";
  className?: string;
}) {
  return (
    <td
      className={cx(
        "border-b border-hairline px-3 py-2.5 text-ink",
        align === "right" ? "text-right tnum" : "text-left",
        className,
      )}
    >
      {children}
    </td>
  );
}

// ---- Meter (horizontal progress with an optional pace marker) -------------
// Resting state shows the final fill — width is the value, never gated behind
// an entrance animation (reduced-motion safe).
export function Meter({
  value,
  max,
  marker,
  tone = "brand",
}: {
  value: number;
  max: number;
  marker?: number; // 0..1 pace marker position
  tone?: "brand" | "amber" | "pos";
}) {
  const pct = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;
  const fill: Record<string, string> = {
    brand: "bg-brand",
    amber: "bg-amber",
    pos: "bg-pos",
  };
  return (
    <div className="relative h-2 w-full overflow-hidden rounded-pill bg-surface-3">
      <div
        className={cx("h-full rounded-pill transition-[width] duration-700", fill[tone])}
        style={{ width: `${pct * 100}%` }}
      />
      {marker !== undefined && marker >= 0 && marker <= 1 ? (
        <span
          aria-hidden="true"
          className="absolute top-0 h-full w-0.5 bg-ink-3"
          style={{ left: `${Math.min(1, marker) * 100}%` }}
        />
      ) : null}
    </div>
  );
}

// ---- Ring (donut progress) ------------------------------------------------
export function Ring({
  value,
  max,
  label,
}: {
  value: number;
  max: number;
  label?: ReactNode;
}) {
  const pct = max > 0 ? Math.min(1, Math.max(0, value / max)) : 0;
  const r = 52;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - pct);
  return (
    <div className="relative inline-flex h-[132px] w-[132px] items-center justify-center">
      <svg width="132" height="132" viewBox="0 0 132 132" className="-rotate-90">
        <circle
          cx="66"
          cy="66"
          r={r}
          fill="none"
          stroke="var(--surface-3)"
          strokeWidth="12"
        />
        <circle
          cx="66"
          cy="66"
          r={r}
          fill="none"
          stroke="var(--brand)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className="transition-[stroke-dashoffset] duration-700"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="tnum text-[22px] font-bold text-ink">
          {Math.round(pct * 100)}%
        </span>
        {label ? <span className="text-[11px] text-ink-3">{label}</span> : null}
      </div>
    </div>
  );
}

// ---- BarChart (grouped income vs expense by month) ------------------------
// Each month renders its income/expense values as accessible (sr-only) text so
// the data is present at rest even with motion disabled.
export function BarChart({
  data,
  format,
}: {
  data: Array<{ month: number; income: number; expenses: number }>;
  format: (cents: number) => string;
}) {
  const max = Math.max(1, ...data.map((d) => Math.max(d.income, d.expenses)));
  const monthName = (m: number) =>
    [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ][(m - 1) % 12] ?? String(m);
  return (
    <div className="flex h-44 items-end gap-2">
      {data.map((d) => (
        <div key={d.month} className="flex flex-1 flex-col items-center gap-1">
          <div className="flex h-36 w-full items-end justify-center gap-1">
            <div
              className="w-1/2 rounded-t bg-brand transition-[height] duration-700"
              style={{ height: `${(d.income / max) * 100}%` }}
              title={`${monthName(d.month)} income ${format(d.income)}`}
            />
            <div
              className="w-1/2 rounded-t bg-ink-3/60 transition-[height] duration-700"
              style={{ height: `${(d.expenses / max) * 100}%` }}
              title={`${monthName(d.month)} expense ${format(d.expenses)}`}
            />
          </div>
          <span className="text-[10.5px] text-ink-3">{monthName(d.month)}</span>
          <span className="sr-only tnum">
            {monthName(d.month)}: income {format(d.income)}, expense{" "}
            {format(d.expenses)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ---- StackBar (paid vs outstanding) ---------------------------------------
export function StackBar({
  paid,
  outstanding,
}: {
  paid: number;
  outstanding: number;
}) {
  const total = paid + outstanding;
  const paidPct = total > 0 ? (paid / total) * 100 : 0;
  return (
    <div className="flex h-3 w-full overflow-hidden rounded-pill bg-surface-3">
      <div className="h-full bg-brand" style={{ width: `${paidPct}%` }} />
      <div className="h-full bg-amber" style={{ width: `${100 - paidPct}%` }} />
    </div>
  );
}

// ---- Modal ----------------------------------------------------------------
export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="w-full max-w-[440px] rounded-card border border-border bg-surface shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-hairline px-[22px] py-[16px]">
          <h2 className="text-[15px] font-bold text-ink">{title}</h2>
          <Button variant="ghost" size="sm" aria-label="Close dialog" onClick={onClose}>
            <X size={16} />
          </Button>
        </div>
        <div className="px-[22px] py-[18px]">{children}</div>
      </div>
    </div>
  );
}

// ---- Toast ----------------------------------------------------------------
export function Toast({
  message,
  onDismiss,
}: {
  message: string | null;
  onDismiss: () => void;
}) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onDismiss, 2600);
    return () => clearTimeout(t);
  }, [message, onDismiss]);
  if (!message) return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center">
      <div
        role="status"
        className="pointer-events-auto rounded-pill bg-ink px-4 py-2 text-[13px] font-medium text-bg shadow-lg"
      >
        {message}
      </div>
    </div>
  );
}
