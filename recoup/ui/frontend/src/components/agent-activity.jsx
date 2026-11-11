import { BookOpen, CheckCheck, CircleAlert, FilePenLine } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tag, Sources } from "@/lib/ui";

export default function AgentActivity({ detail, navigate }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold">How the agent reacted</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Recorded tool calls and rule outputs. In fake mode, this is a
          deterministic offline policy, not a live-model evaluation or a
          reasoning transcript.
        </p>
      </div>
      {detail.decision_changes?.length > 0 && (
        <Card className="border-amber-200 bg-amber-50/40 shadow-none">
          <CardHeader>
            <CardTitle className="text-base">
              What changed in the assessment
            </CardTitle>
            <CardDescription>
              Compared with the last different assessment recorded in this case.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {detail.decision_changes.map((change) => (
              <div key={change.line_id} className="space-y-2">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <strong>{change.line_id}</strong>
                  <Tag>{change.before}</Tag>
                  <span>to</span>
                  <Tag color="orange">{change.after}</Tag>
                </div>
                <p className="text-sm">
                  Supported deduction:{" "}
                  <strong>{change.supported_before}</strong> to{" "}
                  <strong>{change.supported_after}</strong>.
                </p>
                <p className="text-sm text-muted-foreground">
                  {change.rationale}
                </p>
                <Sources citations={change.citations} />
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      {detail.agent_runs?.map((run, index) => (
        <Card className="shadow-none" key={`${run.at}:${index}`}>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle className="text-base">
                {index === 0 ? "Latest investigation" : "Earlier investigation"}{" "}
                · Day {run.day}
              </CardTitle>
              <Tag>
                {run.mode} · {run.model || "recorded provider"}
              </Tag>
            </div>
            <CardDescription>{run.outcome}</CardDescription>
          </CardHeader>
          <CardContent>
            <details className="mb-4 rounded-lg border p-3">
              <summary className="cursor-pointer text-sm font-medium">
                Read{" "}
                {
                  run.tools.filter((tool) => tool.tool === "read_evidence")
                    .length
                }{" "}
                source documents
              </summary>
              <div className="mt-3 flex flex-wrap gap-2">
                {run.tools
                  .filter((tool) => tool.tool === "read_evidence")
                  .map((tool) => (
                    <Button
                      key={tool.evidence_id}
                      variant="outline"
                      size="sm"
                      className="h-auto whitespace-normal text-left"
                      onClick={() =>
                        navigate({
                          tab: "documents",
                          document: tool.evidence_id,
                        })
                      }
                    >
                      {tool.detail}
                    </Button>
                  ))}
              </div>
            </details>
            <ol className="space-y-3">
              {run.tools
                .filter((tool) => tool.tool !== "read_evidence")
                .map((tool, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-3 border-b pb-3 last:border-0"
                  >
                    <span
                      className={`mt-0.5 ${tool.ok ? "text-emerald-700" : "text-red-700"}`}
                    >
                      {tool.ok ? (
                        tool.tool === "read_evidence" ? (
                          <BookOpen size={16} />
                        ) : (
                          <CheckCheck size={16} />
                        )
                      ) : (
                        <CircleAlert size={16} />
                      )}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">
                        {tool.label}
                        {tool.occurrences > 1 && (
                          <span className="ml-2 text-xs font-normal text-muted-foreground">
                            {tool.occurrences} recorded calls
                          </span>
                        )}
                      </p>
                      {tool.detail && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {tool.detail}
                        </p>
                      )}
                    </div>
                    {tool.evidence_id && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          navigate({
                            tab: "documents",
                            document: tool.evidence_id,
                          })
                        }
                      >
                        Open source
                      </Button>
                    )}
                  </li>
                ))}
            </ol>
            <p className="mt-3 text-[11px] text-muted-foreground">
              {run.model_calls} recorded provider calls; {run.tool_calls}{" "}
              recorded tool calls. Financial amounts and gates are enforced by
              code.
            </p>
          </CardContent>
        </Card>
      ))}
      {!detail.agent_runs?.length && (
        <p className="text-sm text-muted-foreground">
          No investigation has been recorded. Run the agent from the Simulation
          lab.
        </p>
      )}
    </div>
  );
}
