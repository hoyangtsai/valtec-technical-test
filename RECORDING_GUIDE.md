# Valtec MVP 驗收錄影腳本

目標：用**單一支 3 分鐘內 MP4（至少 480p）**，直接證明 container、
QGroundControl 與四個控制 API 都能正常運作。邀請信指定截止日前直接回覆原信；
2026-09-26 起改為 3 分鐘內（原確認規格為 5–8 分鐘，寄出前請確認邀請方可接受）；
等待飛行的時間用 ffmpeg 加速，不留靜止畫面。

## 錄影前準備

- [ ] 關閉或隱藏通知、私人郵件、密碼與無關視窗。
- [ ] 準備終端機、QGroundControl、Swagger 三個視窗。
- [ ] 確認瀏覽器開啟 http://127.0.0.1:8000/docs。
- [ ] 確認目前無人機已落地；若不確定，先執行 `docker compose down`。
- [ ] 將 QGC Go To 目標控制在起飛點約 10–30 公尺內。
- [ ] 可先不錄影排練一次 `python3 scripts/demo_api.py`。

## 建議分鏡

### 1. 專案與啟動（約 45 秒）

1. 短暫展示 README 的架構和快速啟動段落。
2. 在終端機執行：

   ```sh
   docker compose down
   docker compose up --build -d
   docker compose ps
   ```

3. 拍到 container 最後顯示 `healthy`。

### 2. QGC 與狀態 API（約 30 秒）

1. 切到 QGC，拍到地圖上的模擬無人機、`Ready`、高度與 GPS 狀態。
2. 切到 Swagger，執行 `GET /status`。
3. 拍到 `armed: false`、位置和相對高度接近 0。

### 3. Takeoff（約 45 秒）

1. 在 Swagger 的 `POST /takeoff` 輸入：

   ```json
   {"altitude_m": 3}
   ```

2. 執行並拍到 HTTP 200。
3. 切到 QGC，拍到 `Flying / Guided` 與高度約 3 公尺。

### 4. Land（約 45 秒）

1. 在 Swagger 執行 `POST /land`。
2. 拍到 API HTTP 200、QGC 原地降落並回到 `Ready`。

### 5. 第二次 Takeoff（約 45 秒）

1. 再次執行 `POST /takeoff`，高度設為 3 公尺。
2. 拍到 API HTTP 200。
3. 切到 QGC，拍到 `Flying / Guided` 與高度約 3 公尺。

### 6. QGC Go To 與 API 讀回結果（約 60 秒）

1. 在 QGC Fly 畫面選起飛點附近約 10–30 公尺的位置並執行 Go To。
2. 拍到無人機移動完成。
3. 回 Swagger 執行 `GET /status`，拍到 API 讀回 QGC 控制後的新座標。
4. 口頭或字幕說明：QGC 與 API 經 MAVLink-router 控制同一台模擬無人機。

### 7. Goto API（約 45 秒）

1. 在 `POST /goto` 輸入：

   ```json
   {
     "latitude": -35.363170,
     "longitude": 149.165230,
     "altitude_m": 3
   }
   ```

2. 執行並拍到 HTTP 200 和 `Target position reached`。
3. 切到 QGC，拍到無人機飛往 API 指定位置，地圖位置及飛行軌跡再次改變。

### 8. RTL（約 60–90 秒）

1. 在 Swagger 執行 `POST /rtl`。
2. 同時切到 QGC，拍到返航軌跡、回到起飛點及自動降落。
3. 拍到 API HTTP 200，以及 QGC 最後顯示 `Ready`。

### 9. 收尾（約 15 秒）

1. 執行 `GET /status`，拍到 `armed: false` 和高度接近 0。
2. 說明四個控制 API 與 QGC 交替控制均已完成。
3. 可執行 `docker compose ps` 再拍一次健康狀態。

## 成片檢查清單

- [ ] 畫面沒有私人資料、token、密碼或通知內容。
- [ ] 看得到 container `healthy`。
- [ ] 看得到 QGC 已連線及即時 telemetry。
- [ ] 看得到 `takeoff`、`goto`、`rtl`、`land` 全部成功。
- [ ] 看得到 QGC 手動 Go To，以及 API 讀回新位置。
- [ ] 看得到最終已落地、解除鎖定。
- [ ] 指令、JSON 和 API 回應文字清楚可讀。
- [ ] 影片可從頭播放，聲音或字幕足以理解操作。
- [ ] 成片為單一 MP4，長度 3 分鐘內，解析度至少 480p。
- [ ] 截止日前以 Gmail 回覆原邀請信；寄出前由使用者本人確認附件或連結。
