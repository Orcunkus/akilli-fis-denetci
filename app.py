from flask import Flask, render_template, request, flash, redirect, url_for, session
import pandas as pd
import numpy as np  
import re  
import os
import io

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin-v18-nihai-fix" 

ROW_LIMIT = 500 
RULE_FILE_PATH = 'TDHP_Normal_Bakiye_Yonu_SON_7li_dahil.xlsx - TDHP_Bakiye.csv'

# Kural yükleme fonksiyonunu tutuyoruz ama şimdilik kullanmıyoruz
# ... 

@app.route('/')
def ana_sayfa():
    # Artık denetim butonu yok, sadece sonuç gösterilecek
    return render_template('index.html', data_loaded=False) 


# --- YÜKLEME VE KAYDIRMA KODU (ODAK NOKTASI) ---
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
        
        # --- BORÇ/ALACAK KAYDIRMA KISMI (KRİTİK) ---
        df_final['BORÇ_HAM'] = pd.to_numeric(df_final['BORÇ'], errors='coerce')
        df_final['ALACAK_HAM'] = pd.to_numeric(df_final['ALACAK'], errors='coerce')

        df_error = df_final[df_final['BORÇ_HAM'].isna() & df_final['ALACAK_HAM'].isna()].copy()
        
        # Metin içinden sayı çekme fonksiyonu (Türkçe formatı temizler)
        def extract_amount(row):
            # DETAY'dan veya AÇIKLAMA'dan ilk sayıyı bulmaya çalış
            text = str(row['DETAY']) + " " + str(row['AÇIKLAMA'])
            match = re.search(r'(\d[\d\.\,]+)', text) 
            if match:
                # KRİTİK: Türkçe formattan sayıya çevir
                return float(match.group(1).replace('.', '').replace(',', '.')) 
            return 0.0

        if not df_error.empty:
            df_error.loc[:, 'BORÇ_YENİ'] = df_error.apply(extract_amount, axis=1)
            df_error.loc[:, 'ALACAK_YENİ'] = 0.0 # Alacak her zaman aynı satırda boş
            
            df_final.update(df_error[['BORÇ_YENİ']].rename(columns={'BORÇ_YENİ': 'BORÇ'}))
            df_final.update(df_error[['ALACAK_YENİ']].rename(columns={'ALACAK_YENİ': 'ALACAK'}))
            
            df_final['BORÇ'] = df_final['BORÇ'].combine_first(df_final['BORÇ_HAM']).fillna(0)
            df_final['ALACAK'] = df_final['ALACAK'].combine_first(df_final['ALACAK_HAM']).fillna(0)
            
        df_final = df_final.drop(columns=['BORÇ_HAM', 'ALACAK_HAM'], errors='ignore')
        
        # --- SONUÇ RAPORU (Denetimsiz, Sadece Kaydırmayı Göster) ---
        total_rows = len(df_final)

        cikti = f"<h2 style='color: #4CAF50;'>VERİ KAYDIRMA TESTİ BAŞARILI!</h2>"
        cikti += f"Net İşlem Satırı: {total_rows} <br>"
        cikti += f"<b>Lütfen aşağıdaki tablonun BORÇ ve ALACAK sütunlarını kontrol edin.</b><br><br>"
        
        df_final['BORÇ'] = df_final['BORÇ'].round(2)
        df_final['ALACAK'] = df_final['ALACAK'].round(2)
        df_final = df_final.fillna('')
        
        return cikti + df_final.head(ROW_LIMIT).to_html(na_rep='', justify='left')

    except Exception as e:
        # HATA KAYDI: Kaydırma kodundaki asıl hatayı burada yakalayacağız.
        flash("error", f"KRİTİK VERİ İŞLEME HATASI! Hata Kodu: {str(e)}")
        return redirect(url_for('ana_sayfa'))


# --- DENETİM VE SESSION İŞLEMLERİ KALDIRILDI ---
@app.route('/denetle', methods=['GET'])
def denetle():
    flash("error", "Denetim butonu şu an pasiftir. Önce kaydırma hatasını çözmeliyiz.")
    return redirect(url_for('ana_sayfa'))

@app.teardown_request
def cleanup(exception=None):
    pass
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
