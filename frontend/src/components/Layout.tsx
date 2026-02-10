import { LayoutDashboard } from "lucide-react";

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="dark min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
        <div className="flex h-14 items-center gap-3 px-6">
          <LayoutDashboard className="h-6 w-6 text-indigo-400" />
          <h1 className="text-lg font-bold">SbioChat Dashboard</h1>
        </div>
      </header>
      <main className="mx-auto max-w-7xl p-6">{children}</main>
      <footer className="border-t border-border py-4 text-center text-sm text-muted-foreground">
        Contact: jisung.jang@samsung.com
      </footer>
    </div>
  );
}
