import { useEffect, useState } from "react";
import type { Reference, Transaction, TransactionsResponse } from "@/lib/types";
import { centsToUsd } from "@/lib/format";
import { Inbox } from "@/icons";
import { Button, Card, CardBody, CardHead, Table, Td, Th } from "@/primitives";

// The categorization review queue (admin). Reads GET /api/transactions?needs_review
// =true; Save → PATCH /api/transactions/:id { category_id }; "Create rule"
// pre-fills a pattern via GET /api/rules/suggest then POSTs /api/rules. All fetch/
// handler behavior reused unchanged. The create-rule compose panel now lives on
// this screen (Rules is a separate nav screen), so the suggested pattern is still
// reachable without leaving the queue (visual-redesign-009).
export default function ReviewQueue({
  reference,
  onCountChange,
  onToast,
}: {
  reference: Reference | null;
  onCountChange?: (n: number) => void;
  onToast?: (msg: string) => void;
}) {
  const [reviewTxns, setReviewTxns] = useState<Transaction[]>([]);
  const [reviewTotal, setReviewTotal] = useState(0);
  const [reviewCat, setReviewCat] = useState<Record<number, string>>({});
  const [composingId, setComposingId] = useState<number | null>(null);
  const [ruleForm, setRuleForm] = useState({ pattern: "", category_id: "" });
  const [reload, setReload] = useState(0);

  const categories = reference?.categories ?? [];
  const firstCatId = categories[0]?.id;
  const defaultCatValue = firstCatId !== undefined ? String(firstCatId) : "";

  useEffect(() => {
    let active = true;
    void (async () => {
      const res = await fetch("/api/transactions?needs_review=true", {
        credentials: "include",
      });
      if (!res.ok) {
        if (active) {
          setReviewTxns([]);
          setReviewTotal(0);
        }
        return;
      }
      const data = (await res.json()) as TransactionsResponse;
      if (active) {
        setReviewTxns(data.transactions ?? []);
        setReviewTotal(data.total ?? 0);
        onCountChange?.(data.total ?? 0);
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reload]);

  async function handleSaveFix(txn: Transaction) {
    const catId = Number(reviewCat[txn.id] ?? defaultCatValue);
    await fetch(`/api/transactions/${txn.id}`, {
      method: "PATCH",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ category_id: catId }),
    });
    setReload((t) => t + 1);
    onToast?.("Transaction categorized");
  }

  async function handleCreateRuleFromReview(txn: Transaction) {
    let pattern = txn.description;
    const res = await fetch(
      `/api/rules/suggest?description=${encodeURIComponent(txn.description)}`,
      { credentials: "include" },
    );
    if (res.ok) {
      const data = (await res.json()) as { pattern?: string };
      pattern = data.pattern ?? txn.description;
    }
    setComposingId(txn.id);
    setRuleForm({ pattern, category_id: reviewCat[txn.id] ?? defaultCatValue });
  }

  async function handleCreateRule() {
    const catId = Number(ruleForm.category_id || defaultCatValue);
    await fetch("/api/rules", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ pattern: ruleForm.pattern, category_id: catId }),
    });
    setRuleForm({ pattern: "", category_id: "" });
    setComposingId(null);
    setReload((t) => t + 1);
    onToast?.("Rule created");
  }

  return (
    <section data-testid="review-queue" aria-label="Review queue" className="space-y-[18px]">
      <div className="grid grid-cols-1 gap-[18px] sm:grid-cols-3">
        <Card className="p-[22px]">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-[0.05em] text-ink-3">
              Awaiting review
            </span>
            <span className="flex h-7 w-7 items-center justify-center rounded-ctrl bg-amber-soft text-amber">
              <Inbox size={16} />
            </span>
          </div>
          <div
            className="tnum mt-2 text-[30px] font-bold leading-none text-ink"
            data-testid="review-count"
            aria-label={`${reviewTotal} transactions need review`}
          >
            {reviewTotal}
          </div>
        </Card>
      </div>

      <Card>
        <CardHead title="Review queue" subtitle="Categorize flagged transactions" />
        <CardBody className="px-0 py-0">
          {reviewTxns.length === 0 ? (
            <p className="px-[22px] py-6 text-[13px] text-ink-2">
              Inbox zero — every transaction is categorized.
            </p>
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Date</Th>
                  <Th>Description</Th>
                  <Th align="right">Amount</Th>
                  <Th>Category</Th>
                  <Th>Actions</Th>
                </tr>
              </thead>
              <tbody>
                {reviewTxns.map((t) => (
                  <tr key={t.id} className="hover:bg-surface-2">
                    <Td className="mono text-ink-2">{t.post_date}</Td>
                    <Td className="font-medium">{t.description}</Td>
                    <Td align="right" className={t.debit ? "text-neg" : "text-pos"}>
                      {centsToUsd(t.debit ?? t.credit)}
                    </Td>
                    <Td>
                      <select
                        aria-label="Category"
                        value={reviewCat[t.id] ?? defaultCatValue}
                        onChange={(e) =>
                          setReviewCat((prev) => ({ ...prev, [t.id]: e.target.value }))
                        }
                        className="h-9 rounded-ctrl border border-border-2 bg-surface px-2 text-[13px] text-ink"
                      >
                        {categories.map((c) => (
                          <option key={c.id ?? c.name} value={String(c.id ?? "")}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </Td>
                    <Td>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="primary"
                          onClick={() => handleSaveFix(t)}
                        >
                          Save
                        </Button>
                        {composingId === null && (
                          <Button size="sm" onClick={() => handleCreateRuleFromReview(t)}>
                            Create rule
                          </Button>
                        )}
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </CardBody>
      </Card>

      {composingId !== null && (
        <Card>
          <CardHead title="Create rule from transaction" />
          <CardBody className="space-y-3">
            <div>
              <label
                htmlFor="review-rule-pattern"
                className="mb-1.5 block text-[12.5px] font-semibold text-ink-2"
              >
                Pattern
              </label>
              <input
                id="review-rule-pattern"
                type="text"
                value={ruleForm.pattern}
                onChange={(e) =>
                  setRuleForm((prev) => ({ ...prev, pattern: e.target.value }))
                }
                className="mono h-10 w-full rounded-ctrl border border-border-2 bg-surface px-3 text-[13px] text-ink"
              />
            </div>
            <div>
              <label
                htmlFor="review-rule-category"
                className="mb-1.5 block text-[12.5px] font-semibold text-ink-2"
              >
                Rule category
              </label>
              <select
                id="review-rule-category"
                value={ruleForm.category_id || defaultCatValue}
                onChange={(e) =>
                  setRuleForm((prev) => ({ ...prev, category_id: e.target.value }))
                }
                className="h-10 rounded-ctrl border border-border-2 bg-surface px-2 text-[13px] text-ink"
              >
                {categories.map((c) => (
                  <option key={c.id ?? c.name} value={String(c.id ?? "")}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex justify-end gap-2">
              <Button onClick={() => setComposingId(null)}>Cancel</Button>
              <Button variant="primary" onClick={handleCreateRule}>
                Save rule
              </Button>
            </div>
          </CardBody>
        </Card>
      )}
    </section>
  );
}
