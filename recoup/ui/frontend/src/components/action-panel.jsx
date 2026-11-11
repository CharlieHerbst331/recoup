import { useState } from "react";
import { ArrowRight, CheckCheck, FileText, LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { names, states, nice, DataTable, Sources } from "@/lib/ui";

export default function ActionPanel({
  proposal,
  act,
  busy,
  receipts,
  error,
  submissionBlocked = false,
  suppressAction = false,
}) {
  const p = proposal.current,
    [editing, setEditing] = useState(false),
    [draft, setDraft] = useState(p.draft_text),
    [recipient, setRecipient] = useState(p.recipient),
    [allocations, setAllocations] = useState(
      proposal.allocations.map((a) => ({ ...a })),
    ),
    [reject, setReject] = useState(false),
    [reason, setReason] = useState("");
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Dialog open={editing} onOpenChange={setEditing}>
          <DialogTrigger asChild>
            <Button variant="ghost" disabled={busy || p.status !== "proposed"}>
              <FileText />
              Edit draft
            </Button>
          </DialogTrigger>
          <DialogContent className="max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                Edit {names[p.kind]?.toLowerCase()} draft
              </DialogTitle>
              <DialogDescription>
                Saving creates a new version. Review and approve that version
                before MOCK submission.
              </DialogDescription>
            </DialogHeader>
            {error && (
              <p
                role="alert"
                className="whitespace-pre-wrap text-sm text-destructive"
              >
                {error}
              </p>
            )}
            <form
              className="space-y-4"
              onSubmit={async (e) => {
                e.preventDefault();
                if (
                  await act("edit", {
                    proposal_id: p.proposal_id,
                    version: p.version,
                    draft_text: draft,
                    recipient,
                    allocations: allocations.map((a) => ({
                      line_id: a.line_id,
                      cents: a.cents,
                    })),
                  })
                )
                  setEditing(false);
              }}
            >
              <label className="block space-y-2 text-sm font-medium">
                <span>Draft text</span>
                <Textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={7}
                  required
                />
              </label>
              <label className="block space-y-2 text-sm font-medium">
                <span>Recipient</span>
                <Input
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  required
                />
              </label>
              {(p.amount !== null ? allocations : []).map((a, index) => (
                <label
                  key={a.line_id}
                  className="block space-y-2 text-sm font-medium"
                >
                  <span>{a.line_id} allocation (integer cents)</span>
                  <Input
                    inputMode="numeric"
                    pattern="[0-9]+"
                    value={a.cents}
                    onChange={(e) =>
                      setAllocations((rows) =>
                        rows.map((r, i) =>
                          i === index ? { ...r, cents: e.target.value } : r,
                        ),
                      )
                    }
                    required
                  />
                </label>
              ))}
              <Button disabled={busy} type="submit">
                {busy && <LoaderCircle className="animate-spin" />}Save changes
              </Button>
            </form>
          </DialogContent>
        </Dialog>
        {!suppressAction && p.status === "proposed" && (
          <Button
            disabled={busy || p.status !== "proposed"}
            onClick={() =>
              act("approve", { proposal_id: p.proposal_id, version: p.version })
            }
          >
            Approve{" "}
            {p.kind === "credit_memo"
              ? "credit"
              : p.kind === "dispute"
                ? "dispute"
                : p.kind === "claim_package"
                  ? "claim"
                  : p.kind === "insurer_notice"
                    ? "notice"
                    : "draft"}
          </Button>
        )}
        {!suppressAction && p.status === "approved" && (
          <Button
            variant={p.status === "approved" ? "default" : "outline"}
            disabled={busy || p.status !== "approved" || submissionBlocked}
            onClick={() =>
              act("submit", { proposal_id: p.proposal_id, version: p.version })
            }
          >
            Submit{" "}
            {p.kind === "credit_memo"
              ? "credit"
              : p.kind === "dispute"
                ? "dispute"
                : p.kind === "claim_package"
                  ? "claim"
                  : p.kind === "insurer_notice"
                    ? "notice"
                    : "response"}
          </Button>
        )}
      </div>
      <details className="mt-5 text-sm">
        <summary className="cursor-pointer text-muted-foreground">
          View draft & supporting documents
        </summary>
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap justify-between gap-3 text-xs text-muted-foreground">
            <span>Recipient: {p.recipient}</span>
            <span>
              Version {p.version} ·{" "}
              {
                {
                  mock_buyer_portal: "Buyer portal · MOCK",
                  mock_erp: "Accounting system · MOCK",
                  mock_email: "Email · MOCK",
                  mock_insurer: "Insurer · MOCK",
                }[p.target]
              }{" "}
              · {p.created_by === "human_edit" ? "Edited draft" : "Agent draft"}
            </span>
          </div>
          <Dialog open={reject} onOpenChange={setReject}>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                disabled={busy || !["proposed", "approved"].includes(p.status)}
              >
                Reject
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Reject this draft</DialogTitle>
                <DialogDescription>
                  Record why this version should not be submitted.
                </DialogDescription>
              </DialogHeader>
              {error && (
                <p
                  role="alert"
                  className="whitespace-pre-wrap text-sm text-destructive"
                >
                  {error}
                </p>
              )}
              <form
                className="space-y-4"
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (
                    await act("reject", {
                      proposal_id: p.proposal_id,
                      version: p.version,
                      reason,
                    })
                  )
                    setReject(false);
                }}
              >
                <label className="block space-y-2 text-sm">
                  <span>Rejection reason</span>
                  <Textarea
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    required
                  />
                </label>
                <Button variant="destructive" disabled={busy || !reason.trim()}>
                  Reject draft
                </Button>
              </form>
            </DialogContent>
          </Dialog>{" "}
          {p.amount !== null && proposal.allocations.length > 0 && (
            <DataTable
              rows={proposal.allocations.map((a) => ({
                Line: a.line_id,
                "Amount (USD)": a.amount,
              }))}
            />
          )}
          <div className="whitespace-pre-wrap rounded-lg border bg-muted/60 p-4 text-sm leading-relaxed">
            {p.draft_text}
          </div>
          {["stale", "cancelled"].includes(p.status) && (
            <Alert>
              <AlertDescription>
                This draft is out of date. Run the agent to review the latest
                evidence.
              </AlertDescription>
            </Alert>
          )}
          <Sources citations={p.citations} />
          <details>
            <summary className="cursor-pointer text-xs font-medium text-muted-foreground">
              Earlier draft versions
            </summary>
            <div className="mt-4 space-y-4">
              {proposal.versions.map((v) => (
                <div key={v.version} className="rounded border p-3 text-xs">
                  <p className="mb-2 font-medium">
                    v{v.version} · {states[v.status]} · {v.created_by}
                  </p>
                  <p className="whitespace-pre-wrap">{v.draft_text}</p>
                </div>
              ))}
            </div>
          </details>
        </div>
      </details>
    </div>
  );
}
