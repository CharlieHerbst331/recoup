import { ArrowRight, Search } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ActionBadge, CompanyMark } from "@/components/case-labels";
import { caseStatus } from "@/lib/ui";

function actionContext({ action, brief }) {
  if (!action || action.status === "submitted_mock" || brief.label === "Human attention needed")
    return caseStatus(brief.label);
  if (action.kind === "claim_package" && brief.label === "Claim needs documents")
    return caseStatus(brief.label);
  return action.status === "approved" ? "Ready to submit" : "Needs approval";
}

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
        <div className="hidden grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_7rem] gap-5 border-b px-6 py-3 text-xs text-muted-foreground sm:grid">
          <span>Customer</span>
          <span>Next action / outcome</span>
          <span className="text-right">Open balance</span>
        </div>
        <ul className="divide-y">
          {cases.map((c) => (
            <li key={c.case_id}>
              <Button
                variant="ghost"
                className="grid h-auto w-full grid-cols-[minmax(0,1fr)_auto] gap-x-3 gap-y-3 rounded-none px-4 py-4 text-left sm:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_7rem] sm:gap-x-5 sm:px-6 sm:py-5"
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
                <span className="flex min-w-0 items-center gap-3 whitespace-normal font-semibold">
                  <CompanyMark buyer={c.buyer} />
                  <span className="wrap-anywhere">{c.buyer}</span>
                </span>
                <span className="col-span-2 row-start-2 flex flex-wrap items-center gap-x-2 gap-y-1 pl-[52px] text-xs font-normal whitespace-normal text-muted-foreground sm:col-span-1 sm:col-start-2 sm:row-start-1 sm:pl-0">
                  {c.action && <ActionBadge kind={c.action.kind} />}
                  {actionContext(c)}
                </span>
                <span className="col-start-2 row-start-1 text-right font-medium tabular-nums sm:col-start-3">
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
