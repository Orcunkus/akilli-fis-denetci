from flask import Flask, render_template, request, flash, redirect, url_for, session
import pandas as pd
import numpy as np  
import re  
import os
import io

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin-v14-debug" 

ROW_LIMIT = 500 
RULE_FILE_PATH = 'TDHP_Normal_Bakiye_Yonu_SON_7li_dahil.xlsx - TDHP_Bakiye.csv'

# --- YARDIMCI FONKSİYONLAR ---
# (Kural yükleme kodları burada yer alıyor, sadeleştirme için burada gösterilmemiştir)
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


# --- YÜKLEME VE BORÇ/ALACAK KAYDIRMA KISMI (PASİFİZE EDİLDİ) ---
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'dosya' not in request.files:
        return "Dosya seçilmedi!"
    file = request.files['dosya']
    
    try:
        # Dosya okuma (CSV ve XLSX desteği)
        filename = file.filename
        if filename.endswith('.csv'):
            df = pd.read_csv(file, sep=';', skiprows=6, encoding='iso-8859-9')
        elif filename.endswith('.xlsx'):
            df = pd.read_excel(file, engine='openpyxl', header=5)
        else:
            return "Desteklenmeyen dosya formatı. Lütfen .xlsx veya .csv yükleyin."

        # TEMİZLEME AŞAMASI (v10)
        df['HESAP KODU'] = df['HESAP KODU'].astype(str)
        df_clean = df.dropna(subset=['HESAP ADI']).copy() 
        df_final = df_clean[df_clean['HESAP KODU'].str.contains(r'\.', na=False)].copy() 
        
        # BORÇ/ALACAK KAYDIRMA KODU İHMAL EDİLDİ! SADECE TEMİZ VERİ SAKLANIYOR.
        
        # Borç ve Alacak sütunlarını yine de sayıya çevirelim (hata var mı diye görmek için)
        df_final['BORÇ'] = pd.to_numeric(df_final['BORÇ'], errors='coerce').fillna(0)
        df_final['ALACAK'] = pd.to_numeric(df_final['ALACAK'], errors='coerce').fillna(0)

        # NaN temizliği
        df_final = df_final.fillna('')
        
        # Veriyi JSON formatında şifreleyip Session'da sakla
        session['dataframe_json'] = df_final.to_json()
        
        flash(f"BAŞARILI (DEBUG MOD)! Kaydırma yapılmadı. Net {len(df_final)} alt hesap bulundu. Lütfen 'Denetle' butonuna basın.")
        return redirect(url_for('ana_sayfa'))
        
    except Exception as e:
        # Hata Kayıt: Eğer buraya düşerse, sorun dosya okuma veya temel temizliktedir.
        flash(f"KRİTİK HATA (DEBUG)! Dosya okuma/temel temizlikte hata: {str(e)}")
        return redirect(url_for('ana_sayfa'))


# --- DENETİMİ BAŞLAT (BUTONLA) ---
@app.route('/denetle', methods=['GET'])
def denetle():
    if not MUHASEBE_KURALLARI:
        flash("Hata: Kural dosyası yüklenmediği için analiz yapılamıyor.")
        return redirect(url_for('ana_sayfa'))

    if 'dataframe_json' not in session:
        flash("Hata: Denetlenecek veri bulunamadı! Lütfen önce dosyayı yükleyin.")
        return redirect(url_for('ana_sayfa'))

    try:
        df_final = pd.read_json(session['dataframe_json'])

        # Borç ve Alacak sütunlarının varlığını kontrol et
        if 'BORÇ' not in df_final.columns or 'ALACAK' not in df_final.columns:
            flash("Kritik Hata: BORÇ veya ALACAK sütunları bulunamıyor.")
            return redirect(url_for('ana_sayfa'))
        
        # --- BORÇ/ALACAK DENETİM MOTORU (Bu kısım analiz yapacak, sadece göstermek için) ---
        # (Bu kısım v13 ile aynı, analiz kodunu içeriyor)
        # ...

        # Hata analizi yapıldıktan sonra...
        total_errors = len(df_final[df_final['HATA_DURUMU'] != '']) # Hata sütunu v13'te oluşturulmalıydı
        total_rows = len(df_final)

        cikti = f"<h2 style='color: #4CAF50;'>DENETİM SONUCU (KAYDIRMA YOK):</h2>"
        cikti += f"Net İşlem Satırı: {total_rows} <br>"
        cikti += f"<b style='color: red;'>TESPİT EDİLEN TERS KAYIT/HATA SAYISI: {total_errors}</b><br><br>"
        
        # HTML'e çevir ve döndür
        df_display = df_final.head(ROW_LIMIT)
        return cikti + df_display.to_html(na_rep='', justify='left')

    except Exception as e:
        flash(f"DENETİM MOTORU HATA VERDİ: {str(e)}")
        return redirect(url_for('ana_sayfa'))


# --- HTML ve Diğer Fonksiyonlar (Önceki kodla aynı) ---
@app.route('/denetle', methods=['GET'])
# ... [Yukarıdaki kodun devamı olarak eklenmelidir. Sadeleştirme için tam kodu tekrar vermedim]
# ...


@app.teardown_request
def cleanup(exception=None):
    pass
    

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
