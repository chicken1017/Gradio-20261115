# 📊 開放資料 CSV 探索器

以 Gradio 打造的開放資料瀏覽工具：貼上 CSV 連結，即可下載、清理、搜尋、分析並視覺化。預設資料來源為台南市政府資料開放平台。

## 功能

- 載入任意公開 CSV 連結，支援編碼自動偵測（UTF-8 / Big5 / CP950）
- 缺值處理：不清理、刪除任一欄有缺值的列、只刪除整列皆空的列
- 資料預覽與全欄位關鍵字搜尋
- 缺值分析、統計摘要
- 視覺化：長條圖、圓餅圖、直方圖
- 下載清理後的 CSV（`utf-8-sig`，Excel 開啟不亂碼）

## 專案結構

```
.
├── app.py             # Gradio 主程式
├── requirements.txt   # 相依套件
└── README.md
```

## 本機執行

```bash
pip install -r requirements.txt
python app.py
```

開啟瀏覽器前往 http://localhost:7860

## 部署到 Render

1. 將本專案推送到 GitHub。
2. 登入 [Render](https://render.com)，點選 **New → Web Service**，連結你的 GitHub repo。
3. 填寫設定：

   | 欄位 | 值 |
   | --- | --- |
   | Language / Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `python app.py` |
   | Instance Type | Free（或依需求升級） |

4. （建議）在 **Environment** 新增變數 `PYTHON_VERSION` = `3.11.9`，避免使用過新或過舊的 Python 版本。
5. 點選 **Create Web Service**，等待建置完成後即可透過 `https://<your-app>.onrender.com` 存取。

> `app.py` 會自動讀取 Render 提供的 `PORT` 環境變數，並綁定 `0.0.0.0`，不需額外設定。

## 注意事項

- **Free 方案會休眠**：閒置約 15 分鐘後會進入休眠，下次開啟需等待數十秒冷啟動。
- **記憶體限制**：Free 方案約 512 MB，處理超大型 CSV 可能會記憶體不足。
- **資料來源連線**：部分台灣政府網站可能封鎖海外主機（Render 機房位於海外），若出現下載失敗或逾時，請改換資料來源或將 CSV 放到可公開存取的位置（例如 GitHub raw 連結）。
- **SSL 驗證**：部分政府網站憑證不完整，預設關閉 SSL 驗證；若資料來源憑證正常，建議在介面中勾選驗證。
- 暫存檔寫在容器的暫存目錄，重啟後會消失，屬正常行為。

## 授權

MIT License
