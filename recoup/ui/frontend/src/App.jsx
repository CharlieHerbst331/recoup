import { useEffect, useRef, useState } from "react";
import { LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { request, readLocation, writeLocation } from "@/lib/ui";
import WorkbenchSidebar from "@/components/workbench-sidebar";
import Dashboard from "@/components/dashboard";
import CasePage from "@/components/case-page";

export default function App() {
  const [data, setData] = useState(null),
    [detail, setDetail] = useState(null),
    [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(""),
    [error, setError] = useState("");
  const [focus, setFocus] = useState({ tab: "review" });
  const navigation = useRef({});
  const pending = useRef(false);
  useEffect(() => {
    request("dashboard")
      .then(setData)
      .catch((e) => setError(e.message));
    function followLocation() {
      const route = readLocation();
      if (route.caseId)
        navigation.current.openCase(route.caseId, {
          ...route.focus,
          history: false,
        });
      else navigation.current.home({ history: false });
    }
    followLocation();
    window.addEventListener("popstate", followLocation);
    window.addEventListener("hashchange", followLocation);
    return () => {
      window.removeEventListener("popstate", followLocation);
      window.removeEventListener("hashchange", followLocation);
    };
  }, []);
  async function openCase(id, options = {}) {
    const target = {
      tab: options.tab || "review",
      document: options.document || "",
      proposal: options.proposal || "",
      locator: options.locator || "",
      quote: options.quote || "",
    };
    if (selected === id && detail) {
      setFocus(target);
      if (options.history !== false) writeLocation(id, target);
      return;
    }
    if (pending.current) return;
    pending.current = true;
    setBusy("Opening case…");
    setError("");
    try {
      setDetail(await request(`cases/${encodeURIComponent(id)}`));
      setSelected(id);
      setFocus(target);
      if (options.history !== false) writeLocation(id, target);
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError(e.message);
    } finally {
      pending.current = false;
      setBusy("");
    }
  }
  async function act(action, payload = {}) {
    if (pending.current) return false;
    pending.current = true;
    setBusy(
      action === "advance"
        ? "Advancing time and reviewing cases…"
        : action === "fresh"
          ? "Starting a fresh simulation…"
          : "Updating case…",
    );
    setError("");
    try {
      const withCase = ["fresh", "open_database"].includes(action)
        ? payload
        : { ...payload, ...(selected ? { case_id: selected } : {}) };
      const result = await request(action, withCase);
      setData(result.dashboard);
      if (result.case) setDetail(result.case);
      const next = result.dashboard.journey?.current;
      if (
        ["submit", "advance", "run"].includes(action) &&
        next?.case_id === selected &&
        next.proposal_key
      ) {
        const target = { tab: "review", proposal: next.proposal_key };
        setFocus(target);
        writeLocation(selected, target);
      }
      if (["fresh", "open_database"].includes(action)) {
        setSelected(null);
        setDetail(null);
        setFocus({ tab: "review" });
        writeLocation(null, {});
      }
      return true;
    } catch (e) {
      setError(e.message);
      return false;
    } finally {
      pending.current = false;
      setBusy("");
    }
  }
  function home(options = {}) {
    window.scrollTo({ top: 0 });
    setFocus({ tab: "review" });
    if (options.history !== false) writeLocation(null, {});
    setSelected(null);
    setDetail(null);
  }
  navigation.current = { openCase, home };
  return (
    <SidebarProvider defaultOpen={false}>
      <WorkbenchSidebar
        data={data}
        selected={selected}
        openCase={openCase}
        home={home}
        act={act}
        busy={!!busy}
        error={error}
      />
      <SidebarInset className="min-w-0 bg-background">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b bg-white px-4 md:px-8">
          <SidebarTrigger aria-label="Toggle navigation" />
          <Separator orientation="vertical" className="h-4" />
          <button
            className="font-semibold tracking-tight"
            onClick={() => home()}
            disabled={!!busy}
          >
            Recoup
          </button>
          <div className="ml-auto">
            <Badge
              variant="outline"
              title={`Synthetic data · MOCK actions · LLM ${data?.llm || "fake"}. Nothing is sent externally.`}
            >
              Demo
            </Badge>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1100px] space-y-6 p-5 md:p-10">
          {busy && (
            <Alert role="status" className="border-0 bg-transparent px-0 py-1">
              <LoaderCircle className="animate-spin" />
              <AlertDescription>{busy}</AlertDescription>
            </Alert>
          )}
          {error && (
            <Alert variant="destructive" role="alert">
              <AlertTitle>Couldn’t complete that action</AlertTitle>
              <AlertDescription className="whitespace-pre-wrap">
                {error}
              </AlertDescription>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setError("")}
                className="mt-2"
              >
                Dismiss
              </Button>
            </Alert>
          )}
          {!data ? (
            <div className="space-y-5">
              <Skeleton className="h-16 w-2/3" />
              <Skeleton className="h-40 w-full" />
            </div>
          ) : selected && detail ? (
            <CasePage
              key={selected}
              detail={detail}
              focus={focus}
              navigate={(target) => openCase(selected, target)}
              journey={data.journey}
              openCase={openCase}
              act={act}
              home={home}
              busy={!!busy}
              error={error}
            />
          ) : (
            <Dashboard
              data={data}
              openCase={openCase}
              act={act}
              busy={!!busy}
            />
          )}
        </main>
      </SidebarInset>
    </SidebarProvider>
  );
}
