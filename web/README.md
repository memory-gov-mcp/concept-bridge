# 概念桥前端

需要 Node.js 24 和 npm。以下命令从项目根目录运行。

```bash
npm --prefix web ci
npm --prefix web run dev:mock
```

打开 http://127.0.0.1:5174/，首屏加载「锂枝晶抑制」样例。安装依赖后，Mock 模式只需要本地 Vite，浏览器通过 MSW 读取仓库样例。其他查询显示空结果。

接真实 API 时，分别在两个终端运行 `uv run task dev` 和 `npm --prefix web run dev`，打开 http://127.0.0.1:5173/。Vite 将 API 请求转发到本机 8000 端口。

```bash
npm --prefix web run test
npm --prefix web run typecheck
npm --prefix web run build
```
