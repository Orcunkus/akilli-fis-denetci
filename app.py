from flask import Flask, render_template, request, flash, redirect, url_for, session
import pandas as pd
import numpy as np  
import re  
import os
import io

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin-v26-denetim-aktif" 

ROW_LIMIT = 500 
RULE_FILE_PATH = 'TDHP_Normal_Bakiye_Yonu_SON_7li_dahil.xlsx - TDHP_Bakiye.csv'

# --- YARDIMCI FONKSİYONLAR (KURAL YÜKLEME) ---
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

# Rakam Temizleme (V20) - Sadece sayısal sütunlar için
def clean_amount_v20(series):
    series = series.astype(str).str.strip()
    series = series.str.replace(r'[^\d\.\,]', '', regex=True) 
    series = series.str.replace('.', '', regex=False)        
    series = series.str.replace(',', '.', regex=False)        
    return pd.to_numeric(series, errors='coerce').fillna(0)


# --- ANA SAYFA ---
@app.route('/')
def ana_sayfa():
    data_loaded = 'dataframe_json' in session
    return render_template('index.html', data_loaded=data_loaded)


# --- YÜKLEME VE VERİYİ SAKLAMA ---
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

        # HAM FİLTRE: Sadece Alt Hesapları Tutan Basit Filtre
        df['HESAP KODU'] = df['HESAP KODU'].astype(str)
        df_clean = df.dropna(subset=['HESAP ADI']).copy() 
        df_final = df_clean[df_clean['HESAP KODU'].str.contains(r'\.', na=False)].copy() 

        # Rakam Temizliği ve Sayısallaştırma (Analiz için şart)
        df_final['BORÇ'] = clean_amount_v20(df_final['BORÇ'])
        df_final['ALACAK'] = clean_amount_v20(df_final['ALACAK'])
        
        # Veriyi JSON formatında şifreleyip Session'da sakla
        session['dataframe_json'] = df_final.to_json()
        
        flash("success", f"Başarılı! Dosyanız temizlendi ve denetim için hazır. Net {len(df_final)} alt hesap bulundu.")
        return redirect(url_for('ana_sayfa'))
        
    except Exception as e:
        flash("error", f"YÜKLEME SIRASINDA KRİTİK HATA! {str(e)}")
        return redirect(url_for('ana_sayfa'))


# --- DENETİMİ BAŞLAT (NİHAİ ANALİZ MOTORU) ---
@app.route('/denetle', methods=['GET'])
def denetle():
    if not MUHASEBE_KURALLARI:
        flash("error", "Hata: Kural dosyası yüklenmediği için analiz yapılamıyor.")
        return redirect(url_for('ana_sayfa'))

    if 'dataframe_json' not in session:
        flash("error", "Hata: Denetlenecek veri bulunamadı! Lütfen önce dosyayı yükleyin.")
        return redirect(url_for('ana_sayfa'))

    try:
        df_final = pd.read_json(session['dataframe_json'])

        # --- BORÇ/ALACAK DENETİM MOTORU ---
        
        df_final['HATA_DURUMU'] = ''
        
        for index, row in df_final.iterrows():
            try:
                # Alt hesaptan ana hesabı bul (örn: 153.00.20 -> 153)
                ana_hesap = str(row['HESAP KODU']).split('.')[0].strip()
                ana_hesap_ilk_uc = ana_hesap[:3]
            except Exception as e_analiz:
                 df_final.loc[index, 'HATA_DURUMU'] = f"Analiz Hatası: Hesap Kodu Bulunamadı. {e_analiz}"
                 continue 
            
            if ana_hesap_ilk_uc in MUHASEBE_KURALLARI:
                kural = MUHASEBE_KURALLARI[ana_hesap_ilk_uc]
                borc_var = row['BORÇ'] > 0
                alacak_var = row['ALACAK'] > 0
                
                hata_mesaji = []
                
                if kural == 'B' and alacak_var:
                    hata_mesaji.append(f"TERS KAYIT (B): Kural Borç çalışması der, Alacak'ta değer var.")
                
                if kural == 'A' and borc_var:
                    hata_mesaji.append(f"TERS KAYIT (A): Kural Alacak çalışması der, Borç'ta değer var.")
                
                if borc_var and alacak_var:
                     hata_mesaji.append(f"ÇİFT KAYIT: Borç ve Alacak aynı anda dolu! Kural: {kural}")

                if hata_mesaji:
                    df_final.loc[index, 'HATA_DURUMU'] = " / ".join(hata_mesaji)
        
        # --- SONUÇ RAPORU HAZIRLAMA VE GÖSTERME ---
        
        total_errors = len(df_final[df_final['HATA_DURUMU'] != ''])
        total_rows = len(df_final)

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
    data_loaded = 'dataframe_json' in session
    return render_template('index.html', data_loaded=data_loaded)

@app.teardown_request
def cleanup(exception=None):
    pass
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
