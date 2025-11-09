from flask import Flask, render_template, request, flash, redirect, url_for, session
import pandas as pd
import numpy as np  
import os
import io

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin-v24-sadece-temizlik" 

ROW_LIMIT = 500 

# --- RAKAM TEMİZLEME FONKSİYONU (V20) ---
# Bu, Borç/Alacak sütunlarındaki format hatalarını (nokta/virgül) temizler.
def clean_amount_v20(series):
    series = series.astype(str).str.strip()
    series = series.str.replace(r'[^\d\.\,]', '', regex=True) 
    series = series.str.replace('.', '', regex=False)        
    series = series.str.replace(',', '.', regex=False)        
    return pd.to_numeric(series, errors='coerce').fillna(0)


# --- YÜKLEME VE FİLTRELEME ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'dosya' not in request.files:
        flash("error", "HATA! Dosya Seçilmedi.")
        return redirect(url_for('ana_sayfa'))
    file = request.files['dosya']
    
    try:
        # Dosya okuma (CSV ve XLSX desteği)
        filename = file.filename
        if filename.endswith('.csv'):
            df = pd.read_csv(file, sep=';', skiprows=6, encoding='iso-8859-9')
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file, engine='openpyxl', header=5)
        else:
            flash("error", "HATA! Desteklenmeyen dosya formatı. Lütfen .xlsx veya .csv yükleyin.")
            return redirect(url_for('ana_sayfa'))

        # TEMİZLEME AŞAMASI (Sadece Alt Hesapları Tutar, Rakamları Temizler)
        df['HESAP KODU'] = df['HESAP KODU'].astype(str)
        df_clean = df.dropna(subset=['HESAP ADI']).copy() 
        df_final = df_clean[df_clean['HESAP KODU'].str.contains(r'\.', na=False)].copy() 
        
        # Rakam Temizliği (Borç/Alacak)
        df_final['BORÇ'] = clean_amount_v20(df_final['BORÇ'])
        df_final['ALACAK'] = clean_amount_v20(df_final['ALACAK'])

        # Veriyi JSON formatında şifreleyip Session'da sakla (Bu, HTML'de sonucu gösterir)
        session['dataframe_json_gosterim'] = df_final.to_json()
        
        flash("success", f"Başarılı! Veriniz temizlendi ve denetim için hazır. Net {len(df_final)} alt hesap bulundu.")
        return redirect(url_for('ana_sayfa'))
        
    except Exception as e:
        flash("error", f"YÜKLEME SIRASINDA KRİTİK HATA! {str(e)}")
        return redirect(url_for('ana_sayfa'))


# --- DENETİMİ BAŞLAT (PASİF) ---
@app.route('/denetle', methods=['GET'])
def denetle():
    flash("error", "Denetim butonu şu an pasif durumdadır. Önce veri temizliğini kontrol ediniz.")
    return redirect(url_for('ana_sayfa'))


# --- ANA SAYFA (SONUCU GÖSTEREN) ---
@app.route('/', methods=['GET'])
def ana_sayfa():
    df_html = ""
    # Eğer yüklenen veri varsa, onu oku ve HTML'e çevir
    if 'dataframe_json_gosterim' in session:
        try:
            df_gosterim = pd.read_json(session.pop('dataframe_json_gosterim'))
            df_gosterim['BORÇ'] = df_gosterim['BORÇ'].round(2)
            df_gosterim['ALACAK'] = df_gosterim['ALACAK'].round(2)
            df_gosterim = df_gosterim.fillna('')
            df_html = df_gosterim.head(ROW_LIMIT).to_html(na_rep='', justify='left')
        except Exception as e:
            flash("error", f"Veri Görüntüleme Hatası: {str(e)}")
            
    data_loaded = False # Denetim butonu göstermeyeceğiz
    return render_template('index.html', data_loaded=data_loaded, result_table=df_html)

@app.teardown_request
def cleanup(exception=None):
    pass
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
