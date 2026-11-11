import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Tag, Sources } from "@/lib/ui";

const requirements = {
  "claim.notice_receipt": "Insurer notice receipt",
  "claim.waiting_period": "Policy waiting period",
  "claim.collection_history": "Collection history",
  "claim.disputed_portion": "Policy treatment of disputed debt",
  "claim.credit_limit": "Policy credit limit",
  "notice.applicability": "Buyer and invoice period",
  "notice.trigger": "Positive overdue balance",
  "notice.deadline": "Policy notice deadline",
  "notice.balance_basis": "Current ledger balance",
  "notice.dispute_status": "Buyer deduction status (annotation)",
};

export default function InsuranceReview({ detail, kind = "claim" }) {
  const readiness = detail.view.readiness
    .filter((r) => r.kind === kind && r.status !== "stale")
    .at(-1);
  const gaps = readiness?.items.filter((i) => i.status !== "present") || [];
  function label(item) {
    if (requirements[item.item_id]) return requirements[item.item_id];
    const clauseKey = "claim_doc." + item.item_id.split(".").at(-1);
    const answer = detail.policy_review?.find(
      (a) => a.question === "claim documents" && a.clause_key === clauseKey,
    );
    return answer
      ? `Required ${answer.result.replaceAll("_", " ")}`
      : item.requirement.replaceAll(".", " ");
  }
  return (
    <Card className="gap-3 border-blue-200 bg-blue-50/20 py-4 shadow-none">
      <CardHeader className="px-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-base">
            {kind === "claim"
              ? "Claim submission checklist"
              : "Insurer notice checks"}
          </CardTitle>
          <Tag color={readiness?.status === "ready" ? "green" : "orange"}>
            {readiness?.status === "ready"
              ? "Ready for MOCK submission"
              : "Submission needs review"}
          </Tag>
        </div>
        <CardDescription>
          Current ledger balance: {detail.balance}. A document-ready package
          records no insurer decision or payment.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 px-5">
        {kind === "claim" && gaps.length > 0 && (
          <p
            role="status"
            className="rounded border border-amber-200 bg-amber-50 p-3 text-sm font-medium"
          >
            Submission blocked: {gaps.map(label).join(", ")}.
          </p>
        )}
        <ul className="grid gap-2 text-sm sm:grid-cols-2">
          {readiness?.items.map((item) => (
            <li
              key={item.item_id}
              className="flex items-start justify-between gap-3 rounded border bg-white p-2"
            >
              <span>{label(item)}</span>
              <Tag color={item.status === "present" ? "green" : "orange"}>
                {item.status}
              </Tag>
            </li>
          ))}
        </ul>
        <details>
          <summary className="cursor-pointer text-sm font-medium">
            Recorded policy checks and source clauses
          </summary>
          <div className="mt-3 space-y-4">
            {detail.policy_review?.map((answer, index) => (
              <div className="space-y-2 text-sm" key={index}>
                <p className="font-medium capitalize">{answer.question}</p>
                <p className="whitespace-pre-wrap text-muted-foreground">
                  {answer.result}
                </p>
                <Sources citations={answer.citations} />
              </div>
            ))}
          </div>
        </details>
      </CardContent>
    </Card>
  );
}
