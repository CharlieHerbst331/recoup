import { useState } from "react";
import {
  LayoutDashboard,
  PackageOpen,
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
  selected,
  home,
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
          <PackageOpen size={22} />
          Recoup
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
                isActive={!selected}
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
