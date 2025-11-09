from flask import Flask, render_template, request, flash
import pandas as pd
import os
import io 

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin" 

# --- YENİ LİMİTİMİZ ---
# Sunucuyu çökertmemek için en fazla kaç satır göstereceğimizi belirleyelim.
ROW_LIMIT = 200

@app.route('/')
def ana_sayfa():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'dosya' not in request.files:
        return "Dosya seçilmedi!"

    file = request.files['dosya']

    if file.filename == '':
        return "Dosya adı boş!"
    
    if not file:
        return "Dosya objesi boş!"

    try:
        filename = file.filename
        df = None
        file_type = ""

        if filename.endswith('.csv'):
            file_type = "CSV"
            # CSV okuyucuyu (skiprows=6 ile) geri getiriyoruz
            try:
                file.seek(0)
                # Not: CSV'de satır sayımı 1'den başlar, 6 satır atla = 7. satırdan başla
                df = pd.read_csv(file, sep=';', skiprows=6, encoding='latin1')
            except Exception as e_csv1:
                file.seek(0)
                try:
                    df = pd.read_csv(file, sep=',', skiprows=6, encoding='utf-8')
                except Exception as e_csv2:
                    return f"CSV dosyası okunamadı (skiprows=6 denendi). Hata: {str(e_csv2)}"

        elif filename.endswith('.xlsx'):
            file_type = "Excel"
            # Excel kodumuz (header=5 ile) zaten çalışıyordu
            file.seek(0) 
            df = pd.read_excel(file, engine='openpyxl', header=5)
        
        else:
            return "Desteklenmeyen dosya formatı. Lütfen .xlsx veya .csv yükleyin."
        
        # --- RAPORLAMA (LİMİTLİ) ---
        
        total_rows = len(df)
        
        cikti = f"Dosya ({file_type}) başarıyla okundu! **Toplam {total_rows} satır** bulundu. <br>"
        cikti += f"Sunucu çökmesin diye **ilk {ROW_LIMIT} satır** gösteriliyor...<br><br>"
        
        cikti += "<b>Algılanan Sütunlar:</b> " + ", ".join(df.columns) + "<br><br>"
        
        # 'NaN' gitsin (na_rep='') VE ilk 200 satırı göster (.head(ROW_LIMIT))
        cikti += df.head(ROW_LIMIT).to_html(na_rep='') 

        return cikti
        
    except Exception as e:
        return f"GENEL HATA: {str(e)}"
