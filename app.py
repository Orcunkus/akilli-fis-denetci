from flask import Flask, render_template, request, flash, redirect, url_for, session
import pandas as pd
import numpy as np  
import re  
import os
import io

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin-v20-rakam-fix" 

ROW_LIMIT = 500 
RULE_FILE_PATH = 'TDHP_Normal_Bakiye_Yonu_SON_7li_dahil.xlsx - TDHP_Bakiye.csv'

# --- YARDIMCI FONKSİYONLAR ---
def load_rules():
    try:
        rules_df = pd.read_csv(RULE_FILE_PATH, sep=';', encoding='iso-8859-9')
        rules_df.columns = ['HESAP_KODU', 'HESAP_ADI', 'BAKIYE_YONU', 'BAKIYE_YONU_ING'] + list(rules_df.columns[4:])
        rules_df['HESAP_KODU'] = pd.to_numeric(rules_df['HESAP_KODU'], errors='coerce')
        rules_df = rules_df.dropna(subset=['HESAP_KODU'])
        rules_df['HESAP_KODU'] = rules_df['HESAP_KODU'].astype(int).astype(str).str[:3]
        rules_df = rules_df.drop_duplicates(subset=['HESAP_KODU']).set_index('HESAP_KODU')
        rules_df['BAKIYE_YONU'] = rules_df['BAKIYE_YONU'].str.upper().str.strip().replace({'BORÇ': 'B', 'ALACAK': 'A', 'HESAP TÜRÜNE GÖRE': 'H'})
        return rules_df['BAKIYE_YONU'].to_dict()
    except Exception as e:
        print(f"Kural dosyası yüklenirken HATA oluştu: {e}")
        return None

MUHASEBE_KURALLARI = load_rules()

# --- YENİ FONKSİYON: RAKAM TEMİZLEME ---
def clean_amount_v20(series):
    series = series.astype(str).str.strip()
    # 1. Metin dışı karakterleri sil
    series = series.str.replace(r'[^\d\.\,]', '', regex=True) 
    # 2. Binlik ayıracı (nokta) kaldır
    series = series.str.replace('.', '', regex=False)        
    # 3. Ondalık ayıracı (virgül) noktaya çevir
    series = series.str.replace(',', '.', regex=False)        
    return pd.to_numeric(series, errors='coerce').fillna(0)


# --- ANA SAYFA ---
@app.route('/')
def ana_sayfa():
    data_loaded = 'dataframe_json' in session
    return render_template('index.html', data_loaded=data_loaded)


# --- YÜKLEME VE BORÇ/ALACAK RAKAM TEMİZLİĞİ ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'dosya' not in request.files:
        flash("error", "HATA! Dosya Seçilmedi.")
        return redirect(url_for('ana_sayfa'))
    file = request.files['dosya']
    
    try:
        # Dosya okuma (Aynı)
        filename = file.filename
        if filename.endswith('.csv'):
            df = pd.read_csv(file, sep=';', skiprows=6, encoding='iso-8859-9')
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file, engine='openpyxl', header=5)
        else:
            flash("error", "HATA! Desteklenmeyen dosya formatı. Lütfen .xlsx veya .csv yükleyin.")
            return redirect(url_for('ana_sayfa'))

        # TEMİZLEME AŞAMASI (v10)
        df['HESAP KODU'] = df['HESAP KODU'].astype(str)
        df_clean = df.dropna(subset=['HESAP ADI']).copy() 
        df_final = df_clean[df_clean['HESAP KODU'].str.contains(r'\.', na=False)].copy() 
        
        # --- BORÇ/ALACAK RAKAM TEMİZLİĞİ UYGULANMASI ---
        df_final['BORÇ'] = clean_amount_v20(df_final['BORÇ'])
        df_final['ALACAK'] = clean_amount_v20(df_final['ALACAK'])
        
        # --- SONUÇ RAPORU (Sadece Kaydırma Testi) ---
        session['dataframe_json'] = df_final.to_json()
        
        # Hata ayıklama mesajı:
        flash("success", f"Başarılı! Veriniz hazır. Lütfen Borç ve Alacak sütunlarının rakamlarını kontrol edin. Net {len(df_final)} alt hesap.")
        
        # Ekrana sonucu bas (Kaydırma hatasını görmek için)
        total_rows = len(df_final)
        cikti = f"<h2 style='color: #4CAF50;'>VERİ KAYDIRMA/RAKAM TESTİ BAŞARILI!</h2>"
        cikti += f"Net İşlem Satırı: {total_rows} <br>"
        cikti += f"<b>LÜTFEN TABLONUN BORÇ VE ALACAK SÜTUNLARINI KONTROL EDİNİZ!</b><br><br>"
        
        df_final['BORÇ'] = df_final['BORÇ'].round(2)
        df_final['ALACAK'] = df_final['ALACAK'].round(2)
        df_final = df_final.fillna('')
        
        return cikti + df_final.head(ROW_LIMIT).to_html(na_rep='', justify='left')

    except Exception as e:
        flash("error", f"KRİTİK VERİ İŞLEME HATASI! Hata Kodu: {str(e)}")
        return redirect(url_for('ana_sayfa'))


# --- DENETİMİ BAŞLAT (BUTONLA) ---
# (Bu kısım aynı kalıyor, sadece yüklemeden sonraki butona basıldığında çalışacak)
@app.route('/denetle', methods=['GET'])
def denetle():
    if 'dataframe_json' not in session:
        flash("error", "Hata: Denetlenecek veri bulunamadı! Lütfen önce dosyayı yükleyin.")
        return redirect(url_for('ana_sayfa'))

    try:
        df_final = pd.read_json(session['dataframe_json'])

        # Borç/Alacak sütunlarının varlığını kontrol et
        if 'BORÇ' not in df_final.columns or 'ALACAK' not in df_final.columns:
            flash("error", "Kritik Hata: BORÇ veya ALACAK sütunları bulunamıyor. Kaydırma hatası olabilir.")
            return redirect(url_for('ana_sayfa'))
        
        # --- BORÇ/ALACAK DENETİM MOTORU ---
        
        # ... (Denetim kodu ve raporlama v15'teki gibi)
        
        total_errors = len(df_final[df_final['HATA_DURUMU'] != ''])
        total_rows = len(df_final)

        # HTML çıktısı
        cikti = f"<h2 style='color: #4CAF50;'>BORÇ/ALACAK DENETİMİ TAMAMLANDI!</h2>"
        cikti += f"Net İşlem Satırı: {total_rows} <br>"
        cikti += f"<b style='color: red;'>TESPİT EDİLEN TERS KAYIT/HATA SAYISI: {total_errors}</b><br><br>"
        
        df_final['BORÇ'] = df_final['BORÇ'].round(2)
        df_final['ALACAK'] = df_final['ALACAK'].round(2)
        
        df_final = df_final.fillna('')
        
        cols = ['HATA_DURUMU'] + [col for col in df_final.columns if col not in ['HATA_DURUMU', 'HESAP KODU', 'HESAP_KODU_STR']]
        df_final = df_final[['HESAP KODU'] + cols] 
        
        return cikti + df_final.head(ROW_LIMIT).to_html(na_rep='', justify='left')

    except Exception as e:
        flash("error", f"DENETİM MOTORU KRİTİK HATA VERDİ: {str(e)}")
        return redirect(url_for('ana_sayfa'))


# --- HTML ve Diğer Fonksiyonlar ---
@app.route('/', methods=['GET'])
def ana_sayfa():
    # ... (Aynı)
    data_loaded = 'dataframe_json' in session
    return render_template('index.html', data_loaded=data_loaded)

# ... (Diğer fonksiyonlar)
@app.route('/teardown_request')
def cleanup(exception=None):
    pass
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
