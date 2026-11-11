import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { useState } from "react";
import { BookOpen, FileText, GitCompare, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { nice, Tag, DataTable } from "@/lib/ui";

function SourceReader({ document, locator, quote }) {
  const e = document.evidence;
  return (
    <div className="space-y-5">
      <div>
        <div className="mb-3 flex flex-wrap gap-2">
          <Tag color={e.active ? "green" : "gray"}>
            v{e.version} · {e.active ? "Current" : "Superseded"}
          </Tag>
          <Tag>{nice(e.kind)}</Tag>
          <Tag>{e.readable ? "Readable source" : "Not readable"}</Tag>
        </div>
        <h3 className="text-lg font-semibold">
          {e.title.replace(/^SYNTHETIC — /, "")}
        </h3>
      </div>
      {quote && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
          <p className="mb-1 text-xs font-medium text-amber-900">
            You followed a citation
          </p>
          <blockquote className="whitespace-pre-wrap">“{quote}”</blockquote>
          <p className="mt-1 text-xs text-muted-foreground">
            {locator?.replace(/^fields\./, "").replaceAll(".", " ")}
          </p>
        </div>
      )}
      {document.source_facts?.length > 0 && (
        <dl className="grid gap-3 rounded-lg border bg-muted/30 p-4 sm:grid-cols-2">
          {document.source_facts?.map((f) => (
            <div
              key={f.key}
              className={
                locator === `fields.${f.key}` ? "rounded bg-amber-100 p-2" : ""
              }
            >
              <dt className="text-xs text-muted-foreground">{f.label}</dt>
              <dd className="mt-1 whitespace-pre-wrap text-sm font-medium">
                {f.value}
              </dd>
              {["ocr", "vision", "model_extracted"].includes(f.trust) && (
                <Tag color="orange">{nice(f.trust)} · review required</Tag>
              )}
            </div>
          ))}
        </dl>
      )}
      {e.text && (
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <BookOpen size={14} />
            Source document text · SYNTHETIC
          </p>
          <div className="whitespace-pre-wrap rounded-lg border bg-white p-5 text-sm leading-7">
            {e.text}
          </div>
        </div>
      )}
      {e.failure && (
        <p className="text-sm text-red-700">
          Document processing: {nice(e.failure)}
        </p>
      )}
    </div>
  );
}

export default function Documents({
  detail,
  act,
  busy,
  error,
  focus,
  navigate,
}) {
  const [adding, setAdding] = useState(false),
    [json, setJson] = useState(""),
    [file, setFile] = useState(null),
    [localError, setLocalError] = useState("");
  const chosen =
    detail.documents.find((d) => d.evidence.evidence_id === focus.document) ||
    detail.documents.find((d) => d.evidence.active) ||
    detail.documents[0];
  const versions = chosen
    ? detail.documents
        .filter((d) => d.evidence.doc_ref === chosen.evidence.doc_ref)
        .sort((a, b) => a.evidence.version - b.evidence.version)
    : [];
  async function add(e) {
    e.preventDefault();
    setLocalError("");
    try {
      let upload;
      if (file) {
        if (file.size > 5 * 1024 * 1024)
          throw new Error("Choose a file smaller than 5 MB.");
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result).split(",")[1]);
          reader.onerror = () =>
            reject(new Error("The selected file could not be read."));
          reader.readAsDataURL(file);
        });
        upload = { name: file.name, base64 };
      }
      if (
        await act("add_evidence", {
          case_id: detail.view.case_id,
          document_json: json,
          upload,
        })
      )
        setAdding(false);
    } catch (e) {
      setLocalError(e.message);
    }
  }
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">Case documents</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Select a record to read it. Source links from drafts and agent
            activity open the relevant record here.
          </p>
        </div>
        <Dialog open={adding} onOpenChange={setAdding}>
          <DialogTrigger asChild>
            <Button variant="outline" disabled={busy}>
              <Plus />
              Add supporting document
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add supporting document</DialogTitle>
              <DialogDescription>
                Supply SYNTHETIC evidence in BundleDoc JSON format, with the
                referenced file if needed.
              </DialogDescription>
            </DialogHeader>
            {(error || localError) && (
              <p role="alert" className="text-sm text-destructive">
                {localError || error}
              </p>
            )}
            <form onSubmit={add} className="space-y-4">
              <label className="block space-y-2 text-sm">
                <span>Document description (JSON)</span>
                <Textarea
                  value={json}
                  onChange={(e) => setJson(e.target.value)}
                  rows={8}
                  required
                />
              </label>
              <label className="block space-y-2 text-sm">
                <span>Document file (optional, up to 5 MB)</span>
                <Input
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
              </label>
              <Button disabled={busy}>Add document</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>
      <div className="lg:hidden">
        <Select
          value={chosen?.evidence.evidence_id || ""}
          onValueChange={(document) => navigate({ tab: "documents", document })}
        >
          <SelectTrigger className="w-full" aria-label="Choose document">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {detail.documents.map((d) => (
              <SelectItem
                key={d.evidence.evidence_id}
                value={d.evidence.evidence_id}
              >
                {d.evidence.title.replace(/^SYNTHETIC — /, "")} · v
                {d.evidence.version}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="grid items-start gap-4 lg:grid-cols-[235px_1fr]">
        <Card className="hidden gap-0 py-2 shadow-none lg:block">
          <CardContent className="space-y-1 px-2">
            {detail.documents.map((d) => (
              <Button
                key={d.evidence.evidence_id}
                variant={chosen === d ? "secondary" : "ghost"}
                className="h-auto w-full items-start justify-start whitespace-normal py-3 text-left"
                onClick={() =>
                  navigate({
                    tab: "documents",
                    document: d.evidence.evidence_id,
                  })
                }
              >
                <FileText className="mt-0.5 shrink-0" />
                <span>
                  <span className="block text-sm">
                    {d.evidence.title.replace(/^SYNTHETIC — /, "")}
                  </span>
                  <span className="mt-1 block text-[11px] text-muted-foreground">
                    v{d.evidence.version} ·{" "}
                    {d.evidence.active ? "Current" : "Superseded"}
                  </span>
                </span>
              </Button>
            ))}
          </CardContent>
        </Card>
        <Card className="shadow-none">
          <CardContent className="space-y-5 pt-5">
            {chosen ? (
              <>
                {versions.length > 1 && (
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button variant="outline" size="sm">
                        <GitCompare />
                        Compare document versions
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
                      <DialogHeader>
                        <DialogTitle>
                          Compare {chosen.evidence.doc_ref} versions
                        </DialogTitle>
                        <DialogDescription>
                          The original and revised records remain available. The
                          agent’s changed assessment is recorded separately in
                          Agent activity.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-5 md:grid-cols-2">
                        {[versions[0], versions.at(-1)].map((d) => (
                          <SourceReader
                            key={d.evidence.evidence_id}
                            document={d}
                          />
                        ))}
                      </div>
                    </DialogContent>
                  </Dialog>
                )}
                <SourceReader
                  document={chosen}
                  locator={focus.locator}
                  quote={focus.quote}
                />
                <Accordion type="single" collapsible>
                  <AccordionItem value="fields">
                    <AccordionTrigger>
                      Extracted fields and provenance
                    </AccordionTrigger>
                    <AccordionContent className="space-y-3">
                      <p className="text-xs text-muted-foreground">
                        {chosen.evidence.evidence_id} ·{" "}
                        {nice(chosen.evidence.method)}
                      </p>
                      <DataTable rows={chosen.fields} />
                      {chosen.fields
                        .filter((f) =>
                          ["ocr", "vision"].includes(f.field_trust),
                        )
                        .map((f) => (
                          <div
                            key={f.field}
                            className="flex justify-between gap-3 text-xs"
                          >
                            <span>
                              {f.field}: {f.value} · {f.field_trust}
                            </span>
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={busy}
                              onClick={() =>
                                act("confirm_field", {
                                  evidence_id: chosen.evidence.evidence_id,
                                  field: f.field,
                                })
                              }
                            >
                              Confirm field
                            </Button>
                          </div>
                        ))}
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                No source records are available.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
