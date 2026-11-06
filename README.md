# Valtec 技術測驗：無人機模擬 MVP

本專案在**同一個 Docker container** 中執行 ArduPilot 四軸無人機模擬器、
MAVLink-router 與 FastAPI。Mac 上的 QGroundControl（QGC）可觀看及控制同一台
模擬無人機，API 則提供起飛、降落、前往座標與返航功能。

程式與整合驗收均已完成，驗收錄影位於 [`deliverables/`](deliverables/)
（見下方「交付影片」）。完整進度請見 [PROJECT_PLAN.md](PROJECT_PLAN.md)，錄影腳本請見
[RECORDING_GUIDE.md](RECORDING_GUIDE.md)。

> 本專案只控制軟體模擬器，不會連接或操作真實無人機。

## 交付影片

驗收錄影放在 [`deliverables/`](deliverables/)，內容為依「人工整合驗收」流程，同時顯示
終端機、Swagger/API 與 QGC，示範 `status → takeoff → land → takeoff → QGC Go To →
goto → rtl`。

| 檔案 | 長度 | 解析度 | 說明 |
| --- | --- | --- | --- |
| **[`deliverables/valtec-acceptance-final.mp4`](deliverables/valtec-acceptance-final.mp4)（主要交付）** | 5 分 45 秒 | 1280×720 | 完整版驗收錄影，為正式交付影片 |
| [`deliverables/v2/valtec-acceptance-v2.mp4`](deliverables/v2/valtec-acceptance-v2.mp4) | 2 分 38 秒 | 1600×1000 | 較短的替代版本（精簡重剪，符合 [RECORDING_GUIDE.md](RECORDING_GUIDE.md) 的 3 分鐘內目標），非主要交付 |

其他檔案：

- `deliverables/video-cards/`：影片的片頭、章節與片尾字卡（PNG / SVG / 文字）。
- `deliverables/v2/build_video.py`、`marks.txt`：精簡版的剪輯腳本與時間標記。
- 原始錄影（`*.mov`、`deliverables/v2/raw-cleanshot.mp4`，合計約 16 GB）超過 GitHub
  的 100 MB 單檔限制，**不在此 repo 中**，僅保留在原作者本機。

## 系統架構

```text
Mac
├─ 瀏覽器 / Postman ──HTTP 8000──────────────┐
└─ QGroundControl ◀──UDP 14550───────────┐  │
                                         │  │
Docker container                         │  │
  ArduPilot Quad SITL ──TCP 5760──▶ MAVLink-router
                                         │  ▲
                                         │ TCP 5770
                                         ▼  │
                                       FastAPI
```

MAVLink-router 像「轉接器」：它把 ArduPilot 的即時資料同時送給 QGC 和 FastAPI，
也把兩邊的控制指令送回同一台模擬無人機。

## 執行環境

已驗證的環境：

- Apple Silicon Mac（`arm64`）。
- OrbStack / Docker。
- QGroundControl 5.1。
- Container：Ubuntu 24.04、`linux/amd64`。
- ArduCopter SITL 4.7.1、MAVLink-router v4。

模擬器使用 Canberra 測試座標 `-35.363261, 149.165230`，不是使用者的真實位置。

## 快速啟動

1. 開啟 OrbStack（或其他 Docker Desktop 相容環境）。
2. 開啟 QGroundControl，保持預設 UDP 自動連線設定。
3. 在本專案目錄執行：

```sh
docker compose up --build -d
docker compose ps
```

第一次 build 需要下載與編譯相依套件，之後啟動會較快。等待 `docker compose ps`
顯示 `healthy`，以及 QGC 左上角顯示 `Ready`，再開始操作。

開啟 API 測試介面：

- Swagger UI：http://127.0.0.1:8000/docs
- API 狀態：http://127.0.0.1:8000/status

只有 `127.0.0.1:8000` 會公開到 Mac，不會開放給區域網路的其他裝置。

## API 一覽

| 方法與路徑 | 用途 | Request body | 執行前條件 |
| --- | --- | --- | --- |
| `GET /status` | 讀取模式、解鎖、位置與高度 | 無 | 無 |
| `POST /takeoff` | 切到 Guided、解鎖並起飛 | `altitude_m` | 已落地且 QGC 顯示 Ready |
| `POST /goto` | 飛到指定經緯度與高度 | `latitude`、`longitude`、`altitude_m` | 必須已在飛行中 |
| `POST /rtl` | 回到起飛點並降落 | 無 | 必須已在飛行中 |
| `POST /land` | 在目前位置降落 | 無 | 必須已在飛行中 |

題目要求的四個控制 API 是 `takeoff`、`goto`、`rtl`、`land`；`status` 是為了驗證而
額外提供的唯讀 API。控制 API 一次只會執行一個動作，HTTP 200 表示該動作已完成。

### 1. 查看狀態

```sh
curl -s http://127.0.0.1:8000/status
```

### 2. 起飛到 3 公尺

```sh
curl -s -X POST http://127.0.0.1:8000/takeoff \
  -H 'Content-Type: application/json' \
  -d '{"altitude_m":3}'
```

### 3. 飛到指定位置

以下範例約為起飛點北方 10 公尺：

```sh
curl -s -X POST http://127.0.0.1:8000/goto \
  -H 'Content-Type: application/json' \
  -d '{"latitude":-35.363170,"longitude":149.165230,"altitude_m":3}'
```

`altitude_m` 代表**相對起飛點的目標高度（公尺）**。例如目前飛在 3 公尺，傳入
`5` 代表飛到相對起飛點 5 公尺，不是再上升 5 公尺，也不是海拔高度。

### 4A. 返航並降落

```sh
curl -s -X POST http://127.0.0.1:8000/rtl
```

### 4B. 原地降落

`rtl` 和 `land` 是兩種不同的收尾方式。若要測試 `land`，請在另一次起飛後呼叫：

```sh
curl -s -X POST http://127.0.0.1:8000/land
```

## 用 Postman 測試

有 JSON body 的 `/takeoff` 和 `/goto` 必須選：

1. `Body`
2. `raw`
3. 右側格式選 `JSON`

不要選 `form-data`。例如 `/takeoff` 的 body 是：

```json
{
  "altitude_m": 3
}
```

`/goto` 的 body 是：

```json
{
  "latitude": -35.363170,
  "longitude": 149.165230,
  "altitude_m": 3
}
```

`/rtl` 和 `/land` 不需要 body。

常見 HTTP 狀態：

- `200`：動作已完成。
- `409`：目前飛行狀態不允許這個動作，例如尚未起飛就呼叫 `/goto`。
- `422`：request 格式或欄位不正確，例如用 `form-data` 或漏掉必要欄位。

## 自動化 API 示範

主機端只需要 Python 3，不需額外安裝套件。QGC 顯示 `Ready` 後執行：

```sh
python3 scripts/demo_api.py
```

腳本會示範：

```text
status → takeoff 3 m → land → takeoff 3 m → 暫停讓你用 QGC Go To
       → status 驗證 QGC 結果 → goto 約 10 m → rtl
```

每個會移動無人機的步驟前都有提示；按 Enter 才會繼續。若只想測 API、不測
QGC 手動 Go To，可用：

```sh
python3 scripts/demo_api.py --skip-qgc
```

## 人工整合驗收

建議同時顯示終端機、Swagger 與 QGC：

1. 依「快速啟動」啟動，確認 container 為 `healthy`、QGC 顯示 `Ready`。
2. 呼叫 `GET /status`，預期 `armed: false`、高度接近 0。
3. 呼叫 `/takeoff`（3 公尺），預期 API 200；QGC 顯示 `Flying / Guided`、高度約 3 公尺。
4. 呼叫 `/land`，確認在目前位置降落、解除鎖定，QGC 回到 `Ready`。
5. 再次呼叫 `/takeoff`（3 公尺）。
6. 在 QGC Fly 畫面使用 Go To，選另一個鄰近且安全的位置。
7. 等待移動完成，再呼叫 `/status`；座標應反映 QGC 剛才的移動結果。
8. 呼叫 `/goto`，預期 API 200；QGC 地圖上的無人機移到指定座標附近。
9. 呼叫 `/rtl`；QGC 應顯示返航、回到起飛點、降落，最後回到 `Ready`。
10. 最後呼叫 `/status`，預期 `armed: false`、高度接近 0。

QGC 的 Go To 請選起飛點附近，錄影示範約 10–30 公尺即可，不需要飛數百公尺。

## 不起飛的連線檢查

```sh
docker compose ps
docker compose exec simulator python /opt/sitl/check_connection.py
```

預期結果：container 為 `healthy`；工具輸出 heartbeat、經緯度和 `armed: false`；
QGC 同時持續顯示 telemetry。

## 查看記錄與停止

查看記錄：

```sh
docker compose logs -f
```

按 `Ctrl+C` 只會停止顯示 logs，不會停止 container。停止整套環境：

```sh
docker compose down
```

模擬器參數與記錄保存在 Docker named volume。若需要完全清除保存資料，可自行使用
`docker compose down --volumes`；一般操作不需要執行。

## 疑難排解

### QGC 尚未顯示 Ready

剛啟動時 ArduPilot 需要初始化 GPS、陀螺儀與起飛點。先等待約 30–60 秒，不要在
`Not Ready` 或 `Need Position Estimate` 時起飛。可用以下命令確認狀態：

```sh
docker compose ps
docker compose logs --tail=100 simulator
```

### Postman 回傳 422

確認 Body 使用 `raw` + `JSON`，Header 為 `Content-Type: application/json`，欄位名稱與
本 README 的範例完全一致。也請確認實際送出的 URL 是 `/takeoff` 或 `/goto`。

### `/goto` 或 `/rtl` 回傳 409

若訊息為 `Vehicle must be flying ...`，先成功呼叫 `/takeoff`，再呼叫 `/goto` 或
`/rtl`。409 是安全檢查，不是服務崩潰。

### 起飛回傳 PreArm 相關錯誤

等待 QGC 顯示 `Ready` 後重試。若仍無法執行，先確認目前已落地，再重新啟動：

```sh
docker compose down
docker compose up -d
```

### QGC 沒有自動連線

確認 QGC 已開啟、沒有另一個程式占用 UDP 14550，並確認 `compose.yaml` 中的
`QGC_HOST=host.docker.internal` 未被修改。然後重新啟動 Compose。

### 8000 port 已被使用

停止占用 `127.0.0.1:8000` 的本機服務，或先停止先前啟動的本專案 container，再重新
啟動。

## 專案結構

```text
.
├── app/                    # FastAPI 與 MAVLink 控制器
├── config/                 # MAVLink-router 設定模板
├── scripts/
│   ├── check_connection.py # 唯讀連線檢查
│   ├── demo_api.py         # 完整 API / QGC 示範腳本
│   └── start.sh            # container 啟動程序
├── deliverables/           # 驗收錄影（成片、字卡、剪輯腳本）
├── compose.yaml
├── Dockerfile
├── PROJECT_PLAN.md         # 階段計畫與目前進度
└── RECORDING_GUIDE.md      # 驗收錄影腳本
```

## 設計範圍與安全措施

- 專案只支援單一模擬 Quad，不包含真實飛控或多機管理。
- FastAPI 與 QGC 透過 MAVLink-router 控制同一台模擬器。
- API 同一時間只執行一個飛行動作。
- 起飛與目標高度限制為 1–20 公尺。
- `goto` 與 `rtl` 必須在已起飛狀態才能執行。
- 控制動作會等待完成；拒絕、狀態不符或逾時會回傳清楚的錯誤。
- MVP 不包含登入、資料庫、Web 前端或雲端部署。

## 官方參考

- [ArduPilot SITL 文件](https://ardupilot.org/dev/docs/using-sitl-for-ardupilot-testing.html)
- [ArduCopter SITL 4.7.1](https://firmware.ardupilot.org/Copter/stable-4.7.1/SITL_x86_64_linux_gnu/)
- [MAVLink-router v4](https://github.com/mavlink-router/mavlink-router/tree/v4)
- [QGroundControl 5.1](https://docs.qgroundcontrol.com/Stable_V5.1/en/qgc-user-guide/getting_started/download_and_install.html)
