import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Check, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { DataTable, Sources, EvidenceNavigation } from "@/lib/ui";
import { ActionBadge, CompanyMark } from "@/components/case-labels";
import ActionPanel from "@/components/action-panel";
import Documents from "@/components/documents";
import AgentActivity from "@/components/agent-activity";
import InsuranceReview from "@/components/insurance-review";
import AuditTrail from "@/components/audit-trail";

const titles = {
  credit_memo: "Issue credit",
  dispute: "Dispute deduction",
  insurer_notice: "Notify insurer",
  claim_package: "Submit claim",
  info_request: "Request information",
  follow_up: "Follow up",
  correction: "Correct earlier dispute",
  counteroffer: "Review counteroffer",
};
const reasons = {
  credit_memo: "The source records support this credit adjustment.",
  dispute:
    "The source records do not support this deduction. Request repayment from the buyer.",
  insurer_notice:
    "The overdue balance meets the supplied policy's notice checks.",
  claim_package:
    "Required documents are present. The package is ready for insurer review.",
  info_request:
    "Ask the buyer for the information needed to assess this deduction.",
  follow_up: "The balance remains unpaid. Follow up with the buyer.",
  correction: "New evidence changes the earlier assessment.",
};
function savedContext(text) {
  const facts = text.match(/Source facts: ([\s\S]*?)(?:\n\n|$)/)?.[1];
  if (!facts) return "";
  const sentences = facts.split(/(?<=\.)\s+(?=[A-Z])/);
  const first = sentences.find((s) => s.startsWith("The invoice lists"));
  const source =
    sentences.find(
      (s) =>
        s.startsWith("The amendment lists") ||
        s.startsWith("The signed amendment records"),
    ) || sentences.find((s) => s.startsWith("POD v"));
  return [first, source].filter(Boolean).join(" ");
}

export default function CasePage({
  detail,
  act,
  home,
  busy,
  error,
  focus,
  navigate,
  journey,
  openCase,
}) {
  const c = detail.view,
    step = journey?.current;
  const [expanded, setExpanded] = useState(false);
  const live = detail.proposals.filter((p) =>
    ["proposed", "approved"].includes(p.current.status),
  );
  const preferred =
    focus.proposal || (step?.case_id === c.case_id ? step.proposal_key : null);
  const latestReceipt = c.receipts.at(-1);
  const receiptView =
    ((step?.case_id === c.case_id &&
      step.action === "advance" &&
      !step.proposal_key) ||
      journey?.complete) &&
    detail.proposals.find(
      (row) => row.current.proposal_id === latestReceipt?.proposal_id,
    );
  const active =
    detail.proposals.find((p) => p.current.business_key === preferred) ||
    receiptView ||
    live.find(
      (p) => !["insurer_notice", "claim_package"].includes(p.current.kind),
    ) ||
    live[0];
  const p = active?.current;
  const claim = c.readiness
    .filter((r) => r.kind === "claim" && r.status !== "stale")
    .at(-1);
  const blocked = p?.kind === "claim_package" && claim?.status !== "ready";
  const completed =
    (c.open_balance.cents === "0" &&
      !live.some(
        (row) =>
          !["insurer_notice", "claim_package"].includes(row.current.kind),
      )) ||
    p?.status === "submitted_mock";
  const next =
    step && (step.action === "advance" || step.case_id !== c.case_id);
  const invoice = detail.documents.find((d) => d.evidence.kind === "invoice")
    ?.evidence.fields.invoice_no;
  useEffect(() => {
    setExpanded(focus.tab !== "review");
  }, [focus.tab, focus.proposal]);
  function continueReview() {
    if (step.action === "advance") act("advance", { to_next_due: true });
    else
      openCase(step.case_id, {
        tab: "review",
        proposal: step.proposal_key || "",
      });
  }
  const outcome =
    c.open_balance.cents === "0"
      ? detail.new_payments !== "$0.00"
        ? `Buyer payment received: ${detail.new_payments}. No credit conceded.`
        : "Credit posted. The account is reconciled."
      : p?.kind === "claim_package" && p.status === "submitted_mock"
        ? "Claim submitted. The balance remains open pending insurer review."
        : p?.kind === "insurer_notice" && p.status === "submitted_mock"
          ? "Notice submitted. The agent will check the claim window as time advances."
          : "Response submitted. Awaiting the buyer's reply.";
  return (
    <EvidenceNavigation.Provider
      value={{ documents: detail.documents, navigate }}
    >
      <button
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        disabled={busy}
        onClick={home}
      >
        <ArrowLeft size={15} />
        Cases
      </button>
      <div className="flex flex-wrap items-start justify-between gap-4 sm:gap-6">
        <div className="flex min-w-0 items-center gap-3 sm:gap-4">
          <CompanyMark buyer={c.buyer} large />
          <div className="min-w-0">
            <h1 className="wrap-anywhere text-2xl font-semibold tracking-tight sm:text-3xl">{c.buyer}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {invoice || `Case ${c.case_id}`}
            </p>
          </div>
        </div>
        <div className="ml-auto text-right">
          <p className="text-xs text-muted-foreground">Open balance</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {detail.balance}
          </p>
        </div>
      </div>
      <section
        className="rounded-xl border bg-white p-6 md:p-8"
        aria-label="Recommendation"
      >
        {completed ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 font-medium">
              <Check size={18} />
              {c.open_balance.cents === "0" ? "Resolved" : "Submitted"}
              {p && <ActionBadge kind={p.kind} />}
            </div>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
              {outcome}
            </p>
          </div>
        ) : active ? (
          <>
            <div className="mb-3"><ActionBadge kind={p.kind} /></div>
            <div className="mb-3 flex items-baseline justify-between gap-4">
              <h2 className="text-xl font-semibold">
                {titles[p.kind] || "Review response"}
              </h2>
              {p.amount !== null && (
                <span className="text-xl font-semibold tabular-nums">
                  {active.amount}
                </span>
              )}
            </div>
            <p className="mb-6 max-w-2xl text-sm leading-relaxed text-muted-foreground">
              {blocked
                ? "An account statement is still missing. The agent will update the claim when it arrives."
                : savedContext(p.draft_text) ||
                  reasons[p.kind] ||
                  detail.brief.summary}
            </p>
            <ActionPanel
              key={`${p.proposal_id}:${p.version}`}
              proposal={active}
              act={act}
              busy={busy}
              receipts={c.receipts}
              error={error}
              submissionBlocked={blocked}
              suppressAction={blocked}
            />
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            {detail.brief.summary}
          </p>
        )}
        {(completed || blocked || !active) && (
          <div className="mt-6">
            {next ? (
              <Button disabled={busy} onClick={continueReview}>
                {step.action === "advance" ? "Advance to next event" : step.cta}
                <ArrowRight />
              </Button>
            ) : journey?.complete ? (
              <Button disabled={busy} onClick={home}>
                Back to cases
                <ArrowRight />
              </Button>
            ) : null}
          </div>
        )}
      </section>
      <details
        open={expanded}
        onToggle={(e) => setExpanded(e.currentTarget.open)}
        className="border-t pt-5"
      >
        <summary className="flex cursor-pointer list-none items-center gap-2 text-sm text-muted-foreground">
          Details
          <ChevronDown size={15} />
        </summary>
        <Tabs
          value={focus.tab === "review" ? "documents" : focus.tab}
          onValueChange={(tab) => navigate({ tab })}
          className="mt-5 space-y-5"
        >
          <TabsList className="w-full justify-start overflow-x-auto bg-transparent p-0">
            {[
              ["documents", "Documents"],
              ["agent", "Agent activity"],
              ["checklists", "Policy & checks"],
              ["activity", "Audit trail"],
              ["assessment", "Assessment"],
            ].map(([value, label]) => (
              <TabsTrigger key={value} value={value}>
                {label}
              </TabsTrigger>
            ))}
          </TabsList>
          <TabsContent value="documents">
            <Documents
              detail={detail}
              act={act}
              busy={busy}
              error={error}
              focus={focus}
              navigate={navigate}
            />
          </TabsContent>
          <TabsContent value="agent">
            <AgentActivity detail={detail} navigate={navigate} />
          </TabsContent>
          <TabsContent value="checklists">
            <InsuranceReview
              detail={detail}
              kind={p?.kind === "insurer_notice" ? "notice" : "claim"}
            />
          </TabsContent>
          <TabsContent value="activity">
            <AuditTrail detail={detail} />
          </TabsContent>
          <TabsContent value="assessment">
            <DataTable rows={detail.money} />
            {c.decision?.lines.map((line) => (
              <div key={line.line_id} className="mt-5 space-y-2 text-sm">
                <p>{line.rationale}</p>
                <Sources citations={line.citations} />
              </div>
            ))}
          </TabsContent>
        </Tabs>
        {detail.proposals.length > 1 && (
          <div className="mt-6 max-w-md">
            <Select
              value={active?.current.business_key || ""}
              onValueChange={(proposal) =>
                navigate({ tab: "review", proposal })
              }
            >
              <SelectTrigger aria-label="Other actions">
                <SelectValue placeholder="Other actions" />
              </SelectTrigger>
              <SelectContent>
                {detail.proposals.map((row) => (
                  <SelectItem
                    key={row.current.business_key}
                    value={row.current.business_key}
                  >
                    <span className="flex flex-wrap items-center gap-2">
                      <ActionBadge kind={row.current.kind} />
                      <span>
                        {row.current.amount !== null ? `${row.amount} · ` : ""}
                        {row.current.status.replaceAll("_", " ")}
                      </span>
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </details>
    </EvidenceNavigation.Provider>
  );
}
