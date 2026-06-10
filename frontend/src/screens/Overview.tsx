import { useEffect, useState } from "react";
import type { DashboardData, DuesData, Reference, Summary } from "@/lib/types";
import { centsToUsd } from "@/lib/format";
import {
  Wallet,
  Landmark,
  TrendingUp,
  Coins,
  CheckCircle2,
} from "@/icons";
import {
  BarChart,
  Card,
  CardBody,
  CardHead,
  Meter,
  Ring,
  StackBar,
  StatCard,
  Table,
  Td,
  Th,
} from "@/primitives";

// The association-level financial overview (default authenticated screen).
// Read-only for both roles. Reads the shell-level shared as-of: changing it
// refetches /api/dashboard and /api/dues with the new date — preserving the
// single-control refetch behavior the dashboard-006 suite asserts. No write
// control lives inside this region (visual-redesign-009 US-5).
export default function Overview({
  asOf,
  reference,
}: {
  asOf: string;
  reference: Reference | null;
}) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [dues, setDues] = useState<DuesData | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const res = await fetch(`/api/dashboard?as_of=${asOf}`, {
        credentials: "include",
      });
      if (!res.ok) {
        if (active) setData(null);
        return;
      }
      const body = (await res.json()) as DashboardData;
      if (active) setData(body);
    })();
    return () => {
      active = false;
    };
  }, [asOf]);

  useEffect(() => {
    let active = true;
    void (async () => {
      const res = await fetch(`/api/dues?as_of=${asOf}`, { credentials: "include" });
      if (!res.ok) {
        if (active) setDues(null);
        return;
      }
      const body = (await res.json()) as DuesData;
      if (active) setDues(body);
    })();
    return () => {
      active = false;
    };
  }, [asOf]);

  const units = reference?.units ?? [];
  const netIncome =
    data ? data.income_summary.actual - data.expense_summary.actual : null;

  return (
    <section aria-label="Financial dashboard" className="space-y-[18px]">
      {/* KPI row */}
      <div className="grid grid-cols-1 gap-[18px] sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total cash on hand"
          value={data ? centsToUsd(data.total_cash) : "—"}
          icon={<Wallet size={16} />}
          sub={data ? "Across all association accounts" : undefined}
        />
        <StatCard
          label="Reserve fund"
          tone="info"
          value={data ? centsToUsd(data.reserve_fund.beginning_balance) : "—"}
          icon={<Landmark size={16} />}
          sub={data ? "Beginning balance" : undefined}
        />
        <StatCard
          label="Net income YTD"
          tone={netIncome !== null && netIncome < 0 ? "neg" : "pos"}
          value={netIncome !== null ? centsToUsd(netIncome) : "—"}
          icon={<TrendingUp size={16} />}
          sub={data ? "Income in, expenses out" : undefined}
        />
        <StatCard
          label="Dues collected YTD"
          tone="amber"
          value={dues && dues.dues_tracked ? centsToUsd(dues.totals.paid) : "—"}
          icon={<Coins size={16} />}
          sub={dues && dues.dues_tracked ? "Of expected to date" : undefined}
        />
      </div>

      {/* Cash flow + reserve */}
      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-[1.9fr_1fr]">
        <Card>
          <CardHead title="Monthly cashflow" subtitle="Income vs. expense by month" />
          <CardBody>
            {data ? (
              <section aria-label="Monthly cashflow">
                <BarChart data={data.monthly_cashflow} format={centsToUsd} />
              </section>
            ) : (
              <p className="text-[13px] text-ink-3">No cashflow data yet.</p>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHead title="Reserve fund" />
          <CardBody>
            {data ? (
              <section aria-label="Reserve fund" className="flex flex-col items-center gap-3">
                <Ring
                  value={data.reserve_fund.contributions}
                  max={Math.max(1, data.reserve_fund.budget)}
                  label="contributed"
                />
                <dl className="w-full space-y-1.5 text-[13px]">
                  <div className="flex justify-between">
                    <dt className="text-ink-2">Budget to date</dt>
                    <dd className="tnum">{centsToUsd(data.reserve_fund.budget)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-ink-2">Contributions</dt>
                    <dd className="tnum text-pos">
                      {centsToUsd(data.reserve_fund.contributions)}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-ink-2">Reserve spend</dt>
                    <dd className="tnum text-neg">
                      {centsToUsd(data.reserve_fund.expenses)}
                    </dd>
                  </div>
                  <div className="flex justify-between font-semibold">
                    <dt>Net to reserve</dt>
                    <dd className="tnum">{centsToUsd(data.reserve_fund.net)}</dd>
                  </div>
                  <div className="flex justify-between text-ink-3">
                    <dt>Beginning balance</dt>
                    <dd className="tnum">
                      {centsToUsd(data.reserve_fund.beginning_balance)}
                    </dd>
                  </div>
                </dl>
              </section>
            ) : (
              <p className="text-[13px] text-ink-3">No reserve data yet.</p>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Budget vs actual */}
      {data && (
        <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-2">
          <SummaryCard title="Income" summary={data.income_summary} overPace={false} />
          <SummaryCard
            title="Expenses"
            summary={data.expense_summary}
            overPace={true}
          />
        </div>
      )}

      {/* Accounts + dues snapshot */}
      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-2">
        {data && (
          <Card>
            <CardHead title="Account balances" />
            <CardBody className="px-0 py-0">
              <section aria-label="Account balances">
                <Table>
                  <thead>
                    <tr>
                      <Th>Account</Th>
                      <Th align="right">Beginning</Th>
                      <Th align="right">Current</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.accounts.map((a) => (
                      <tr key={a.name}>
                        <Td>{a.name}</Td>
                        <Td align="right">{centsToUsd(a.beginning_balance)}</Td>
                        <Td align="right" className="font-semibold">
                          {centsToUsd(a.balance)}
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </section>
            </CardBody>
          </Card>
        )}

        <Card>
          <CardHead title="Dues collection" />
          <CardBody>
            {dues && dues.dues_tracked ? (
              <div className="space-y-3">
                <div className="tnum text-[24px] font-bold text-ink">
                  {centsToUsd(dues.totals.paid)}
                </div>
                <StackBar
                  paid={dues.totals.paid}
                  outstanding={dues.totals.outstanding}
                />
                <div className="flex justify-between text-[12.5px] text-ink-2">
                  <span>Collected</span>
                  <span className="tnum">
                    Outstanding {centsToUsd(dues.totals.outstanding)}
                  </span>
                </div>
                {dues.totals.outstanding === 0 ? (
                  <p className="flex items-center gap-1.5 text-[13px] text-pos">
                    <CheckCircle2 size={15} /> All units current
                  </p>
                ) : null}
              </div>
            ) : (
              <p className="text-[13px] text-ink-3">
                Dues collection appears once tracking data is available.
              </p>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Units */}
      <Card>
        <CardHead title="Units" subtitle="Ownership across the nine homes" />
        <CardBody className="px-0 py-0">
          <section aria-label="Units">
            <Table>
              <thead>
                <tr>
                  <Th>Unit</Th>
                  <Th align="right">Ownership</Th>
                </tr>
              </thead>
              <tbody>
                {units.map((u) => (
                  <tr key={u.number}>
                    <Td className="font-semibold">{u.number}</Td>
                    <Td align="right">{(u.ownership_pct * 100).toFixed(1)}%</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </section>
        </CardBody>
      </Card>
    </section>
  );
}

// One income/expense budget-vs-actual card: a row per category with a meter
// (actual / annual_budget) and a pace marker at prorated_budget / annual_budget.
// Proration is server-computed; never recomputed on the client.
function SummaryCard({
  title,
  summary,
  overPace,
}: {
  title: string;
  summary: Summary;
  overPace: boolean;
}) {
  return (
    <section aria-label={`${title} summary`}>
      <Card>
        <CardHead
          title={title}
          subtitle={`of ${centsToUsd(summary.annual_budget)} annual budget`}
        />
        <CardBody className="space-y-4">
          {summary.categories.map((line) => {
            const isOver =
              overPace && line.actual > line.prorated_budget * 1.08;
            return (
              <div key={line.category_id} className="space-y-1.5">
                <div className="flex items-baseline justify-between text-[13px]">
                  <span className="text-ink">{line.name}</span>
                  <span className="tnum">
                    <span className="font-semibold">
                      {centsToUsd(line.actual)}
                    </span>{" "}
                    <span className="text-ink-3">
                      / {centsToUsd(line.annual_budget)}
                    </span>
                  </span>
                </div>
                <Meter
                  value={line.actual}
                  max={Math.max(1, line.annual_budget)}
                  marker={
                    line.annual_budget > 0
                      ? line.prorated_budget / line.annual_budget
                      : undefined
                  }
                  tone={isOver ? "amber" : "brand"}
                />
                <div className="flex justify-between text-[11.5px] text-ink-3">
                  <span>Budget to date {centsToUsd(line.prorated_budget)}</span>
                  <span className="tnum">
                    Remaining {centsToUsd(line.remaining)}
                  </span>
                </div>
              </div>
            );
          })}
        </CardBody>
      </Card>
    </section>
  );
}
