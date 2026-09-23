架構：
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

本地開啟：

http://127.0.0.1:8000/

可查詢 30+ 個 Steam 地區，
價格紀錄使用台灣時區（UTC+8）。

## 公開網頁
https://steam-price-analyzer.onrender.com/)
