import { ArrowRight, Search } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { caseStatus } from "@/lib/ui";

export default function Dashboard({ data, openCase, act, busy }) {
  const [query, setQuery] = useState("");
  const step = data.journey?.current;
  const cases = [...data.cases]
    .sort(
      (a, b) =>
        ["C", "H", "N"].indexOf(a.case_id) - ["C", "H", "N"].indexOf(b.case_id),
    )
    .filter((c) =>
      `${c.buyer} ${c.case_id}`.toLowerCase().includes(query.toLowerCase()),
    );
  function next() {
    if (step.action === "advance") act("advance", { to_next_due: true });
    else
      openCase(step.case_id, {
        tab: "review",
        proposal: step.proposal_key || "",
      });
  }
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">Cases</h1>
        {step && (
          <Button disabled={busy} onClick={next}>
            {step.action === "advance"
              ? "Advance to next event"
              : "Continue review"}
            <ArrowRight />
          </Button>
        )}
        {!data.cases.length && (
          <Button disabled={busy} onClick={() => act("fresh")}>
            Load cases
          </Button>
        )}
      </div>
      {data.cases.length > 5 && (
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-3 size-4 text-muted-foreground" />
          <Input
            aria-label="Search cases"
            className="pl-9"
            placeholder="Search customers"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      )}
      <div className="overflow-hidden rounded-xl border bg-white">
        <div className="hidden grid-cols-[1fr_1.4fr_auto] gap-6 border-b px-6 py-3 text-xs text-muted-foreground sm:grid">
          <span>Customer</span>
          <span>Next action / outcome</span>
          <span>Open balance</span>
        </div>
        <ul className="divide-y">
          {cases.map((c) => (
            <li key={c.case_id}>
              <Button
                variant="ghost"
                className="grid h-auto w-full grid-cols-[1fr_auto] gap-x-5 gap-y-2 rounded-none px-6 py-6 text-left sm:grid-cols-[1fr_1.4fr_auto]"
                aria-label={`Open ${c.buyer}`}
                disabled={busy}
                onClick={() =>
                  openCase(c.case_id, {
                    proposal:
                      step?.case_id === c.case_id
                        ? step.proposal_key || ""
                        : "",
                  })
                }
              >
                <span className="font-medium">{c.buyer}</span>
                <span className="col-start-1 row-start-2 whitespace-normal text-xs font-normal leading-relaxed text-muted-foreground sm:col-start-2 sm:row-start-1 sm:text-sm">
                  {caseStatus(c.brief.label)}
                </span>
                <span className="col-start-2 row-start-1 font-medium tabular-nums sm:col-start-3">
                  {c.balance}
                </span>
              </Button>
            </li>
          ))}
        </ul>
      </div>
      {data.journey?.complete && (
        <p className="text-sm text-muted-foreground">
          Buyer payments received: {data.new_payments}.{" "}
          {data.claims_submitted_count} claim submitted; insurer review pending.
        </p>
      )}
      {data.quarantined.length > 0 && (
        <details className="text-sm">
          <summary className="cursor-pointer">
            Imports needing attention
          </summary>
          {data.quarantined.map((r) => (
            <p key={r.case_id}>
              {r.case_id}: {r.reason}
            </p>
          ))}
        </details>
      )}
    </div>
  );
}
