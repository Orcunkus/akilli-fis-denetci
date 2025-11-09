from flask import Flask, render_template, request, flash
import pandas as pd
import os
import io 

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin" 

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
            
            # --- HATA AYIKLAMA 1. DENEME: CSV (Noktalı Virgül) ---
            # 'skiprows=6' KALDIRILDI. Muhtemelen CSV'de o başlıklar yok.
            # 'latin1' (veya ISO-8859-9) Türkçe için yaygındır.
            try:
                file.seek(0) # Dosyayı başa sar (her deneme için önemli)
                df = pd.read_csv(file, sep=';', encoding='latin1')
            except Exception as e_csv1:
                
                # --- HATA AYIKLAMA 2. DENEME: CSV (Virgül) ---
                try:
                    file.seek(0) # Dosyayı başa sar
                    df = pd.read_csv(file, sep=',', encoding='utf-8')
                except Exception as e_csv2:
                    # İkisi de başarısız olursa hataları göster
                    return f"CSV dosyası okunamadı. <br><br>Hata 1 (Noktalı Virgül denemesi) : {str(e_csv1)} <br><br> Hata 2 (Virgül denemesi) : {str(e_csv2)}"

        elif filename.endswith('.xlsx'):
            file_type = "Excel"
            # Excel kodumuz zaten çalışıyordu, buna dokunmuyoruz.
            file.seek(0) 
            df = pd.read_excel(file, engine='openpyxl', header=5)
        
        else:
            return "Desteklenmeyen dosya formatı. Lütfen .xlsx veya .csv yükleyin."
        
        # --- RAPORLAMA (GÜNCELLENDİ) ---
        
        total_rows = len(df)
        
        cikti = f"Dosya ({file_type}) başarıyla okundu! **Toplam {total_rows} satır** bulundu. (DEBUG MODU) <br><br>"
        cikti += "<b>Algılanan Sütunlar:</b> " + ", ".join(df.columns) + "<br><br>"
        
        # 'NaN' gitsin VE sunucu çökmesin diye ilk 100 satırı göster
        cikti += df.head(100).to_html(na_rep='') 

        return cikti
        
    except Exception as e:
        # Bu, en dıştaki hata yakalayıcı.
        return f"GENEL HATA (en dış blok): {str(e)}"
