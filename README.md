# MathPad

MathPad 是從 [engineeringpaper.xyz](https://engineeringpaper.xyz) / [mgreminger/EngineeringPaper.xyz](https://github.com/mgreminger/EngineeringPaper.xyz) fork 出來的專案，延續其以瀏覽器為核心的工程計算與數學筆記能力。

如果你要了解實際使用方式、功能介紹、教學文件或範例，請直接參考 EngineeringPaper.xyz 的官方資源：

- 產品網站: [engineeringpaper.xyz](https://engineeringpaper.xyz)
- 內建教學: [editable tutorial](https://engineeringpaper.xyz/CUsUSuwHkHzNyButyCHEng)
- 教學影片: [tutorial video](https://youtu.be/r7EZQVhcr5Q)
- 延伸說明: [learning EngineeringPaper.xyz](https://blog.engineeringpaper.xyz/engineeringpaperxyz-tutorial)

本 README 主要整理 `MathPad` 的開發、建置、測試與部署資訊。

## 專案概要

- 前端技術: Svelte 5 + Vite 7
- 計算核心: Pyodide、SymPy
- 本機預覽與測試環境: Wrangler Pages
- 端對端測試: Playwright

## 主要修改項目

1. 支援純量單位，以及 `giga`、`kilo` 等單位前綴。

## 開發需求

- Node.js 20 以上
- npm
- 建議使用 Unix-like shell、macOS、Linux 或 WSL2

## 安裝與本機開發

先安裝依賴：

```bash
npm install
```

啟動開發模式：

```bash
npm run dev
```

這個指令會先編譯 browser workers，再啟動 Vite dev server，預設使用 `127.0.0.1:8788`。

如果你透過反向代理、自訂網域或外部 host 存取 dev server，請建立 `.env.local`，並設定允許的 host：

```dotenv
MATHPAD_ALLOWED_HOSTS=your-dev-host.example.com
```

可參考 [`.env.example`](.env.example)。

## 建置與預覽

正式建置：

```bash
npm run build
```

本機預覽：

```bash
npm run preview
```

`preview` 會用 `wrangler pages dev dist --kv SHEETS --local` 啟動本機 Pages 環境，方便驗證接近部署環境的行為。

## 測試

首次使用 Playwright 時，先安裝瀏覽器：

```bash
npx playwright install
```

建立本機測試資料：

```bash
npm run test:seed
```

執行測試：

```bash
npm run test
```

## 常用指令

```bash
npm run dev
npm run build
npm run preview
npm run test:seed
npm run test
```

## 主要腳本說明

- `npm run dev`: 先編譯 workers，再啟動 Vite 開發伺服器
- `npm run build`: 建置前端輸出與 database worker
- `npm run build:workers`: 編譯 `src/pyodideWorker.ts`、`src/parser/parserWorker.ts`、`src/jediWorker.ts`
- `npm run preview`: 以 Wrangler Pages 在本機模擬部署環境
- `npm run test:seed`: 匯入測試用 KV 資料
- `npm run test`: 執行 Playwright 測試

---

# 手動部署 MathPad

`npm run build` 完成後，部署目標是 `dist/` 目錄。你可以把 `dist/` 的內容上傳到任何靜態網站主機、雲端儲存空間，或自己的 web server。

## 1. 建置

```bash
npm install
npm run build
```

建置完成後確認 `dist/` 存在：

```bash
ls dist
```

## 2. 本機驗證

先用靜態伺服器確認 build 結果可正常載入：

```bash
npx serve dist
```

或：

```bash
python3 -m http.server 8080 --directory dist
```

打開 `http://localhost:8080` 檢查畫面與功能。

## 3. 上傳到正式環境

把 `dist/` 內的檔案複製到你的網站根目錄，例如：

```bash
rsync -av --delete dist/ user@your-host:/var/www/mathpad/
```

如果你用的是靜態主機，通常就是把 `dist/` 全部上傳，然後把站點 root 指到該目錄。

## 4. 部署後檢查

部署完成後先確認：

- `index.html` 是網站入口
- 靜態資源能正常回傳
- `application/wasm` 類型有被正確送出
- 如果 Pyodide 相關功能出問題，再確認伺服器是否需要補 `Cross-Origin-Opener-Policy` 和 `Cross-Origin-Embedder-Policy` headers

## 5. 更新版本

之後要更新時，重跑一次建置並把新的 `dist/` 上傳：

```bash
git pull
npm install
npm run build
rsync -av --delete dist/ user@your-host:/var/www/mathpad/
```

---

# Web UI 使用方式

建議用本機 HTTP server 開啟。

```bash
cd MathPad
python3 -m http.server 8788 --directory dist
```

然後開啟：

```text
http://localhost:8788
```

# 以 user-mode systemd 啟動 Web UI

以下設定會以目前使用者的 systemd 執行本機 HTTP server；不需要 `sudo`。範例假設 repository 位於 `~/WorkSpace/MathPad`，並只監聽本機的 `127.0.0.1:8788`。若實際路徑或連接埠不同，請一併修改 unit 內容。

建立 user service：

```bash
mkdir -p ~/.config/systemd/user
editor ~/.config/systemd/user/mathpad.service
```

將以下內容貼入 `~/.config/systemd/user/mathpad.service`：

```ini
[Unit]
Description=mathpad local Web UI

[Service]
Type=simple
WorkingDirectory=%h/WorkSpace/MathPad
ExecStart=/usr/bin/python3 -m http.server 8788 --directory dist --bind 127.0.0.1
Restart=on-failure
RestartSec=2

[Install]
WantedBy=default.target
```

載入設定、設為登入後自動啟動，並立刻啟動：

```bash
systemctl --user daemon-reload
systemctl --user enable --now mathpad.service
systemctl --user status mathpad.service
```

若希望登出後服務仍繼續執行，可額外執行：

```bash
loginctl enable-linger "$USER"
```

查看服務日誌：

```bash
journalctl --user -u mathpad.service -f
```

# 移除 user-mode systemd 設定

停止服務、取消自動啟動並移除 unit 檔：

```bash
systemctl --user disable --now mathpad.service
rm ~/.config/systemd/user/mathpad.service
systemctl --user daemon-reload
systemctl --user reset-failed mathpad.service
```

若先前曾為此服務啟用 linger，且這個使用者沒有其他需要在登出後繼續執行的 user service，才執行：

```bash
loginctl disable-linger "$USER"
```


# 維護這個 Fork

建議保留 `origin` 與 `upstream` 兩個 remote：

```bash
origin   git@github.com:rcliu1975/MathPad
upstream https://github.com/mgreminger/EngineeringPaper.xyz
```

如果還沒設定 `upstream`，可執行：

```bash
git remote add upstream https://github.com/mgreminger/EngineeringPaper.xyz
```

檢查目前分支與上游的差異：

```bash
git fetch upstream
git rev-list --left-right --count HEAD...upstream/main
git log --oneline upstream/main..HEAD
git log --oneline HEAD..upstream/main
```

`git rev-list --left-right --count HEAD...upstream/main` 的輸出例如 `3 0`，表示本地分支比 `upstream/main` 多 3 個 commit，且沒有落後上游。

## 同步上游更新的建議流程

1. 先確認工作區乾淨，或至少知道哪些本地變更尚未提交。
2. 抓取上游最新內容：`git fetch upstream`
3. 檢查上游新增了哪些提交：`git log --oneline HEAD..upstream/main`
4. 視情況用 `merge` 或 `rebase` 將 `upstream/main` 整合進來
5. 重新執行 `npm install`、`npm run build`、必要時再跑 `npm run test`

## 依賴與上游背景

MathPad 繼承了 EngineeringPaper.xyz 的主要能力與依賴組合，包含：

- [Pyodide](https://pyodide.org)
- [SymPy](https://www.sympy.org)
- [MathLive](https://cortexjs.io/mathlive/)
- [Plotly](https://plotly.com/)
- [Quill](https://quilljs.com/)
- [Math.js](https://mathjs.org/)
- [ANTLR](https://www.antlr.org/)

如果你要了解原始產品設計、功能取向或對外使用情境，請回到上游專案與官方網站文件。

## Todo

1. 文字的 cell 加上 上標， 下標的功能

2. 試試看如果不需要 符號運算， 是否可以簡化 SymPy
