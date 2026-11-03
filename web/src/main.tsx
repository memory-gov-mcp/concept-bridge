import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { SearchPage } from "./components/SearchPage";
import "./style.css";

const mock = import.meta.env.DEV && import.meta.env.MODE === "mock";
const pages = [
  { hash: "#/", label: "查询" },
] as const;

function currentPage() {
  return pages.find((item) => item.hash === window.location.hash)?.hash ?? "#/";
}

function App() {
  const [page, setPage] = useState(currentPage);
  useEffect(() => {
    const changePage = () => {
      setPage(currentPage());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", changePage);
    return () => window.removeEventListener("hashchange", changePage);
  }, []);

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-8 sm:py-9">
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <a href="#/" className="font-black tracking-wide text-emerald-950">概念桥 <span className="ml-1 text-xs tracking-widest">CONCEPTBRIDGE</span></a>
          <nav aria-label="主导航" className="flex rounded-full border border-border bg-card p-1 text-sm font-semibold">
            {pages.map((item) => (
              <a key={item.hash} href={item.hash} aria-current={page === item.hash ? "page" : undefined}
                className={`rounded-full px-4 py-1.5 ${page === item.hash ? "bg-emerald-900 text-white" : "hover:bg-emerald-50"}`}>
                {item.label}
              </a>
            ))}
          </nav>
        </header>
        {page === "#/" && <SearchPage mock={mock} />}
      </div>
    </main>
  );
}

const root = createRoot(document.getElementById("root")!);

async function start() {
  if (mock) {
    const { worker } = await import("./mocks/browser");
    await worker.start({
      onUnhandledRequest(request, print) {
        if (new URL(request.url).pathname.startsWith("/api/v1/")) print.error();
      },
    });
  }
  root.render(<App />);
}

void start().catch(() => {
  root.render(<p role="alert" className="p-6">无法启动离线样例。请允许本站使用 Service Worker 后刷新。</p>);
});
