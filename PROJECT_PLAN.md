# Valtec 無人機模擬 MVP：實作計畫與進度

最後更新：2026-09-26

## 目前進度

- 目前里程碑：**七個實作階段均已完成，交付檔案已整理完成**。
- 下一個里程碑：**由使用者確認後，回覆原 Gmail 並提供原始碼與驗收影片**。
- 階段進度：**7 / 7 個階段完成**。
- MVP 核心驗收進度：**10 / 10 項完成**。
- 目前系統狀態：加入 heartbeat 自動重連後 image 已重建且 container healthy；最終完整 API 示範已通過，模擬無人機已降落、未解鎖（`armed: false`）。
- 已可使用的 API：`GET /status`、`POST /takeoff`、`POST /land`、`POST /goto`、`POST /rtl`。
- 第五階段驗證結果：API 與 QGC 已完成交替控制；QGC Go To 約 480.8 公尺後，API RTL 成功返航並降落。
- Swagger 測試介面：http://127.0.0.1:8000/docs

| 階段 | 狀態 | 結果 |
| --- | --- | --- |
| 0. 需求與 MVP 範圍 | ✅ 完成 | 已確定以最快完成可驗收版本為目標 |
| 1. Mac 開發環境 | ✅ 完成 | Docker、OrbStack、QGroundControl 可用 |
| 2. 模擬與通訊環境 | ✅ 完成 | ArduPilot、MAVLink-router、QGC 已連線 |
| 3. 起飛與降落 API | ✅ 完成 | 已用 API 執行並在 QGC 視覺驗證 |
| 4. 移動與返航 API | ✅ 完成 | `goto` 與 `rtl` 已通過 API 和 QGC 驗證 |
| 5. 完整整合驗收 | ✅ 完成 | API 與 QGC 交替控制已通過完整驗收 |
| 6. 文件、錄影與交付 | ✅ 完成 | README、示範腳本與 5 分 45 秒主要驗收影片已整理完成（另附 2 分 38 秒替代版） |

## 專案目標

在同一個 Docker container 中執行 ArduPilot 四軸無人機模擬器與 FastAPI，透過
MAVLink-router 同時連接 API 和 Mac 上的 QGroundControl。使用者可以從 Swagger
呼叫 API 控制模擬無人機，也可以從 QGroundControl 看到飛行狀態並下達控制指令。

MVP 完成時必須具備：

- [x] 一個指令可啟動完整 Docker 模擬環境。
- [x] QGroundControl 能透過 MAVLink-router 看見並監控模擬無人機。
- [x] API 能取得無人機目前狀態。
- [x] API 能控制起飛。
- [x] API 能控制降落。
- [x] API 能控制飛往指定經緯度與相對高度。
- [x] API 能控制 RTL（Return to Launch，回到起飛點）。
- [x] 有可操作的 API 測試介面（Swagger UI）。
- [x] 完成一輪從啟動、飛行控制到降落的整合驗收。
- [x] 錄製可證明需求已完成的操作影片。

## 系統架構

```text
Mac 上的 QGroundControl
        ▲
        │ UDP 14550
        │
Docker container
  ArduPilot Quad SITL ──TCP 5760──▶ MAVLink-router
                                      ▲        │
                                      │        └──UDP──▶ QGroundControl
                                      │ TCP 5770
                                      │
                                  FastAPI
                                      ▲
                                      │ localhost:8000
                                      │
                              Swagger / 程式碼呼叫
```

安全與範圍設定：

- 模擬位置固定使用 Canberra 測試場，不使用真實位置。
- FastAPI 只公開在 Mac 的 `127.0.0.1:8000`。
- API 同一時間只執行一個飛行動作。
- 起飛高度限制為 1–20 公尺。
- 僅完成技術測驗所需 MVP，不加入登入、資料庫、前端網站或多機管理。

## 階段 0：確認需求與 MVP 範圍

目標：先把題目翻成可實作、可驗收的項目，避免加入不必要功能。

- [x] 閱讀技術測驗邀請內容。
- [x] 用初學者能理解的方式說明 ArduPilot、Quad、QGroundControl 與 MAVLink-router。
- [x] 確認在目前這台 Apple Silicon Mac 上實作。
- [x] 確認以「最快完成」與「只做 MVP」為原則。
- [x] 確認採分階段方式：每一階段先說明，再實作與驗證。
- [x] 確認核心需求為 ArduPilot 模擬、QGC 控制、四個飛行 API 與操作錄影。

完成條件：需求、技術方向與不做的範圍都清楚。

## 階段 1：準備 Mac 開發環境

目標：讓 Mac 能執行 container，並準備 QGroundControl 作為視覺操作介面。

- [x] 檢查 Mac 晶片架構為 Apple Silicon `arm64`。
- [x] 檢查並啟動 OrbStack / Docker。
- [x] 用 `hello-world` 驗證 Docker 可執行 container。
- [x] 安裝 QGroundControl 5.1。
- [x] 驗證 QGroundControl 的簽章與 notarization。
- [x] 完成 QGroundControl 首次啟動設定。
- [x] 建立專案目錄 `valtec-technical-test`。

完成條件：Docker 可正常執行，QGroundControl 可正常開啟。

## 階段 2：建立模擬器與 MAVLink 通訊

目標：在 container 內啟動四軸無人機模擬器，並讓 Mac 上的 QGC 收到資料。

- [x] 建立 Ubuntu 24.04、`linux/amd64` Docker image。
- [x] 安裝官方 ArduCopter SITL 4.7.1。
- [x] 安裝 MAVLink-router v4。
- [x] 以 Quad 模型啟動 ArduPilot SITL。
- [x] 使用 Canberra 固定測試座標。
- [x] 設定 ArduPilot TCP 5760 到 MAVLink-router。
- [x] 設定 MAVLink-router UDP 14550 到 Mac 上的 QGroundControl。
- [x] 保留 MAVLink-router TCP 5770 給 FastAPI 使用。
- [x] 建立 Docker Compose 與健康檢查。
- [x] 確認 QGC 能看到模擬無人機、位置、高度與飛行模式。
- [x] 建立不會解鎖或移動無人機的連線檢查工具。

完成條件：container 顯示 healthy，QGC 顯示無人機並持續收到 telemetry。

## 階段 3：實作狀態、起飛與降落 API

目標：建立最小 FastAPI 控制層，先完成風險最低且容易視覺驗證的飛行流程。

- [x] 在同一個 container 中啟動 FastAPI。
- [x] 建立 FastAPI 與 MAVLink-router TCP 5770 的持續連線。
- [x] 實作 `GET /status`。
- [x] 回傳連線、模式、解鎖狀態、經緯度與相對高度。
- [x] 實作 `POST /takeoff`。
- [x] 驗證起飛高度只能是 1–20 公尺。
- [x] 起飛時切換到 `GUIDED`、解鎖、送出起飛命令並等待到達高度。
- [x] 實作 `POST /land`。
- [x] 降落時切換到 `LAND` 並等待落地與解除鎖定。
- [x] 避免同時執行兩個 API 飛行動作。
- [x] 將 ArduPilot 拒絕或逾時轉為可理解的 HTTP 409 錯誤。
- [x] 起飛失敗時嘗試切換 `LAND`，避免模擬機停留在危險狀態。
- [x] 透過 Swagger 實際起飛至約 3 公尺。
- [x] 在 QGC 視覺確認 `Flying`、`Guided` 與約 3 公尺高度。
- [x] 透過 Swagger 實際降落。
- [x] 在 QGC 視覺確認 `Land`、高度回到約 0 公尺與 `Ready`。
- [x] 驗證不合法高度回傳 422，重複降落回傳 409。

完成條件：API 起飛與降落都會等待動作完成，QGC 顯示的實際狀態和 API 回應一致。

## 階段 4：實作前往指定位置與返航 API

目標：補齊技術測驗要求的 `goto` 與 `rtl`，形成完整四個飛行控制 API。

- [x] 新增 `POST /goto` 的 request model。
- [x] 接收 `latitude`、`longitude` 與 `altitude_m`（相對起飛點高度）。
- [x] 驗證經緯度範圍與 MVP 高度限制。
- [x] 僅允許已起飛且已解鎖的無人機執行 `goto`。
- [x] 切換或維持 `GUIDED` 模式。
- [x] 透過 MAVLink 送出全球座標目標。
- [x] 等待無人機進入設定的水平距離與高度容許範圍。
- [x] 加入移動逾時與清楚的錯誤訊息。
- [x] 新增 `POST /rtl`。
- [x] 僅允許飛行中的無人機執行 RTL。
- [x] 切換到 `RTL` 模式。
- [x] 等待無人機回到起飛點、降落並解除鎖定。
- [x] 透過 API 驗證 `takeoff → goto → rtl`，並確認 Swagger 已列出新端點。
- [x] 在 QGC 地圖上目視確認位置移動、返航結果與最終降落。
- [x] 驗證尚未起飛時呼叫 `goto` 或 `rtl` 會得到 409。

完成條件：四個控制 API 全部存在，`goto` 與 `rtl` 的實際飛行結果可在 QGC 看見。

### 第四階段驗證紀錄

- [x] `/takeoff` 起飛至 3 公尺，回傳 HTTP 200；實際高度約 3.09 公尺。
- [x] `/goto` 向北移動約 10 公尺，回傳 HTTP 200。
- [x] 到達 `goto` 目標時，距離誤差約 1.33 公尺、高度誤差 0 公尺。
- [x] QGC 顯示 `Flying`、`Guided`、高度 3.0 公尺及距起飛點約 10.2 公尺。
- [x] `/rtl` 回傳 HTTP 200，最終回到起飛點、降落並解除鎖定。
- [x] QGC 顯示 `Ready`，高度及距起飛點均為 0.0 公尺。
- [x] 地面呼叫 `/goto` 或 `/rtl` 回傳 HTTP 409。
- [x] 不合法緯度回傳 HTTP 422。
- [x] 最終 Docker image 重建成功，container 狀態為 healthy。
- [x] Swagger 已重新載入並顯示全部五個端點。

## 階段 5：完整整合與人工驗收

目標：從乾淨啟動開始，證明 QGC 與 API 可以透過 MAVLink-router 交替控制同一台模擬無人機。

- [x] 停止並重新啟動 Docker Compose，確認不是依賴舊程序狀態。
- [x] 確認 container 健康檢查通過。
- [x] 確認 QGC 自動連線且顯示 `Ready`。
- [x] 用 `GET /status` 確認 API 讀到相同狀態。
- [x] 用 API 起飛至安全測試高度。
- [x] 用 API 執行一次 `goto`。
- [x] 在 QGC 使用 Fly / Go To 指令移動到另一個鄰近位置。
- [x] 用 API 再次讀取狀態，確認 QGC 控制造成的位置變化。
- [x] 用 API 執行 RTL，確認回到起飛點並落地。
- [x] 再次起飛並用 `/land` 驗證獨立降落流程。
- [x] 確認最後狀態為高度約 0 公尺、未解鎖且 QGC 顯示 `Ready`。
- [x] 測試 API 錯誤情境不會讓服務崩潰。
- [x] 檢查 Docker logs 沒有未處理例外。

完成條件：完整流程可重複執行，QGC 手動控制與四個 API 都有實際驗證證據。

### 第五階段驗證紀錄

- [x] 從 `docker compose down` 後重新啟動，container 自動回到 healthy。
- [x] QGC 自動重新連線，API 與 QGC 都顯示無人機已降落且未解鎖。
- [x] API 起飛至約 3.09 公尺，再向北移動約 10 公尺。
- [x] QGC Go To 將無人機移至 `-35.3626006, 149.1704705`，距起飛點約 480.8 公尺。
- [x] API 讀回 QGC 控制後的新座標，證明兩者控制同一台模擬無人機。
- [x] API RTL 從 QGC 目標點回到 `-35.3632609, 149.1652303`，降落並解除鎖定。
- [x] QGC 顯示 `Ready / RTL`、高度 0.0 公尺、距起飛點 0.0 公尺及完整紅色飛行軌跡。
- [x] 再次起飛至約 2.08 公尺，`/land` 成功降落並解除鎖定。
- [x] 最終 API 與 QGC 都顯示 `LAND`、高度 0.0 公尺、`armed: false`。
- [x] PreArm 未完成時回傳 409；地面呼叫 `/land`、`/goto` 回傳 409；不合法輸入回傳 422。
- [x] 修正長時間等待人工操作時的 MAVLink telemetry 佇列問題。
- [x] 修正後 image 重建成功、container healthy，logs 無未處理例外。

## 階段 6：文件、驗收錄影與交付

目標：讓審查者能快速啟動、理解、操作並確認題目已完成。

- [x] 更新 README 的架構、需求、啟動、停止與疑難排解說明。
- [x] 在 README 列出四個控制 API 與 request 範例。
- [x] 加入完整人工驗收步驟與預期畫面。
- [x] 準備一份程式碼呼叫範例，示範 `takeoff → goto → rtl/land`。
- [x] 確認全新啟動只需要 README 中列出的命令。
- [x] 清理不需要的產物與敏感資訊。
- [x] 確認影片採單一支 5–8 分鐘 MP4、至少 480p，截止日前回覆原 Gmail。
- [x] 錄製 container 啟動與 healthy 狀態。
- [x] 錄製 QGC 成功連線與即時 telemetry。
- [x] 錄製 Swagger 操作與 API 成功回應。
- [x] 錄製 QGC Fly / Go To 控制，以及 API 能讀到結果。
- [x] 驗證 RTL 回到起飛點、降落、解除鎖定，並將成功結果加入成片。
- [x] 最後從頭照 README 重跑一次完整驗收。
- [x] 整理原始碼、README、操作影片與交付說明。

完成條件：審查者只看 README 就能重現環境，影片能直接證明所有驗收項目。

### 第六階段目前紀錄

- [x] README 已補齊架構、環境、啟停方式、五個端點、curl / Postman 範例、人工驗收與疑難排解。
- [x] 新增 `scripts/demo_api.py`，可逐步執行完整 API 流程，並保留 QGC 手動 Go To 的人工確認點。
- [x] 新增 `RECORDING_GUIDE.md`，包含 5–8 分鐘分鏡、操作內容與成片檢查清單。
- [x] 新增 `.gitignore` 並掃描專案，未發現 API key、token、密碼或私鑰。
- [x] 依 README 命令重新 build 與啟動，container 顯示 healthy。
- [x] 實跑示範腳本時發現長時間運作後 MAVLink TCP 可能成為失效連線，已加入 heartbeat 遺失時自動重連。
- [x] 重建後再次完成 `takeoff 3 m → goto 10 m → rtl → takeoff 2 m → land`；最終 `armed: false`、高度 0.0 公尺。
- [x] 已確認影片採單一支 5–8 分鐘 MP4。
- [x] 已從邀請信確認：至少 480p，截止日前直接回覆原 Gmail。
- [x] 按照錄影腳本完成實際錄製並檢查成片。
- [x] 成片輸出為 `deliverables/valtec-acceptance-final.mp4`：H.264、1280×720、5 分 45 秒。**此檔為主要交付影片。**
- [x] 另有較短的替代版本 `deliverables/v2/valtec-acceptance-v2.mp4`（1600×1000、2 分 38 秒，由 `deliverables/v2/build_video.py` 重剪），僅供備用，非主要交付。
- [x] 成片保留 QGC、Swagger、起飛、降落、再次起飛及 QGC Go To 的操作畫面。
- [x] `/goto` 與 `/rtl` 實際 HTTP 200 結果已加入片尾驗證頁；RTL 最終為 `Ready`、`armed: false`、高度約 0 公尺。
- [x] 成片已完成抽幀、完整解碼與隱私檢查；未發現 Gmail、聊天內容、token、密碼或帳號資料。
- [x] 將影片、原始碼與說明文件整理成最終交付內容。
- [ ] 選配強化：若審查者要求每一步都必須直接錄到操作畫面，可補錄 QGC 點擊 Go To、Swagger `/goto` 200 與 `/rtl` 200 三個短鏡頭；目前成片以實際成功結果的片尾驗證頁呈現後兩項。
- [ ] 回覆原 Gmail（屬於對外送出動作，等待使用者最後確認）。

## 下一步

實作與驗收素材均已完成。下一步由使用者檢視
`deliverables/valtec-acceptance-final.mp4`（主要交付；2 分 38 秒的 v2 為較短替代版），並決定是否採用目前的 5 分 45 秒版本，或先補錄
三個直接操作鏡頭以降低嚴格驗收風險。確認無誤後，再回覆原 Gmail 並附上或提供原始碼
與影片連結。寄信屬於對外溝通，送出前必須取得使用者明確確認。
