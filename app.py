from flask import Flask, render_template, request, flash, redirect, url_for, session
import pandas as pd
import numpy as np  
import re  
import os
import io

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin-v25-style" 

ROW_LIMIT = 500 
RULE_FILE_PATH = 'TDHP_Normal_Bakiye_Yonu_SON_7li_dahil.xlsx - TDHP_Bakiye.csv'

# ... (Yardımcı fonksiyonlar aynı kalıyor)
# ...


# --- YÜKLEME VE HAM VERİ GÖSTERİMİ ---
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

        # --- FİLTRE VEYA KAYDIRMA YOK ---

        # Veriyi olduğu gibi ekrana basıyoruz.
        total_rows = len(df)

        cikti = f"<h2 style='color: #4CAF50;'>HAM VERİ GÖSTERİMİ BAŞARILI!</h2>"
        cikti += f"Net İşlem Satırı: {total_rows} <br>"
        cikti += f"<b>Lütfen aşağıdaki tablonun Yevmiye Defteri ile aynı olduğunu kontrol edin.</b><br><br>"
        
        # Ekrana basmadan önce NaN'ları temizle
        df = df.fillna('')
        
        # DataFrame'i HTML'e çevir
        html_output = df.head(ROW_LIMIT).to_html(na_rep='', justify='left')

        # --- YENİ KOD: STİL UYGULAMASI (MAHSUP FİŞLERİNİ KIRMIZI VE KALIN YAPMA) ---
        # REGEX: Herhangi bir hücrede "xxxxx-----MAHSUP" düzeni arar
        # Bu Mahsup fişi başlangıcını bulup etiketlerle sarar.
        html_output = re.sub(
            r'(\d{5}-----.*?MAHSUP-----.*?TL)',
            r"<b style='color: red;'>\1</b>", 
            html_output, 
            flags=re.IGNORECASE | re.DOTALL
        )

        cikti += html_output
        return cikti

    except Exception as e:
        flash("error", f"KRİTİK VERİ OKUMA HATASI! Hata Kodu: {str(e)}")
        return redirect(url_for('ana_sayfa'))


# --- DENETİM VE DİĞER KODLAR (AYNI) ---
# ... (Diğer fonksiyonlar ve HTML kısmı v24 ile aynı kalır)
@app.route('/denetle', methods=['GET'])
def denetle():
    flash("error", "Denetim butonu şu an pasiftir. Ham veriyi kontrol ediyoruz.")
    return redirect(url_for('ana_sayfa'))


@app.route('/', methods=['GET'])
def ana_sayfa():
    # Artık denetim butonu yok
    data_loaded = False 
    return render_template('index.html', data_loaded=data_loaded)

@app.teardown_request
def cleanup(exception=None):
    pass
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
