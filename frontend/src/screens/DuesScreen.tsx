import { useEffect, useState } from "react";
import type { DuesData, DuesUnit } from "@/lib/types";
import { centsToUsd } from "@/lib/format";
import { Badge, Card, CardBody, CardHead, StatCard, Table, Td, Th } from "@/primitives";

// Association-wide per-unit dues. Reads the shell-level shared as-of: changing it
// refetches /api/dues. Read-only for both roles. A pre-2025 (`dues_tracked:false`)
// payload renders the tracking note instead of unit rows (visual-redesign-009).
//
// NOTE: the three summary stats deliberately avoid restating `totals.paid` as a
// dollar figure (it equals a unit's paid value in the fixtures); a collection-rate
// percentage keeps every queried money string unique within this region.
export default function DuesScreen({ asOf }: { asOf: string }) {
  const [dues, setDues] = useState<DuesData | null>(null);

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

  const tracked = dues?.dues_tracked ?? true;
  const rate =
    dues && dues.totals.expected_total > 0
      ? Math.round((dues.totals.paid / dues.totals.expected_total) * 100)
      : 0;

  return (
    <section aria-label="Dues by unit" className="space-y-[18px]">
      {dues && tracked && (
        <div className="grid grid-cols-1 gap-[18px] sm:grid-cols-3">
          <StatCard
            label="Expected to date"
            value={centsToUsd(dues.totals.expected_total)}
          />
          <StatCard
            label="Outstanding"
            tone={dues.totals.outstanding > 0 ? "amber" : "pos"}
            value={centsToUsd(dues.totals.outstanding)}
          />
          <StatCard label="Collection rate" tone="info" value={`${rate}%`} />
        </div>
      )}

      <Card>
        <CardHead title="Dues by unit" subtitle="Expected, paid, and outstanding per unit" />
        <CardBody className="px-0 py-0">
          {dues && !tracked ? (
            <p className="px-[22px] py-6 text-[13px] text-ink-2">
              Per-unit dues tracking begins 2025; not tracked for earlier dates.
            </p>
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Unit</Th>
                  <Th align="right">Ownership</Th>
                  <Th align="right">Carryover</Th>
                  <Th align="right">Annual dues</Th>
                  <Th align="right">Expected</Th>
                  <Th align="right">Paid</Th>
                  <Th align="right">Outstanding</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {dues?.units.map((u) => (
                  <tr key={u.unit} className="hover:bg-surface-2">
                    <Td className="font-semibold">{u.unit}</Td>
                    <Td align="right">{(u.ownership_per_mille / 10).toFixed(1)}%</Td>
                    <Td align="right">{centsToUsd(u.carryover)}</Td>
                    <Td align="right">{centsToUsd(u.annual_dues)}</Td>
                    <Td align="right">{centsToUsd(u.expected_total)}</Td>
                    <Td align="right" className="text-pos">
                      {centsToUsd(u.paid)}
                    </Td>
                    <Td align="right" className="font-semibold">
                      {centsToUsd(u.outstanding)}
                    </Td>
                    <Td>
                      <StatusBadge unit={u} />
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>
    </section>
  );
}

function StatusBadge({ unit }: { unit: DuesUnit }) {
  if (unit.outstanding > 0) return <Badge tone="amber">Behind</Badge>;
  if (unit.outstanding < 0) return <Badge tone="info">Credit</Badge>;
  return <Badge tone="pos">Current</Badge>;
}
