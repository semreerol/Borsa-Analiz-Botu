import yfinance as yf
import pandas as pd
import google.generativeai as genai
import os
import requests
import time
from datetime import datetime


API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def get_bist100_tickers():
    try:
        url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx?endeks=01"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
        }
        content = requests.get(url, headers=headers).content
        df = pd.read_html(content)[0]
        tickers = [f"{kod}.IS" for kod in df.iloc[:, 0].tolist()]
        print(f"BIST 100 Listesi: {len(tickers)} hisse.")
        return tickers
    except Exception as e:
        print(f"Hata (Liste): {e}")
        return ["THYAO.IS", "GARAN.IS", "AKBNK.IS", "ASELS.IS"]

def veri_cek(tickers):
    data_list = []
    print(f"Veriler çekiliyor ({len(tickers)} hisse)...")
    
    for i, hisse in enumerate(tickers):
        try:
            if i % 20 == 0: print(f"%{int((i/len(tickers))*100)} tamamlandı...")
            
            ticker = yf.Ticker(hisse)
            hist = ticker.history(period="2d")
            
            if len(hist) >= 2:
                bugun = hist['Close'].iloc[-1]
                dun = hist['Close'].iloc[-2]
                degisim = ((bugun - dun) / dun) * 100
                
                data_list.append({
                    "Kod": hisse.replace(".IS", ""),
                    "Fiyat": round(bugun, 2),
                    "Degisim": round(degisim, 2)
                })
        except:
            continue

    return pd.DataFrame(data_list).sort_values(by="Degisim", ascending=False)

def ai_analiz_yap(df):
    if not API_KEY: return "API Key eksik."

    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    top_yukselen = df.head(5).to_string(index=False)
    top_dusen = df.tail(5).to_string(index=False)
    genel_ortalama = df["Degisim"].mean()
    yon = "POZİTİF 🟢" if genel_ortalama > 0 else "NEGATİF 🔴"

    prompt = f"""
    BIST 100 Günlük Kapanış Analizi Hazırla.
    
    GENEL DURUM: {yon} (Ort: %{genel_ortalama:.2f})

    YÜKSELENLER:
    {top_yukselen}

    DÜŞENLER:
    {top_dusen}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Hatası: {e}"

def telegram_gonder(mesaj):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram ayarları eksik, mesaj gönderilemedi.")
        return

    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mesaj,
        # "parse_mode": "Markdown" # Hata alırsanız bu satırı kapatın
    }
    
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print("📲 Telegram bildirimi gönderildi!")
        else:
            print(f"Telegram Hatası: {r.text}")
    except Exception as e:
        print(f"Telegram Bağlantı Hatası: {e}")

def raporu_kaydet(analiz_metni, df):
    tarih = datetime.now().strftime("%Y-%m-%d")
    dosya_adi = f"reports/{tarih}-BIST100.md"
    os.makedirs("reports", exist_ok=True)
    
    with open(dosya_adi, "w", encoding="utf-8") as f:
        f.write(f"# {tarih} Raporu\n\n{analiz_metni}\n\n")
        f.write(df.to_markdown())
    print(f"💾 Rapor kaydedildi: {dosya_adi}")

if __name__ == "__main__":
    tickers = get_bist100_tickers()
    if tickers:
        df = veri_cek(tickers)
        if not df.empty:
            analiz = ai_analiz_yap(df)         
           
            raporu_kaydet(analiz, df)
            telegram_gonder(analiz)
        else:
            print("Veri yok.")