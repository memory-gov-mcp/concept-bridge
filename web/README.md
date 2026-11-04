# 概念桥前端

需要 Node.js 24 和 npm。以下命令从项目根目录运行。

```bash
npm --prefix web ci
npm --prefix web run dev:mock
```

打开 http://127.0.0.1:5174/，首屏加载「锂枝晶抑制」样例。安装依赖后，Mock 模式只需要本地 Vite，浏览器通过 MSW 读取仓库样例。其他查询显示空结果。

- **查询** `#/` 有三个预置问题。可切换目标桥、拖动图中节点、缩放、重播或跳过桥接动画。结果卡支持用鼠标或键盘高亮 API 返回的引用原文片段。
- **演示** `#/demo` 用 `→` 和 `←` 切换六屏。离线回放使用仓库提供的「锂枝晶抑制」样例与评测快照。其余两个预置问题可切换到实时查询，离线时会注明缺少快照。
- **评测** `#/eval` 读取 `/api/v1/eval/report`。Mock 模式由 MSW 提供仓库评测快照，实时模式由 FastAPI 提供报告。

接真实 API 时，分别在两个终端运行 `uv run task dev` 和 `npm --prefix web run dev`，打开 http://127.0.0.1:5173/。Vite 将 API 请求转发到本机 8000 端口。装好 `fixtures/corpus500.zip` 后，三个预置问题各自返回不同的双域图。

```bash
npm --prefix web run test
npm --prefix web run typecheck
npm --prefix web run build
```
