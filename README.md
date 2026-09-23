# Steam Price Analyzer — Flask templates/static 版

網站架構完全改成參考專案的 Flask 標準方式：

```text
steam_price_analyzer/
├── app.py
├── prices.db
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    └── styles.css
```

`templates/index.html` 使用 Flask `render_template()`，CSS 使用 `static/styles.css` 與 `url_for('static', filename='styles.css')`。

## Mac

```bash
cd ~/Downloads/steam_price_analyzer_flask
python3 -m pip install -r requirements.txt
python3 app.py
```

開啟：

http://127.0.0.1:8000/

健康檢查：

http://127.0.0.1:8000/api/health

預設查詢 30+ 個 Steam 地區，可在網頁直接修改地區代碼。

## 部署到公開網頁

本專案已支援雲端平台提供的 `PORT` 環境變數。以 Render 為例：

1. 將此資料夾推送到 GitHub。
2. 在 Render 建立 **Web Service**，選擇該 GitHub repository。
3. Build Command 填入 `pip install -r requirements.txt`。
4. Start Command 填入 `gunicorn app:app`。
5. 部署完成後使用 Render 提供的 `https://...onrender.com` 網址。

本機區域網路測試時，程式會監聽所有網路介面；同一個網路的其他裝置可透過
`http://你的電腦IP:8000/` 開啟。


## KRW 修正
Steam 的這個價格 API 回傳值在本專案中應以 100 作為最小單位 divisor；例如 ELDEN RING 的 6,480,000 應解析為 ₩64,800，而不是 ₩6,480。
