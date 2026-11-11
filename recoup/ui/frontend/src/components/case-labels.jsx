import {
  Bell, CircleHelp, FileCheck2, FileMinus2, Handshake, History,
  MessageSquare, Scale,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { names } from "@/lib/ui";

const companyMarks = {
  "harbor market": {
    colors: "bg-sky-100 text-sky-900",
    art: <><path d="M4 13h16l-3 5H7zM11 13V4l6 7h-6" /><path d="M3 21c2-1.5 4-1.5 6 0 2-1.5 4-1.5 6 0 2-1.5 4-1.5 6 0" /></>,
  },
  "northwind grocers": {
    colors: "bg-emerald-100 text-emerald-900",
    art: <><path d="m12 3 3 6 6 3-6 3-3 6-3-6-6-3 6-3z" /><path d="m12 8 1 3 3 1-3 1-1 3-1-3-3-1 3-1z" fill="currentColor" stroke="none" /></>,
  },
  "juniper provisions": {
    colors: "bg-violet-100 text-violet-900",
    art: <><path d="M12 21V5m0 13-6-4m6 1 6-5m-6 2L8 8m4 2 3-5" /><circle cx="6" cy="14" r="1.5" fill="currentColor" stroke="none" /><circle cx="18" cy="10" r="1.5" fill="currentColor" stroke="none" /></>,
  },
};

export function CompanyMark({ buyer, large = false }) {
  const key = buyer.trim().toLowerCase();
  const mark = Object.hasOwn(companyMarks, key) ? companyMarks[key] : null;
  const initials = buyer.trim().split(/\s+/).slice(0, 2).map((word) => [...word][0]).join("").toUpperCase();
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-xl font-semibold ${large ? "size-11 sm:size-14" : "size-10"} ${mark?.colors || "bg-stone-100 text-stone-700"}`}
    >
      {mark ? (
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={large ? "size-6 sm:size-7" : "size-5"}
        >
          {mark.art}
        </svg>
      ) : initials || "—"}
    </span>
  );
}

const actionStyles = {
  credit_memo: [FileMinus2, "border-emerald-200 bg-emerald-50 text-emerald-800"],
  dispute: [Scale, "border-amber-200 bg-amber-50 text-amber-900"],
  insurer_notice: [Bell, "border-sky-200 bg-sky-50 text-sky-800"],
  claim_package: [FileCheck2, "border-violet-200 bg-violet-50 text-violet-800"],
  info_request: [CircleHelp, "border-cyan-200 bg-cyan-50 text-cyan-900"],
  follow_up: [MessageSquare, "border-indigo-200 bg-indigo-50 text-indigo-800"],
  correction: [History, "border-rose-200 bg-rose-50 text-rose-800"],
  counteroffer: [Handshake, "border-fuchsia-200 bg-fuchsia-50 text-fuchsia-800"],
};

export function ActionBadge({ kind }) {
  const [Icon, colors] = Object.hasOwn(actionStyles, kind) ? actionStyles[kind] : [
    CircleHelp, "border-stone-200 bg-stone-50 text-stone-700",
  ];
  return (
    <Badge variant="outline" className={`gap-1.5 px-2.5 py-1 ${colors}`}>
      <Icon aria-hidden="true" />
      {Object.hasOwn(names, kind) ? names[kind] : "Action"}
    </Badge>
  );
}
