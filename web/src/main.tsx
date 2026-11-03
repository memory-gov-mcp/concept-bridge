import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { DemoPage } from "./components/DemoPage";
import { EvalPage } from "./components/EvalPage";
import { SearchPage } from "./components/SearchPage";
import "./style.css";

const mock = import.meta.env.DEV && import.meta.env.MODE === "mock";
const pages = [
  { hash: "#/", label: "查询" },
  { hash: "#/demo", label: "演示" },
  { hash: "#/eval", label: "评测" },
] as const;

function currentPage() {
  return pages.find((item) => item.hash === window.location.hash)?.hash ?? "#/";
}

function App() {
  const [page, setPage] = useState(currentPage);
  const content = useRef<HTMLDivElement>(null);
  const previousPage = useRef(page);
  useEffect(() => {
    const changePage = () => {
      setPage(currentPage());
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", changePage);
    return () => window.removeEventListener("hashchange", changePage);
  }, []);
  useEffect(() => {
    if (previousPage.current === page) return;
    previousPage.current = page;
    content.current?.focus({ preventScroll: true });
  }, [page]);

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-8 sm:py-9">
        <a href="#page-content" onClick={(event) => { event.preventDefault(); content.current?.focus(); }}
          className="sr-only focus:not-sr-only focus:mb-3 focus:inline-block focus:rounded-lg focus:bg-emerald-900 focus:px-4 focus:py-2 focus:text-white">
          跳到页面内容
        </a>
        <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <a href="#/" className="font-black tracking-wide text-emerald-950">概念桥 <span className="ml-1 text-xs tracking-widest">CONCEPTBRIDGE</span></a>
          <nav aria-label="主导航" className="flex rounded-full border border-border bg-card p-1 text-sm font-semibold">
            {pages.map((item) => (
              <a key={item.hash} href={item.hash} aria-current={page === item.hash ? "page" : undefined}
                className={`rounded-full px-4 py-1.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 ${page === item.hash ? "bg-emerald-900 text-white" : "hover:bg-emerald-50"}`}>
                {item.label}
              </a>
            ))}
          </nav>
        </header>
        <div id="page-content" ref={content} tabIndex={-1} className="focus:outline-none">
          {page === "#/" && <SearchPage mock={mock} />}
          {page === "#/demo" && <DemoPage mock={mock} />}
          {page === "#/eval" && <EvalPage mock={mock} />}
        </div>
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
