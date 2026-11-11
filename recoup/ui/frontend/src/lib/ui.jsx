import { createContext, useContext } from "react";
import { Button } from "@/components/ui/button";
import { FileText } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export const filters = [
  "All cases",
  "Needs approval",
  "Approved",
  "MOCK submitted",
  "Needs attention",
];
export const names = {
  dispute: "Dispute",
  credit_memo: "Credit memo",
  info_request: "Information request",
  follow_up: "Follow-up",
  insurer_notice: "Insurer notice",
  claim_package: "Claim package",
  correction: "Correction",
  counteroffer: "Counteroffer",
};
export const states = {
  proposed: "Needs approval",
  approved: "Approved · awaiting submission",
  submitted_mock: "MOCK submitted",
  stale: "Outdated draft",
  cancelled: "Cancelled",
  rejected: "Rejected",
};
export const tones = {
  orange: "border-amber-200 bg-amber-50 text-amber-800",
  blue: "border-blue-200 bg-blue-50 text-blue-800",
  green: "border-emerald-200 bg-emerald-50 text-emerald-800",
  red: "border-red-200 bg-red-50 text-red-800",
  violet: "border-violet-200 bg-violet-50 text-violet-800",
  gray: "border-stone-200 bg-stone-50 text-stone-600",
};
export const nice = (s) => (s || "").replaceAll("_", " ");
export const date = (s) =>
  s
    ? new Date(s).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        timeZone: "UTC",
      })
    : "Not scheduled";
export const tone = (s) =>
  s === "proposed"
    ? "orange"
    : s === "approved"
      ? "blue"
      : s === "submitted_mock"
        ? "green"
        : "gray";
export function Tag({ children }) {
  return (
    <span className="text-xs font-medium text-muted-foreground">
      {children}
    </span>
  );
}
export function caseStatus(label) {
  return (
    {
      "Credit ready for review": "Credit to approve",
      "Review the proposed response": "Review case",
      "Valid deduction credited": "Credit posted",
      "Buyer repaid the deduction": "Repaid in full",
      "MOCK claim submitted": "Claim submitted · awaiting insurer",
      "Insurer notice ready": "Insurer notice to approve",
      "Claim needs documents": "Waiting for account statement",
      "Claim ready for review": "Claim ready to submit",
      "Waiting for claim window": "Waiting for claim window",
      "Awaiting buyer response": "Awaiting buyer response",
    }[label] || label
  );
}

export async function request(path, data) {
  const response = await fetch(
    `/api/${path}`,
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        },
  );
  const result = await response.json();
  if (!response.ok)
    throw new Error(
      result.issues
        ?.map(
          (i) => `${i.code}${i.line_id ? ` [${i.line_id}]` : ""}: ${i.message}`,
        )
        .join("\n") ||
        result.error ||
        "Request failed",
    );
  return result;
}

export function DataTable({ rows }) {
  const keys = Object.keys(rows[0] || {});
  return rows.length ? (
    <Table>
      <TableHeader>
        <TableRow>
          {keys.map((k) => (
            <TableHead key={k}>{nice(k)}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r, i) => (
          <TableRow key={i}>
            {keys.map((k) => (
              <TableCell
                className="max-w-[450px] whitespace-normal text-xs"
                key={k}
              >
                {r[k] == null
                  ? "—"
                  : typeof r[k] === "object"
                    ? JSON.stringify(r[k])
                    : String(r[k])}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  ) : (
    <p className="text-sm text-muted-foreground">Nothing recorded yet.</p>
  );
}
export const EvidenceNavigation = createContext(null);
export function Sources({ citations = [] }) {
  const context = useContext(EvidenceNavigation);
  if (!citations.length)
    return (
      <p className="text-xs text-muted-foreground">
        No source citations recorded for this action.
      </p>
    );
  const groups = Object.values(
    citations.reduce((all, c) => {
      (all[c.evidence_id] ||= { id: c.evidence_id, rows: [] }).rows.push(c);
      return all;
    }, {}),
  );
  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-muted-foreground">
        Supporting sources
      </p>
      <div className="flex flex-wrap gap-2">
        {groups.map((group) => {
          const doc = context?.documents.find(
            (d) => d.evidence.evidence_id === group.id,
          )?.evidence;
          const title = doc?.title.replace(/^SYNTHETIC — /, "") || group.id;
          return (
            <Button
              key={group.id}
              variant="outline"
              size="sm"
              className="h-auto max-w-full whitespace-normal text-left"
              onClick={() =>
                context?.navigate({
                  tab: "documents",
                  document: group.id,
                  locator: group.rows[0].locator,
                  quote: group.rows[0].quote || "",
                })
              }
            >
              <FileText className="shrink-0" />
              <span>
                {title}
                <span className="ml-1 text-xs text-muted-foreground">
                  · {group.rows.length}{" "}
                  {group.rows.length === 1 ? "citation" : "citations"}
                </span>
              </span>
            </Button>
          );
        })}
      </div>
    </div>
  );
}
export function readLocation() {
  const raw = window.location.hash.slice(1);
  const [path, query] = raw.split("?");
  if (!path?.startsWith("case/"))
    return { page: path === "sources" ? "sources" : "cases" };
  const p = new URLSearchParams(query || "");
  return {
    caseId: decodeURIComponent(path.slice(5)),
    focus: {
      tab: p.get("tab") || "review",
      document: p.get("document") || "",
      proposal: p.get("proposal") || "",
      locator: p.get("locator") || "",
      quote: p.get("quote") || "",
    },
  };
}
export function writeLocation(caseId, focus, page = "cases") {
  const p = new URLSearchParams(Object.entries(focus).filter(([k, v]) => v));
  const target = caseId
    ? `#case/${encodeURIComponent(caseId)}?${p}`
    : page === "sources" ? "#sources" : "#dashboard";
  if (window.location.hash !== target)
    window.history.pushState(null, "", target);
}
