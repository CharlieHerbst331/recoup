import { useEffect, useRef, useState } from "react";
import { LoaderCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import CompanyData from "@/components/company-data";
import { ScrollBrand } from "@/components/brand/scroll-brand";

export default function App() {
  const [data, setData] = useState(null),
    [detail, setDetail] = useState(null),
    [selected, setSelected] = useState(null);
  const [busy, setBusy] = useState(""),
    [error, setError] = useState("");
  const [focus, setFocus] = useState({ tab: "review" });
  const [page, setPage] = useState("cases");
  const navigation = useRef({});
  const routeVersion = useRef(0);
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
      else navigation.current.showPage(route.page, { history: false });
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
    const version = ++routeVersion.current;
    setBusy("Opening case…");
    setError("");
    try {
      const result = await request(`cases/${encodeURIComponent(id)}`);
      if (routeVersion.current !== version) return;
      setDetail(result);
      setSelected(id);
      setFocus(target);
      setPage("cases");
      if (options.history !== false) writeLocation(id, target);
      window.scrollTo({ top: 0 });
    } catch (e) {
      if (routeVersion.current === version) setError(e.message);
    } finally {
      pending.current = false;
      setBusy("");
    }
  }
  async function act(action, payload = {}) {
    if (pending.current) return false;
    pending.current = true;
    const version = routeVersion.current;
    setBusy(
      action === "advance"
        ? "Advancing time and reviewing cases…"
        : action === "fresh"
          ? "Starting a fresh simulation…"
          : action === "provider"
            ? "Switching model mode…"
            : "Updating case…",
    );
    setError("");
    try {
      const withCase = ["fresh", "open_database"].includes(action)
        ? payload
        : { ...payload, ...(selected ? { case_id: selected } : {}) };
      const result = await request(action, withCase);
      setData(result.dashboard);
      if (routeVersion.current !== version) return true;
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
        home();
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
  function showPage(nextPage, options = {}) {
    routeVersion.current += 1;
    window.scrollTo({ top: 0 });
    setFocus({ tab: "review" });
    if (options.history !== false) writeLocation(null, {}, nextPage);
    setPage(nextPage);
    setSelected(null);
    setDetail(null);
  }
  const home = () => showPage("cases");
  const sources = () => showPage("sources");
  navigation.current = { openCase, showPage };
  return (
    <SidebarProvider defaultOpen={false}>
      <WorkbenchSidebar
        data={data}
        page={page}
        selected={selected}
        home={home}
        sources={sources}
        act={act}
        busy={!!busy}
        error={error}
      />
      <SidebarInset className="min-w-0 bg-background">
        <header className="sticky top-0 z-20 grid shrink-0 grid-cols-[auto_1fr_auto] items-center gap-x-4 border-b bg-white px-4 pt-2 md:px-8 lg:h-16 lg:pt-0">
          <div className="col-start-1 row-start-1 flex items-center gap-3">
            <SidebarTrigger aria-label="Toggle navigation" />
            <span aria-hidden="true" className="h-4 w-px bg-border" />
            <ScrollBrand onClick={home} disabled={!!busy} />
          </div>
          <nav aria-label="Workspace" className="col-span-3 row-start-2 flex gap-5 lg:col-span-1 lg:col-start-2 lg:row-start-1 lg:ml-5 lg:h-full">
            {[["cases", "Cases", home], ["sources", "Company Data", sources]].map(
              ([key, label, go]) => (
                <button
                  key={key}
                  type="button"
                  aria-current={page === key ? "page" : undefined}
                  disabled={!!busy}
                  onClick={go}
                  className="whitespace-nowrap border-b-2 border-transparent px-1 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground aria-[current=page]:border-foreground aria-[current=page]:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2"
                >
                  {label}
                </button>
              ),
            )}
          </nav>
          <div className="col-start-3 row-start-1 justify-self-end">
            <Badge
              variant="outline"
              title={`SYNTHETIC data · MOCK actions · LLM ${data?.llm || "fake"}.${data?.llm === "live" ? " Synthetic case context is sent to the model provider." : " Offline agent; no model requests."}`}
            >
              {data?.llm === "live" ? "Demo · Live LLM" : "Demo"}
            </Badge>
          </div>
        </header>
        <div className="mx-auto w-full max-w-[1100px] space-y-6 p-5 md:p-10">
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
          {page === "sources" ? (
            <CompanyData />
          ) : !data ? (
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
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
