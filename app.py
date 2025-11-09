from flask import Flask, render_template, request, flash
import pandas as pd
import os
import io 

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin" 

ROW_LIMIT = 500 # Güvenli limitimiz

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

        # Dosya okuma mantığımız (CSV ve Excel için)
        if filename.endswith('.csv'):
            file_type = "CSV"
            try:
                file.seek(0)
                df = pd.read_csv(file, sep=';', skiprows=6, encoding='latin1')
            except Exception as e_csv1:
                file.seek(0)
                try:
                    df = pd.read_csv(file, sep=',', skiprows=6, encoding='utf-8')
                except Exception as e_csv2:
                    return f"CSV dosyası okunamadı (skiprows=6 denendi). Hata: {str(e_csv2)}"

        elif filename.endswith('.xlsx'):
            file_type = "Excel"
            file.seek(0) 
            df = pd.read_excel(file, engine='openpyxl', header=5)
        
        else:
            return "Desteklenmeyen dosya formatı. Lütfen .xlsx veya .csv yükleyin."
        
        # --- YENİ AKILLI FİLTRE (v3) ---
        
        # 1. 'BORÇ' ve 'ALACAK' sütunlarını sayıya çevir (çöp temizliği için hazırlık)
        df['BORÇ'] = pd.to_numeric(df['BORÇ'], errors='coerce')
        df['ALACAK'] = pd.to_numeric(df['ALACAK'], errors='coerce')

        # 2. 'AÇIKLAMA' ve 'DETAY' sütunlarına bakarak çöp veriyi (ana/ara toplamları) temizle
        #    Eğer bir satırın hem AÇIKLAMA'sı hem de DETAY'ı boşsa (NaN) O SATIRI AT.
        #    Sadece gerçek işlem satırları kalacak.
        df_clean = df.dropna(subset=['AÇIKLAMA', 'DETAY'], how='all').copy()
        
        # 3. (Ekstra Temizlik) Kalan veride, hem BORÇ hem ALACAK boşsa (bazen olur) onları da at.
        df_final = df_clean.dropna(subset=['BORÇ', 'ALACAK'], how='all').copy()
        
        # ----------------------------------------
        
        # RAPORLAMA (LİMİTLİ)
        total_rows_raw = len(df)
        total_rows_final = len(df_final) # Artık TEMİZLENMİŞ satır sayısı
        
        cikti = f"Dosya ({file_type}) başarıyla okundu! (Toplam {total_rows_raw} ham satır) <br>"
        cikti += f"SADECE GERÇEK İŞLEM SATIRLARI FİLTRELENDİ ('Açıklama' ve 'Detay'ı dolu olanlar). <br>"
        cikti += f"**Net {total_rows_final} satır** işlem bulundu. <br>"
        cikti += f"Sunucu için **ilk {ROW_LIMIT} satır** gösteriliyor...<br><br>"
        
        cikti += "<b>Algılanan Sütunlar:</b> " + ", ".join(df_final.columns) + "<br><br>"
        
        # 'NaN' gitsin (na_rep='') VE ilk 500 satırı göster
        cikti += df_final.head(ROW_LIMIT).to_html(na_rep='') 

        return cikti
        
    except Exception as e:
        return f"GENEL HATA: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
