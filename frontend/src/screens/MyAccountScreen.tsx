import { useEffect, useState } from "react";
import type { AccountData, PaymentGuidance, Reference } from "@/lib/types";
import { centsToUsd } from "@/lib/format";
import { CheckCircle2, User } from "@/icons";
import { Badge, Card, CardBody, CardHead } from "@/primitives";

// localStorage key for the homeowner's self-selected unit (a convenience, not an
// authorization boundary — remembered across visits).
const MY_ACCOUNT_UNIT_KEY = "dwcoa.my-account.unit";

const GUIDANCE_NOTE: Record<PaymentGuidance["status"], string> = {
  owes: "",
  paid_in_full: "You're paid in full for this year.",
  credit: "You have a credit on your account.",
  due_by_year_end: "The remaining balance is due by December 31.",
};

// The per-unit homeowner statement. A homeowner self-selects their unit
// (persisted in localStorage); until then a prompt shows and no /api/account
// call is made. Reads the shell-level shared as-of; selecting a unit fetches
// GET /api/account?unit=<n>&as_of=<asOf>. Read-only for both roles; a not-tracked
// (pre-2025) payload renders a note (visual-redesign-009 US-5).
export default function MyAccountScreen({
  asOf,
  reference,
}: {
  asOf: string;
  reference: Reference | null;
}) {
  const [unit, setUnit] = useState<string>(
    () => localStorage.getItem(MY_ACCOUNT_UNIT_KEY) ?? "",
  );
  const [data, setData] = useState<AccountData | null>(null);

  useEffect(() => {
    if (!unit) {
      setData(null);
      return;
    }
    let active = true;
    void (async () => {
      const res = await fetch(
        `/api/account?unit=${encodeURIComponent(unit)}&as_of=${asOf}`,
        { credentials: "include" },
      );
      if (!res.ok) {
        if (active) setData(null);
        return;
      }
      const body = (await res.json()) as AccountData;
      if (active) setData(body);
    })();
    return () => {
      active = false;
    };
  }, [unit, asOf]);

  function handleSelect(value: string) {
    setUnit(value);
    if (value) localStorage.setItem(MY_ACCOUNT_UNIT_KEY, value);
    else localStorage.removeItem(MY_ACCOUNT_UNIT_KEY);
  }

  const units = reference?.units ?? [];

  // Render nothing until the unit list has loaded, so the selector always has its
  // options the moment the region appears (matches the prior embedded behavior).
  if (units.length === 0) return null;

  const cy = data?.current_year;
  const guidance = data?.payment_guidance;
  const owesStatus = guidance?.status;
  const statusBadge =
    owesStatus === "paid_in_full" ? (
      <Badge tone="pos">Paid in full</Badge>
    ) : owesStatus === "credit" ? (
      <Badge tone="info">Credit</Badge>
    ) : cy ? (
      <Badge tone="amber">Balance due</Badge>
    ) : null;

  return (
    <section aria-label="My account" className="space-y-[18px]">
      <Card>
        <CardHead
          title={
            <span className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-pill bg-brand-soft text-brand-ink">
                <User size={15} />
              </span>
              {unit ? `Unit ${unit} statement` : "Your statement"}
            </span>
          }
          subtitle={
            data
              ? `${(data.ownership_per_mille / 10).toFixed(1)}% ownership · as of ${data.as_of_date}`
              : "Your unit's dues statement"
          }
          actions={
            <div className="flex items-center gap-2">
              <label htmlFor="my-account-unit" className="text-[12.5px] text-ink-2">
                Your unit
              </label>
              <select
                id="my-account-unit"
                value={unit}
                onChange={(e) => handleSelect(e.target.value)}
                className="h-9 rounded-ctrl border border-border-2 bg-surface px-2 text-[13px] text-ink"
              >
                <option value="">Choose a unit…</option>
                {units.map((u) => (
                  <option key={u.number} value={u.number}>
                    {u.number}
                  </option>
                ))}
              </select>
            </div>
          }
        />
        <CardBody>
          {!unit && (
            <p className="text-[13px] text-ink-2">
              Select your unit to view your statement.
            </p>
          )}

          {unit && data && !data.dues_tracked && (
            <p className="text-[13px] text-ink-2">
              Per-unit dues tracking begins 2025; not tracked for earlier dates.
            </p>
          )}

          {unit && data && data.dues_tracked && cy && guidance && (
            <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-2">
              <section aria-label="This year" className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-[13px] font-bold text-ink">
                    This year ({cy.year})
                  </h4>
                  {statusBadge}
                </div>
                <dl className="space-y-1.5 text-[13px]">
                  <Row label="Balance carried over" value={centsToUsd(cy.carryover)} />
                  <Row label="Annual dues" value={centsToUsd(cy.annual_dues)} />
                  <Row label="Total due" value={centsToUsd(cy.total_due)} bold />
                </dl>
                <div className="rounded-ctrl bg-inset px-4 py-3">
                  <div className="text-[11px] font-bold uppercase tracking-[0.05em] text-ink-3">
                    Remaining balance
                  </div>
                  <div
                    className={`tnum mt-1 text-[22px] font-bold ${
                      cy.remaining_balance > 0 ? "text-amber" : "text-pos"
                    }`}
                  >
                    {centsToUsd(cy.remaining_balance)}
                  </div>
                </div>
              </section>

              <div className="space-y-[18px]">
                <section aria-label="Payment guidance">
                  <Card>
                    <CardHead title="Payment guidance" />
                    <CardBody className="space-y-2 text-[13px]">
                      <Row
                        label="Standard monthly"
                        value={centsToUsd(guidance.standard_monthly)}
                      />
                      {guidance.status === "owes" &&
                      guidance.suggested_monthly !== null ? (
                        <div className="rounded-ctrl bg-brand-soft px-3 py-2 text-brand-ink">
                          <div className="text-[12px]">Suggested monthly to stay current</div>
                          <div className="tnum text-[16px] font-bold">
                            {centsToUsd(guidance.suggested_monthly)}
                          </div>
                        </div>
                      ) : (
                        <p className="text-ink-2">{GUIDANCE_NOTE[guidance.status]}</p>
                      )}
                      <p className="text-[12px] text-ink-3">
                        {guidance.months_remaining} months remaining
                      </p>
                    </CardBody>
                  </Card>
                </section>

                <section aria-label="Recent payments">
                  <Card>
                    <CardHead title="Recent payments" />
                    <CardBody>
                      {data.recent_payments.length === 0 ? (
                        <p className="text-[13px] text-ink-3">No recent payments.</p>
                      ) : (
                        <ul className="space-y-2">
                          {data.recent_payments.map((p, i) => (
                            <li
                              key={`${p.date}-${i}`}
                              className="flex items-center justify-between text-[13px]"
                            >
                              <span className="flex items-center gap-2 text-ink-2">
                                <CheckCircle2 size={15} className="text-pos" />
                                {p.date}
                              </span>
                              <span className="tnum font-semibold text-pos">
                                {centsToUsd(p.amount)}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </CardBody>
                  </Card>
                </section>
              </div>
            </div>
          )}
        </CardBody>
      </Card>
    </section>
  );
}

function Row({
  label,
  value,
  bold,
}: {
  label: string;
  value: string;
  bold?: boolean;
}) {
  return (
    <div className={`flex justify-between ${bold ? "font-semibold text-ink" : ""}`}>
      <dt className={bold ? "" : "text-ink-2"}>{label}</dt>
      <dd className="tnum">{value}</dd>
    </div>
  );
}
