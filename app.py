from flask import Flask, render_template, request, flash, redirect, url_for, session
import pandas as pd
import numpy as np  
import re  
import os
import io

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin-v16-debug" 

ROW_LIMIT = 500 
RULE_FILE_PATH = 'TDHP_Normal_Bakiye_Yonu_SON_7li_dahil.xlsx - TDHP_Bakiye.csv'

# --- YARDIMCI FONKSİYONLAR (Aynı) ---
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


# --- YÜKLEME VE VERİYİ SAKLAMA ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'dosya' not in request.files:
        flash("HATA! Dosya Seçilmedi.")
        return redirect(url_for('ana_sayfa'))
    
    file = request.files['dosya']
    
    # DEBUG KONTROL: Eğer dosya adı yoksa (seçilmemişse)
    if file.filename == '':
        flash("HATA! Dosya seçildi ama dosya adı boş.")
        return redirect(url_for('ana_sayfa'))
    
    try:
        # Dosya okuma (CSV ve XLSX desteği)
        # ... (Dosya okuma mantığı aynı)
        
        filename = file.filename
        if filename.endswith('.csv'):
            df = pd.read_csv(file, sep=';', skiprows=6, encoding='iso-8859-9')
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file, engine='openpyxl', header=5)
        else:
            flash("HATA! Desteklenmeyen dosya formatı. Lütfen .xlsx veya .csv yükleyin.")
            return redirect(url_for('ana_sayfa'))


        # TEMİZLEME AŞAMASI (v10)
        df['HESAP KODU'] = df['HESAP KODU'].astype(str)
        df_clean = df.dropna(subset=['HESAP ADI']).copy() 
        df_final = df_clean[df_clean['HESAP KODU'].str.contains(r'\.', na=False)].copy() 
        
        # Veriyi JSON formatında şifreleyip Session'da sakla
        session['dataframe_json'] = df_final.to_json()
        
        flash(f"Başarılı! Dosyanız temizlendi ve denetim için hazır. Net {len(df_final)} alt hesap bulundu.")
        return redirect(url_for('ana_sayfa'))
        
    except Exception as e:
        # HATA KAYDI: Eğer buraya düşerse, dosya çok büyüktür veya format bozuktur.
        flash(f"YÜKLEME SIRASINDA KRİTİK HATA! (Kod hatası veya büyük dosya): {str(e)}")
        return redirect(url_for('ana_sayfa'))


# --- DENETİMİ BAŞLAT (BUTONLA) ---
@app.route('/denetle', methods=['GET'])
def denetle():
    # ... (Denetim kodu v15 ile aynı, BORÇ/ALACAK kaydırma dahil)
    
    if not MUHASEBE_KURALLARI:
        flash("Hata: Kural dosyası yüklenmediği için analiz yapılamıyor.")
        return redirect(url_for('ana_sayfa'))

    if 'dataframe_json' not in session:
        flash("Hata: Denetlenecek veri bulunamadı! Lütfen önce dosyayı yükleyin.")
        return redirect(url_for('ana_sayfa'))

    try:
        df_final = pd.read_json(session['dataframe_json'])

        # --- BORÇ/ALACAK KAYDIRMA İŞLEMİ (v12'nin kayıp parçası) ---
        df_final['BORÇ_HAM'] = pd.to_numeric(df_final['BORÇ'], errors='coerce')
        df_final['ALACAK_HAM'] = pd.to_numeric(df_final['ALACAK'], errors='coerce')
        df_error = df_final[df_final['BORÇ_HAM'].isna() & df_final['ALACAK_HAM'].isna()].copy()
        
        def extract_amount(row):
            text = str(row['DETAY']) + " " + str(row['AÇIKLAMA'])
            match = re.search(r'(\d[\d\.\,]+)', text) 
            if match:
                return float(match.group(1).replace('.', '').replace(',', '.')) 
            return 0.0

        if not df_error.empty:
            df_error.loc[:, 'BORÇ_YENİ'] = df_error.apply(extract_amount, axis=1)
            df_error.loc[:, 'ALACAK_YENİ'] = 0.0
            
            df_final.update(df_error[['BORÇ_YENİ']].rename(columns={'BORÇ_YENİ': 'BORÇ'}))
            df_final.update(df_error[['ALACAK_YENİ']].rename(columns={'ALACAK_YENİ': 'ALACAK'}))
            
            df_final['BORÇ'] = df_final['BORÇ'].combine_first(df_final['BORÇ_HAM']).fillna(0)
            df_final['ALACAK'] = df_final['ALACAK'].combine_first(df_final['ALACAK_HAM']).fillna(0)

        df_final = df_final.drop(columns=['BORÇ_HAM', 'ALACAK_HAM'], errors='ignore')
        
        # --- BORÇ/ALACAK DENETİM MOTORU (v15) ---
        
        df_final['HATA_DURUMU'] = ''
        
        for index, row in df_final.iterrows():
            try:
                ana_hesap = str(row['HESAP KODU']).split('.')[0].strip()
                ana_hesap_ilk_uc = ana_hesap[:3]
            except:
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
        cikti += f"<b style='color: red;'>TESPİT EDİLEN TERS KAYIT/HATA SAYISI: {total_errors}</b><br>"
        cikti += f"<small>(Not: 'HATA_DURUMU' boşsa kayıt kurala uygundur.)</small><br><br>"
        
        df_final['BORÇ'] = df_final['BORÇ'].round(2)
        df_final['ALACAK'] = df_final['ALACAK'].round(2)
        
        df_final = df_final.fillna('')
        
        cols = ['HATA_DURUMU'] + [col for col in df_final.columns if col not in ['HATA_DURUMU', 'HESAP KODU', 'HESAP_KODU_STR']]
        df_final = df_final[['HESAP KODU'] + cols] 
        
        return cikti + df_final.head(ROW_LIMIT).to_html(na_rep='', justify='left')

    except Exception as e:
        flash(f"DENETİM MOTORU KRİTİK HATA VERDİ: {str(e)}")
        return redirect(url_for('ana_sayfa'))

# --- HTML ve Diğer Fonksiyonlar (Aynı) ---
@app.route('/', methods=['GET'])
def ana_sayfa():
    # ...
    data_loaded = 'dataframe_json' in session
    return render_template('index.html', data_loaded=data_loaded)

# ... (Diğer fonksiyonlar)
@app.teardown_request
def cleanup(exception=None):
    pass
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
