import { useEffect, useState } from "react";
import type { BudgetLine, BudgetResponse, Role } from "@/lib/types";
import { centsToUsd } from "@/lib/format";
import { Copy, Lock, Unlock } from "@/icons";
import {
  Badge,
  Button,
  Card,
  CardBody,
  CardHead,
  Modal,
  StatCard,
  Table,
  Td,
  Th,
} from "@/primitives";

// The budget editor. Read-only for viewers; for admins, editable amount inputs,
// Save (per-edited-line POST in integer cents), Copy-year (409 → confirm modal →
// overwrite:true), Lock/Unlock. A locked year is not editable. Proration is
// backend-only, so this shows planned annual amounts. All fetch/handler logic is
// reused unchanged (visual-redesign-009 US-5).
export default function BudgetScreen({
  role,
  onToast,
}: {
  role: Role;
  onToast?: (msg: string) => void;
}) {
  const isAdmin = role === "admin";
  const [budgetYear] = useState(() => String(Math.max(new Date().getFullYear(), 2025)));
  const [data, setData] = useState<BudgetResponse | null>(null);
  const [edits, setEdits] = useState<Record<number, string>>({});
  const [reload, setReload] = useState(0);
  const [copyConflict, setCopyConflict] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      const res = await fetch(`/api/budgets?year=${budgetYear}`, {
        credentials: "include",
      });
      if (!res.ok) {
        if (active) setData(null);
        return;
      }
      const body = (await res.json()) as BudgetResponse;
      if (active) {
        setData(body);
        setEdits({});
      }
    })();
    return () => {
      active = false;
    };
  }, [budgetYear, reload]);

  if (!data) return null;
  const locked = data.locked;

  function effectiveCents(line: BudgetLine): number {
    const edited = edits[line.category_id];
    if (edited !== undefined && edited !== "" && !Number.isNaN(Number(edited))) {
      return Math.round(Number(edited) * 100);
    }
    return line.annual_amount;
  }

  function dollarsValue(line: BudgetLine): string {
    const edited = edits[line.category_id];
    if (edited !== undefined) return edited;
    return String(line.annual_amount / 100);
  }

  const budgetedIncome = data.budgets
    .filter((l) => l.category_type === "Income")
    .reduce((s, l) => s + effectiveCents(l), 0);
  const budgetedExpense = data.budgets
    .filter((l) => l.category_type !== "Income")
    .reduce((s, l) => s + effectiveCents(l), 0);

  async function handleSave() {
    if (!data) return;
    for (const line of data.budgets) {
      const edited = edits[line.category_id];
      if (edited === undefined) continue;
      const cents = Math.round(Number(edited) * 100);
      await fetch("/api/budgets", {
        method: "POST",
        credentials: "include",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          year: data.year,
          category_id: line.category_id,
          annual_amount: cents,
        }),
      });
    }
    setReload((t) => t + 1);
    onToast?.("Budget saved");
  }

  async function postCopy(overwrite: boolean) {
    if (!data) return null;
    return fetch("/api/budgets/copy", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        from_year: data.year - 1,
        to_year: data.year,
        ...(overwrite ? { overwrite: true } : {}),
      }),
    });
  }

  async function handleCopy() {
    const res = await postCopy(false);
    if (!res) return;
    if (res.status === 409) {
      setCopyConflict(true);
      return;
    }
    setCopyConflict(false);
    if (res.ok) {
      setReload((t) => t + 1);
      onToast?.("Budget copied");
    }
  }

  async function handleCopyConfirm() {
    await postCopy(true);
    setCopyConflict(false);
    setReload((t) => t + 1);
    onToast?.("Budget copied");
  }

  async function handleLock() {
    if (!data) return;
    await fetch("/api/budgets/lock", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ year: data.year, locked: !data.locked }),
    });
    setReload((t) => t + 1);
    onToast?.(data.locked ? "Year unlocked" : "Year locked");
  }

  return (
    <section aria-label="Budget" className="space-y-[18px]">
      <div className="grid grid-cols-1 gap-[18px] sm:grid-cols-3">
        <StatCard label="Budgeted income" tone="pos" value={centsToUsd(budgetedIncome)} />
        <StatCard
          label="Budgeted expense"
          tone="neg"
          value={centsToUsd(budgetedExpense)}
        />
        <StatCard
          label="Planned surplus"
          value={centsToUsd(budgetedIncome - budgetedExpense)}
        />
      </div>

      <Card>
        <CardHead
          title={`Annual budget ${data.year}`}
          actions={
            <div className="flex items-center gap-2">
              {locked && <Badge tone="amber">Locked</Badge>}
              {isAdmin && (
                <>
                  <Button size="sm" onClick={handleCopy} disabled={locked}>
                    <Copy size={14} /> Copy {data.year - 1}
                  </Button>
                  <Button size="sm" onClick={handleLock}>
                    {locked ? <Unlock size={14} /> : <Lock size={14} />}
                    {locked ? "Unlock year" : "Lock year"}
                  </Button>
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={handleSave}
                    disabled={locked}
                  >
                    Save changes
                  </Button>
                </>
              )}
            </div>
          }
        />
        <CardBody className="px-0 py-0">
          <Table>
            <thead>
              <tr>
                <Th>Category</Th>
                <Th>Type</Th>
                <Th>Timing</Th>
                <Th align="right">Annual budget</Th>
                {isAdmin && <Th align="right">Edit (USD)</Th>}
              </tr>
            </thead>
            <tbody>
              {data.budgets.map((line) => (
                <tr key={line.category_id} className="hover:bg-surface-2">
                  <Td className="font-medium">{line.category_name}</Td>
                  <Td>
                    <Badge tone={line.category_type === "Income" ? "pos" : "neutral"}>
                      {line.category_type}
                    </Badge>
                  </Td>
                  <Td className="text-ink-3">{line.effective_timing}</Td>
                  <Td align="right" className="font-semibold">
                    {centsToUsd(line.annual_amount)}
                  </Td>
                  {isAdmin && (
                    <Td align="right">
                      <div className="flex items-center justify-end gap-1">
                        <span className="text-ink-3">$</span>
                        <input
                          type="number"
                          step="0.01"
                          aria-label={`${line.category_name} amount`}
                          value={dollarsValue(line)}
                          disabled={locked}
                          onChange={(e) =>
                            setEdits((prev) => ({
                              ...prev,
                              [line.category_id]: e.target.value,
                            }))
                          }
                          className="h-9 w-28 rounded-ctrl border border-border-2 bg-surface px-2 text-right text-[13px] text-ink disabled:opacity-60"
                        />
                      </div>
                    </Td>
                  )}
                </tr>
              ))}
            </tbody>
          </Table>
        </CardBody>
      </Card>

      <Modal
        open={copyConflict}
        onClose={() => setCopyConflict(false)}
        title={`Overwrite ${data.year} budget?`}
      >
        <p className="text-[13px] text-ink-2">
          {data.year} already has budget data. Copying from {data.year - 1} will
          replace it.
        </p>
        <div className="mt-4 flex justify-end gap-2">
          <Button onClick={() => setCopyConflict(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleCopyConfirm}>
            Overwrite
          </Button>
        </div>
      </Modal>
    </section>
  );
}
