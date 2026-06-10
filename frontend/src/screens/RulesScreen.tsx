import { useEffect, useState } from "react";
import type { Reference, Rule } from "@/lib/types";
import { Plus, Trash2 } from "@/icons";
import { Badge, Button, Card, CardBody, CardHead, Table, Td, Th } from "@/primitives";

// The categorization rules editor (admin). Reads GET /api/rules; create → POST
// /api/rules { pattern, category_id }; delete → DELETE /api/rules/:id. All fetch/
// handler behavior reused unchanged. The prototype's "Active toggle" has no API
// endpoint, so it is omitted here (visual-redesign-009 out-of-scope).
export default function RulesScreen({
  reference,
  onToast,
}: {
  reference: Reference | null;
  onToast?: (msg: string) => void;
}) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [ruleForm, setRuleForm] = useState({ pattern: "", category_id: "" });
  const [reload, setReload] = useState(0);

  const categories = reference?.categories ?? [];
  const firstCatId = categories[0]?.id;
  const defaultCatValue = firstCatId !== undefined ? String(firstCatId) : "";

  useEffect(() => {
    let active = true;
    void (async () => {
      const res = await fetch("/api/rules", { credentials: "include" });
      if (!res.ok) {
        if (active) setRules([]);
        return;
      }
      const data = (await res.json()) as { rules: Rule[] };
      if (active) setRules(data.rules ?? []);
    })();
    return () => {
      active = false;
    };
  }, [reload]);

  async function handleCreateRule() {
    const catId = Number(ruleForm.category_id || defaultCatValue);
    await fetch("/api/rules", {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ pattern: ruleForm.pattern, category_id: catId }),
    });
    setRuleForm({ pattern: "", category_id: "" });
    setReload((t) => t + 1);
    onToast?.("Rule created");
  }

  async function handleDeleteRule(ruleId: number) {
    await fetch(`/api/rules/${ruleId}`, { method: "DELETE", credentials: "include" });
    setReload((t) => t + 1);
    onToast?.("Rule deleted");
  }

  return (
    <section data-testid="rules-editor" aria-label="Categorization rules" className="space-y-[18px]">
      <Card>
        <CardHead title="New rule" subtitle="Match a description pattern to a category" />
        <CardBody>
          <div className="flex flex-wrap items-end gap-3">
            <div className="grow">
              <label
                htmlFor="rule-pattern"
                className="mb-1.5 block text-[12.5px] font-semibold text-ink-2"
              >
                Pattern
              </label>
              <input
                id="rule-pattern"
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
                htmlFor="rule-category"
                className="mb-1.5 block text-[12.5px] font-semibold text-ink-2"
              >
                Category
              </label>
              <select
                id="rule-category"
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
            <Button variant="primary" className="h-10" onClick={handleCreateRule}>
              <Plus size={15} /> Add rule
            </Button>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHead title="Categorization rules" subtitle={`${rules.length} active rules`} />
        <CardBody className="px-0 py-0">
          <Table>
            <thead>
              <tr>
                <Th>Pattern</Th>
                <Th>Category</Th>
                <Th>Conditions</Th>
                <Th align="right">Priority</Th>
                <Th>Actions</Th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr
                  key={r.id}
                  className={`hover:bg-surface-2 ${r.active ? "" : "opacity-60"}`}
                >
                  <Td className="mono">{r.pattern}</Td>
                  <Td>
                    <Badge tone="brand">{r.category}</Badge>
                  </Td>
                  <Td className="text-ink-3">
                    {[
                      r.account ? `acct=${r.account}` : null,
                      r.amount_min !== null ? `min=${r.amount_min}` : null,
                      r.amount_max !== null ? `max=${r.amount_max}` : null,
                    ]
                      .filter(Boolean)
                      .join(", ") || "—"}
                  </Td>
                  <Td align="right">{r.priority}</Td>
                  <Td>
                    <Button
                      size="sm"
                      variant="danger"
                      aria-label={`Delete rule ${r.pattern}`}
                      onClick={() => handleDeleteRule(r.id)}
                    >
                      <Trash2 size={14} /> Delete
                    </Button>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </CardBody>
      </Card>
    </section>
  );
}
