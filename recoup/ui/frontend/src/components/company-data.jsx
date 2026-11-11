import {
  Banknote, BookOpen, Boxes, Database, FileText, Landmark, Mail,
  MessagesSquare, Plug, ShieldCheck, Store,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

function SlackMark(props) {
  return (
    <svg viewBox="0 0 24 24" fill="none" strokeWidth="4" strokeLinecap="round" {...props}>
      <path stroke="#36C5F0" d="M4 8h7M11 3h.1" />
      <path stroke="#2EB67D" d="M16 4v7M21 11v.1" />
      <path stroke="#ECB22E" d="M20 16h-7M13 21h-.1" />
      <path stroke="#E01E5A" d="M8 20v-7M3 13v-.1" />
    </svg>
  );
}

function DriveMark(props) {
  return (
    <svg viewBox="0 0 24 24" {...props}>
      <path fill="#188038" d="M8 3 1 16l3.5 6 7-13z" />
      <path fill="#F4B400" d="M8 3h8l7 13h-8z" />
      <path fill="#4285F4" d="M8 16h15l-3.5 6h-15z" />
    </svg>
  );
}

const groups = [
  {
    title: "Documents & conversations",
    description: "Find the agreements and conversations that explain a deduction.",
    sources: [
      ["Slack", "Internal chat", SlackMark, "bg-fuchsia-50 text-fuchsia-800", "Finance and sales channels for deduction context, internal decisions, and escalation threads."],
      ["Company docs", "Internal knowledge base", BookOpen, "bg-stone-100 text-stone-700", "AR playbooks, approval policies, and contract summaries."],
      ["Google Drive", "Shared files", DriveMark, "bg-emerald-50 text-emerald-800", "Signed agreements, proof of delivery, and invoice attachments in shared folders."],
      ["Microsoft Word", "Via SharePoint or OneDrive", FileText, "bg-blue-50 text-blue-800", "Contract amendments, signed addenda, and policy documents in .docx files."],
      ["Microsoft Teams", "Internal chat", MessagesSquare, "bg-indigo-50 text-indigo-800", "Handoff threads between account managers, fulfillment, and finance."],
      ["Email", "Outlook or Gmail", Mail, "bg-sky-50 text-sky-800", "Buyer remittance emails, deduction notices, replies, and attachments."],
    ],
  },
  {
    title: "Finance & operations",
    description: "Verify the transaction records behind an open balance.",
    sources: [
      ["ERP / accounting", "NetSuite or SAP", Landmark, "bg-amber-50 text-amber-800", "Invoices, credit memos, payment applications, and the open receivables ledger."],
      ["Company databases", "PostgreSQL or Snowflake", Database, "bg-cyan-50 text-cyan-800", "Approved views for customer, order, pricing, and invoice line data."],
      ["Bank feeds", "Statements and remittance", Banknote, "bg-green-50 text-green-800", "Deposits and bank statements used to match payments to open invoices."],
      ["Warehouse & logistics", "WMS or carrier records", Boxes, "bg-orange-50 text-orange-800", "Shipment quantities, delivery confirmations, and proof of delivery."],
    ],
  },
  {
    title: "External portals",
    description: "Collect records from the buyers and insurers involved in a case.",
    sources: [
      ["Buyer portals", "Customer AR portals", Store, "bg-rose-50 text-rose-800", "Deduction reason codes, buyer notices, and dispute history."],
      ["Insurer portals", "Trade credit insurance", ShieldCheck, "bg-violet-50 text-violet-800", "Policy documents, account statement requirements, and correspondence history."],
    ],
  },
];

export default function CompanyData() {
  const sourceCount = groups.reduce((count, group) => count + group.sources.length, 0);
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          Workspace
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Company Data</h1>
        <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Sources for investigating deductions, verifying payments, and assembling case evidence.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-4 rounded-xl border bg-white p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent">
            <Plug aria-hidden="true" className="size-4" />
          </span>
          <div className="space-y-1">
            <p className="text-sm font-semibold">Workspace connections</p>
            <p className="text-sm text-muted-foreground">
              Documents, conversations, and records across your workspace.
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2 pl-12 text-xs sm:pl-0">
          <Badge variant="outline" className="border-emerald-200 bg-emerald-50 px-3 py-1 text-emerald-800">
            {sourceCount} connected
          </Badge>
        </div>
      </div>

      {groups.map(({ title, description, sources: entries }, index) => (
        <section key={title} aria-labelledby={`source-group-${index}`} className="space-y-3">
          <div>
            <h2 id={`source-group-${index}`} className="text-lg font-semibold">{title}</h2>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
          <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {entries.map(([name, system, Icon, colors, evidence]) => (
              <li key={name} className="space-y-3 rounded-xl border bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <span className={`grid size-9 shrink-0 place-items-center rounded-lg ${colors}`}>
                    <Icon aria-hidden="true" className="size-5" />
                  </span>
                  <Badge
                    variant="outline"
                    className="border-emerald-200 bg-emerald-50 text-emerald-800"
                  >
                    Connected
                  </Badge>
                </div>
                <div>
                  <h3 className="text-sm font-semibold">{name}</h3>
                  <p className="text-xs text-muted-foreground">{system}</p>
                </div>
                <p className="text-sm leading-relaxed text-muted-foreground">{evidence}</p>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
