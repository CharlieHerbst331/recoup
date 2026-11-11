import { CheckCheck, History } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion";
import { names, date, Tag, DataTable, Sources } from "@/lib/ui";

export default function AuditTrail({ detail }) {
  return (
    <div className="space-y-5">
      <Card className="shadow-none">
        <CardHeader>
          <CardTitle>Recorded MOCK actions</CardTitle>
          <CardDescription>
            Open a receipt to see the exact draft version and its human
            approval. Corrections retain their link to the original dispute.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Accordion type="multiple">
            {detail.receipt_records?.map((r) => (
              <AccordionItem key={r.receipt_id} value={r.receipt_id}>
                <AccordionTrigger className="text-left">
                  <span className="flex flex-wrap items-center gap-2">
                    <CheckCheck className="size-4 text-emerald-700" />
                    <span>
                      {names[r.kind] || r.kind}
                      {r.amount !== "No amount" ? ` · ${r.amount}` : ""}
                    </span>
                    <Tag>{r.receipt_id}</Tag>
                  </span>
                </AccordionTrigger>
                <AccordionContent className="space-y-4">
                  <p className="text-xs text-muted-foreground">
                    {date(r.at)} · Version {r.version} · {r.recipient}
                  </p>
                  {r.corrects && (
                    <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm">
                      Corrects {r.corrects}. The original correspondence remains
                      in this audit trail.
                    </p>
                  )}
                  <div>
                    {r.approvals.map((a, i) => (
                      <p className="text-sm" key={i}>
                        Approved by {a.by} · {date(a.at)}
                      </p>
                    ))}
                  </div>
                  <p className="whitespace-pre-wrap rounded-lg border bg-muted/30 p-4 text-sm leading-relaxed">
                    {r.draft_text}
                  </p>
                  <Sources citations={r.citations} />
                  <p className="text-xs text-muted-foreground">{r.label}</p>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
          {!detail.receipt_records?.length && (
            <p className="text-sm text-muted-foreground">
              No MOCK action has been submitted yet.
            </p>
          )}
        </CardContent>
      </Card>
      <Card className="shadow-none">
        <CardHeader>
          <CardTitle>Receivable ledger</CardTitle>
          <CardDescription>
            Recorded invoice, buyer payments, and MOCK credits. A claim receipt
            creates no insurer payment or receivable credit.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable rows={detail.ledger_records || []} />
        </CardContent>
      </Card>
      <Accordion
        type="single"
        collapsible
        className="rounded-lg border bg-white px-5"
      >
        <AccordionItem value="events">
          <AccordionTrigger>
            Complete event and decision history
          </AccordionTrigger>
          <AccordionContent>
            <DataTable rows={detail.timeline} />
            <p className="mt-3 text-xs text-muted-foreground">
              Recorded service status: {detail.view.status} ·{" "}
              {detail.view.status_reason}
            </p>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
