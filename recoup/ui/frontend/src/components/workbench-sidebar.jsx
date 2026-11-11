import { useState } from "react";
import {
  LayoutDashboard,
  Database,
  Settings2,
  LoaderCircle,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { ScrollBrand } from "@/components/brand/scroll-brand";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
export default function WorkbenchSidebar({
  data,
  page,
  selected,
  home,
  sources,
  act,
  busy,
  error,
}) {
  const { isMobile, setOpenMobile } = useSidebar();
  const [settings, setSettings] = useState(false),
    [days, setDays] = useState("1"),
    [db, setDb] = useState("");
  return (
    <Sidebar>
      <SidebarHeader className="px-6 py-7">
        <div className="flex items-center gap-2 text-xl font-semibold">
          <ScrollBrand forceState="expanded" disabled={busy} onClick={() => { home(); if (isMobile) setOpenMobile(false); }} />
          {isMobile && (
            <Button
              variant="ghost"
              size="icon"
              className="ml-auto"
              aria-label="Close navigation"
              onClick={() => setOpenMobile(false)}
            >
              <X />
            </Button>
          )}
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                isActive={page === "cases"}
                aria-current={page === "cases" ? "page" : undefined}
                disabled={busy}
                onClick={() => {
                  home();
                  if (isMobile) setOpenMobile(false);
                }}
              >
                <LayoutDashboard />
                <span>Cases</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                isActive={page === "sources"}
                aria-current={page === "sources" ? "page" : undefined}
                disabled={busy}
                onClick={() => {
                  sources();
                  if (isMobile) setOpenMobile(false);
                }}
              >
                <Database />
                <span>Company Data</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-4">
        <Dialog
          open={settings}
          onOpenChange={(open) => {
            setSettings(open);
            if (open) setDb(data?.database || "");
          }}
        >
          <DialogTrigger asChild>
            <Button
              variant="ghost"
              className="justify-start text-muted-foreground"
            >
              <Settings2 />
              Demo controls
            </Button>
          </DialogTrigger>
          <DialogContent className="max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Demo controls</DialogTitle>
              <DialogDescription>
                Synthetic data · MOCK actions · LLM {data?.llm || "fake"}. No
                external messages or payments.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-2 rounded-lg border p-4">
              <div className="flex items-center justify-between gap-4">
                <label htmlFor="live-model" className="text-sm font-medium">Real LLM</label>
                <Switch
                  id="live-model"
                  checked={data?.llm === "live"}
                  disabled={busy || (!data?.provider?.available && data?.llm !== "live")}
                  aria-describedby="live-model-help"
                  onCheckedChange={(live) => act("provider", { mode: live ? "live" : "fake" })}
                />
              </div>
              <p id="live-model-help" className="text-sm text-muted-foreground">
                {data?.llm === "live"
                  ? `Future agent runs use ${data?.provider?.model || "the configured model"}. Synthetic case context is sent to the provider; usage may be billed. All business actions remain MOCK.`
                  : "Off uses the offline demo agent. Turn on to use a real model with the same synthetic cases and simulation clock."}
              </p>
              {!data?.provider?.available ? (
                <p className="text-xs text-muted-foreground">
                  To enable, set <code>{data?.provider?.missing?.join(" and ") || "OPENAI_API_KEY and RECOUP_MODEL"}</code> on the Python server and restart it. Keep keys out of the browser.
                </p>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Model: {data.provider.model} · Server key configured, not verified. Switching preserves your progress and makes no model request.
                </p>
              )}
            </div>
            {busy && (
              <p role="status" className="flex items-center gap-2 text-sm">
                <LoaderCircle className="size-4 animate-spin" />
                Updating…
              </p>
            )}
            <p className="text-sm">
              Day {data?.clock.day ?? 0} · {data?.clock.date} · Next event:{" "}
              {data?.clock.next_due_day == null
                ? "none"
                : `day ${data.clock.next_due_day}`}
            </p>
            {error && (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={busy || data?.clock.next_due_day == null}
                onClick={() => act("advance", { to_next_due: true })}
              >
                Advance to next event
              </Button>
              <Button
                variant="outline"
                disabled={busy || !selected}
                onClick={() => act("run")}
              >
                Run agent
              </Button>
            </div>
            <form
              className="flex items-end gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                act("advance", { days: Number(days) });
              }}
            >
              <label className="space-y-2 text-sm">
                Days
                <Input
                  aria-label="Days"
                  type="number"
                  min="1"
                  step="1"
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                  required
                />
              </label>
              <Button variant="outline" disabled={busy}>
                Advance days
              </Button>
            </form>
            <details className="border-t pt-4 text-sm">
              <summary className="cursor-pointer">Run settings</summary>
              <div className="mt-4 space-y-4">
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={async () => {
                    if (await act("fresh")) {
                      setSettings(false);
                      setOpenMobile(false);
                    }
                  }}
                >
                  Start fresh demo
                </Button>
                <form
                  className="space-y-3"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    if (await act("open_database", { database: db }))
                      setSettings(false);
                  }}
                >
                  <label className="space-y-2">
                    Database path
                    <Input
                      value={db}
                      onChange={(e) => setDb(e.target.value)}
                      required
                    />
                  </label>
                  <Button variant="outline" disabled={busy}>
                    Open saved run
                  </Button>
                </form>
                <Button
                  variant="ghost"
                  disabled={busy}
                  onClick={() => act("load")}
                >
                  Load reviewer cases
                </Button>
              </div>
            </details>
          </DialogContent>
        </Dialog>
      </SidebarFooter>
    </Sidebar>
  );
}
