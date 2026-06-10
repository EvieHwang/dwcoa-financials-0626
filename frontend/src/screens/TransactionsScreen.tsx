import { useEffect, useMemo, useState } from "react";
import type { Reference, Transaction, TransactionsResponse } from "@/lib/types";
import { centsToUsd, yearOptions } from "@/lib/format";
import { ChevronLeft, ChevronRight } from "@/icons";
import { Badge, Button, Card, CardBody, CardHead, Table, Td, Th } from "@/primitives";

// The full transactions ledger with Year/Account filters and server-side
// pagination. Filter changes reset the offset to 0; paging advances it. All
// fetch behavior is reused unchanged from the prior implementation
// (visual-redesign-009 US-5).
export default function TransactionsScreen({
  reference,
}: {
  reference: Reference | null;
}) {
  const [txns, setTxns] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [year, setYear] = useState("");
  const [account, setAccount] = useState("");

  useEffect(() => {
    let active = true;
    void (async () => {
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      params.set("offset", String(offset));
      if (year) params.set("year", year);
      if (account) params.set("account", account);
      const res = await fetch(`/api/transactions?${params.toString()}`, {
        credentials: "include",
      });
      if (!res.ok) {
        if (active) {
          setTxns([]);
          setTotal(0);
        }
        return;
      }
      const data = (await res.json()) as TransactionsResponse;
      if (active) {
        setTxns(data.transactions);
        setTotal(data.total);
        setLimit(data.limit);
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, account, offset]);

  const accountOptions = useMemo(() => {
    const masked = new Map<string, string | undefined>();
    reference?.accounts.forEach((a) => masked.set(a.name, a.masked_number));
    txns.forEach((t) => {
      if (!masked.has(t.account_name)) masked.set(t.account_name, t.account_number);
    });
    return Array.from(masked.entries()).map(([name, number]) => ({ name, number }));
  }, [reference, txns]);

  const hasNextPage = offset + limit < total;
  const hasPrevPage = offset > 0;

  return (
    <Card>
      <CardHead
        title="Transactions"
        subtitle="Every posted transaction across the association's accounts"
        actions={
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5">
              <label htmlFor="filter-year" className="text-[12.5px] text-ink-2">
                Year
              </label>
              <select
                id="filter-year"
                value={year}
                onChange={(e) => {
                  setOffset(0);
                  setYear(e.target.value);
                }}
                className="h-9 rounded-ctrl border border-border-2 bg-surface px-2 text-[13px] text-ink"
              >
                <option value="">All years</option>
                {yearOptions().map((y) => (
                  <option key={y} value={String(y)}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-1.5">
              <label htmlFor="filter-account" className="text-[12.5px] text-ink-2">
                Account
              </label>
              <select
                id="filter-account"
                value={account}
                onChange={(e) => {
                  setOffset(0);
                  setAccount(e.target.value);
                }}
                className="h-9 rounded-ctrl border border-border-2 bg-surface px-2 text-[13px] text-ink"
              >
                <option value="">All accounts</option>
                {accountOptions.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.number ? `${a.name} (${a.number})` : a.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        }
      />
      <CardBody className="px-0 py-0">
        <Table>
          <thead>
            <tr>
              <Th>Date</Th>
              <Th>Account</Th>
              <Th>Check</Th>
              <Th>Description</Th>
              <Th>Category</Th>
              <Th align="right">Debit</Th>
              <Th align="right">Credit</Th>
              <Th align="right">Balance</Th>
            </tr>
          </thead>
          <tbody>
            {txns.map((t) => (
              <tr key={t.id} className="hover:bg-surface-2">
                <Td className="mono text-ink-2">{t.post_date}</Td>
                <Td>{t.account_name}</Td>
                <Td className="mono text-ink-3">{t.check_number ?? ""}</Td>
                <Td className="font-medium">{t.description}</Td>
                <Td>
                  {t.category ? (
                    <Badge tone="neutral">{t.category}</Badge>
                  ) : (
                    <Badge tone="amber">Needs review</Badge>
                  )}
                </Td>
                <Td align="right" className="text-neg">
                  {centsToUsd(t.debit)}
                </Td>
                <Td align="right" className="text-pos">
                  {centsToUsd(t.credit)}
                </Td>
                <Td align="right" className="text-ink-3">
                  {centsToUsd(t.balance)}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      </CardBody>
      <div className="flex items-center justify-between border-t border-hairline px-[22px] py-3">
        <span className="text-[12.5px] text-ink-2">
          {total === 0
            ? "No transactions"
            : `Showing ${offset + 1}–${Math.min(offset + limit, total)} of ${total}`}
        </span>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            aria-label="Previous page"
            onClick={() => setOffset(Math.max(0, offset - limit))}
            disabled={!hasPrevPage}
          >
            <ChevronLeft size={15} /> Previous
          </Button>
          <Button
            size="sm"
            aria-label="Next page"
            onClick={() => setOffset(offset + limit)}
            disabled={!hasNextPage}
          >
            Next <ChevronRight size={15} />
          </Button>
        </div>
      </div>
    </Card>
  );
}
