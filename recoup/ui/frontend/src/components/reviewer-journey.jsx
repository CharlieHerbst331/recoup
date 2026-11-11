import { useState } from "react";
import {
  ArrowRight,
  CheckCheck,
  ChevronDown,
  FlaskConical,
  RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function ReviewerJourney({
  journey,
  openCase,
  act,
  busy,
  compact = false,
  currentCase = null,
  currentProposalKey = null,
  currentTab = "review",
}) {
  const [expanded, setExpanded] = useState(false);
  if (!journey) return null;
  const step = journey.current;
  return (
    <Card
      className="gap-0 border-[#d6dfb1] bg-[#f3f6e8] py-3 shadow-none"
      aria-label="Guided reviewer walkthrough"
    >
      <CardContent className="space-y-2 px-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs font-medium text-[#59692f]">
            <FlaskConical size={16} />
            GUIDED REVIEWER DEMO
            <Badge variant="outline" className="bg-white/70">
              {journey.complete
                ? "Complete"
                : `${journey.completed} of ${journey.total} steps`}
            </Badge>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            <ChevronDown size={14} />
            {expanded ? "Hide outline" : "Demo outline"}
          </Button>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h2 className="text-base font-semibold">
              {step?.title ||
                journey.completion_title ||
                "Walkthrough complete"}
            </h2>
            {!compact && (
              <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted-foreground">
                {step?.description ||
                  journey.completion_summary ||
                  "Inspect each case outcome and its recorded actions."}
              </p>
            )}
          </div>
          {compact &&
          step?.case_id === currentCase &&
          step.action === "review" &&
          currentTab === "review" &&
          currentProposalKey === step.proposal_key ? (
            <Badge variant="outline">Review, approve, then submit below</Badge>
          ) : step ? (
            <Button
              disabled={busy}
              onClick={() =>
                step.action === "advance"
                  ? act("advance", { to_next_due: true })
                  : openCase(step.case_id, {
                      tab: "review",
                      proposal: step.proposal_key || "",
                    })
              }
            >
              {step.action === "advance" ? "Advance to next event" : step.cta}
              <ArrowRight />
            </Button>
          ) : (
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => act("fresh")}
            >
              <RotateCcw />
              Start another walkthrough
            </Button>
          )}
        </div>
        <progress
          className="h-1.5 w-full overflow-hidden rounded-full accent-[#75853f]"
          max={journey.total}
          value={journey.completed}
          aria-label="Completed walkthrough steps"
        />
        {journey.out_of_order && !journey.complete && (
          <p role="status" className="text-xs text-amber-900">
            Time advanced before an earlier correspondence step. You can explore
            the current records or start fresh to follow the complete correction
            story.
          </p>
        )}
        {expanded && (
          <div className="grid gap-3 border-t border-[#d6dfb1] pt-3 md:grid-cols-3">
            {["Review", "Insurance", "Outcomes"].map((phase) => (
              <div key={phase}>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide">
                  {phase}
                </h3>
                <ol className="space-y-2">
                  {journey.steps
                    .filter((s) => s.phase === phase)
                    .map((s) => (
                      <li
                        key={s.id}
                        className={`flex gap-2 text-xs leading-relaxed ${s.state === "upcoming" ? "text-muted-foreground" : "text-foreground"}`}
                      >
                        {s.state === "complete" ? (
                          <CheckCheck
                            size={14}
                            className="mt-0.5 shrink-0 text-emerald-700"
                          />
                        ) : (
                          <span className="w-3.5 shrink-0 font-semibold">
                            {s.state === "current" ? "•" : "–"}
                          </span>
                        )}
                        <span>
                          {s.title}
                          {s.state === "current" && (
                            <strong className="ml-1"> · Next</strong>
                          )}
                        </span>
                      </li>
                    ))}
                </ol>
              </div>
            ))}
          </div>
        )}
        {!compact && (
          <p className="text-[11px] text-muted-foreground">
            {journey.disclosure}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
