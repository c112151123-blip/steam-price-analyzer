import concurrent.futures, os, sqlite3, time
from datetime import datetime, timezone
from pathlib import Path
import requests
from flask import Flask, render_template, request

app=Flask(__name__)
BASE=Path(__file__).resolve().parent
DB=BASE/'prices.db'
STEAM='https://store.steampowered.com/api/appdetails'
SEARCH='https://store.steampowered.com/api/storesearch/'
REGIONS={'AR':'阿根廷','AT':'奧地利','AU':'澳洲','BE':'比利時','BR':'巴西','CA':'加拿大','CH':'瑞士','CL':'智利','CN':'中國','CO':'哥倫比亞','CZ':'捷克','DE':'德國','DK':'丹麥','ES':'西班牙','FI':'芬蘭','FR':'法國','GB':'英國','GR':'希臘','HK':'香港','HU':'匈牙利','ID':'印尼','IE':'愛爾蘭','IL':'以色列','IN':'印度','IT':'義大利','JP':'日本','KR':'韓國','MX':'墨西哥','MY':'馬來西亞','NL':'荷蘭','NO':'挪威','NZ':'紐西蘭','PE':'秘魯','PH':'菲律賓','PL':'波蘭','PT':'葡萄牙','RO':'羅馬尼亞','RU':'俄羅斯','SA':'沙烏地阿拉伯','SE':'瑞典','SG':'新加坡','TH':'泰國','TR':'土耳其','TW':'台灣','UA':'烏克蘭','US':'美國','ZA':'南非'}
DEFAULT='US,GB,DE,FR,JP,KR,TW,CN,HK,SG,AU,CA,BR,MX,IN,TR,RU,PL,SE,NO,DK,FI,NL,IT,ES,CH,NZ,MY,TH,ID,PH,ZA,IL,SA'
DIV={'USD':100,'GBP':100,'EUR':100,'CHF':100,'RUB':100,'PLN':100,'BRL':100,'NOK':100,'IDR':100,'MYR':100,'PHP':100,'SGD':100,'THB':100,'KRW':100,'TRY':100,'UAH':100,'MXN':100,'CAD':100,'AUD':100,'NZD':100,'CNY':100,'INR':100,'CLP':100,'PEN':100,'COP':100,'ZAR':100,'HKD':100,'TWD':100,'SAR':100,'ILS':100,'CZK':100,'DKK':100,'HUF':100,'RON':100,'SEK':100,'VND':100}
s=requests.Session();s.headers['User-Agent']='SteamRegionalPriceAnalyzer/2.0'

def init_db():
 c=sqlite3.connect(DB);c.execute('''CREATE TABLE IF NOT EXISTS price_history(id INTEGER PRIMARY KEY,app_id TEXT,game_name TEXT,country_code TEXT,country_name TEXT,currency TEXT,local_price REAL,initial_price REAL,discount_percent INTEGER,exchange_rate REAL,twd_price REAL,recorded_at TEXT)''');c.commit();c.close()

def amt(raw,cur): return None if raw is None else float(raw)/DIV.get(cur,100)
def resolve(q):
 if q.isdigit():
  d=s.get(STEAM,params={'appids':q,'cc':'us'},timeout=15).json().get(q)
  if not d or not d.get('success'): raise ValueError('找不到 Steam App ID')
  return q,d['data'].get('name',q)
 d=s.get(SEARCH,params={'term':q,'l':'english','cc':'us'},timeout=15).json().get('items',[])
 if not d: raise ValueError(f'找不到遊戲：{q}')
 return str(d[0]['id']),d[0].get('name',q)

def fetch(app_id,cc):
 r=s.get(STEAM,params={'appids':app_id,'cc':cc.lower(),'filters':'price_overview'},timeout=15).json().get(str(app_id))
 p=(r or {}).get('data',{}).get('price_overview') if r and r.get('success') else None
 if not p or p.get('final') is None:return None
 cur=p.get('currency');return {'country_code':cc,'country_name':REGIONS[cc],'currency':cur,'local_price':amt(p['final'],cur),'initial_price':amt(p.get('initial'),cur),'discount_percent':int(p.get('discount_percent',0))}

def rates():
 try:return s.get('https://open.er-api.com/v6/latest/TWD',timeout=10).json().get('rates',{})
 except:return {}
def twd(v,cur,fx): return v if cur=='TWD' else (v/float(fx[cur]) if fx.get(cur) else None)

def collect(app_id,name,codes):
 fx=rates();now=datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S')
 with concurrent.futures.ThreadPoolExecutor(max_workers=min(12,len(codes))) as ex: rows=[x for x in ex.map(lambda c:fetch(app_id,c),codes) if x]
 c=sqlite3.connect(DB)
 for r in rows:
  c.execute('INSERT INTO price_history(app_id,game_name,country_code,country_name,currency,local_price,initial_price,discount_percent,exchange_rate,twd_price,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(app_id,name,r['country_code'],r['country_name'],r['currency'],r['local_price'],r['initial_price'],r['discount_percent'],fx.get(r['currency'],1),twd(r['local_price'],r['currency'],fx),now))
 c.commit();c.close()

def latest(app_id):
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row
 rows=c.execute('''SELECT p.* FROM price_history p JOIN (SELECT country_code,MAX(id) id FROM price_history WHERE app_id=? GROUP BY country_code)x ON p.id=x.id WHERE p.app_id=? ORDER BY CASE WHEN p.twd_price IS NULL THEN 1 ELSE 0 END,p.twd_price''',(app_id,app_id)).fetchall();c.close();return [dict(x) for x in rows]
def history(app_id):
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;r=c.execute('SELECT * FROM price_history WHERE app_id=? ORDER BY recorded_at,country_code',(app_id,)).fetchall();c.close();return [dict(x) for x in r]
def games():
 c=sqlite3.connect(DB);r=c.execute('SELECT DISTINCT game_name FROM price_history ORDER BY game_name').fetchall();c.close();return [x[0] for x in r]

@app.route('/',methods=['GET','POST'])
def index():
 init_db();form={'query':'','regions':DEFAULT,'min_price':'','max_price':''};result=None;hist=[];err=None
 if request.method=='POST':
  form={k:request.form.get(k,'').strip() for k in form}
  try:
   app_id,name=resolve(form['query']);codes=list(dict.fromkeys(x for x in [z.strip().upper() for z in form['regions'].split(',')] if x in REGIONS))
   if not codes:raise ValueError('沒有有效的地區代碼')
   t=time.perf_counter();collect(app_id,name,codes);rows=latest(app_id);tw=next((r['twd_price'] for r in rows if r['country_code']=='TW'),None)
   for r in rows:r['diff_vs_taiwan']=((r['twd_price']-tw)/tw*100) if r['twd_price'] is not None and tw else None
   mn=float(form['min_price']) if form['min_price'] else 0;mx=float(form['max_price']) if form['max_price'] else None
   if mx is not None and mn>mx:raise ValueError('最低價格不能高於最高價格')
   rows=[r for r in rows if r['twd_price'] is not None and r['twd_price']>=mn and (mx is None or r['twd_price']<=mx)]
   result={'game_name':name,'rows':rows,'taiwan':next((r for r in rows if r['country_code']=='TW'),None),'cheapest':min(rows,key=lambda r:r['twd_price']) if rows else None,'elapsed':round(time.perf_counter()-t,3)};hist=history(app_id)
  except Exception as e:err=str(e)
 return render_template('index.html',games=games(),result=result,history=hist,error_message=err,form=form)

@app.get('/api/health')
def health():return {'status':'ok'}
@app.get('/api/games/<app_id>/latest')
def api_latest(app_id):return latest(app_id)
@app.get('/api/games/<app_id>/history')
def api_history(app_id):return history(app_id)

if __name__=='__main__':
 init_db()
 app.run(host='0.0.0.0',port=int(os.environ.get('PORT',8000)),debug=False)
