from flask import Flask, render_template, request, flash
import pandas as pd
import os
import io 

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin" 

# Sunucuyu çökertmeyecek güvenli bir limit
ROW_LIMIT = 500

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
                # CSV'de 6 satır atla = 7. satırdan (header) başla
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
            # Excel'de 5. index = 6. satır (header)
            df = pd.read_excel(file, engine='openpyxl', header=5)
        
        else:
            return "Desteklenmeyen dosya formatı. Lütfen .xlsx veya .csv yükleyin."
        
        # --- YENİ AKILLI FİLTRE (v2) ---
        
        # 1. 'BORÇ' ve 'ALACAK' sütunlarını sayıya çevir. Sayı olmayanlar 'NaN' olacak.
        df['BORÇ'] = pd.to_numeric(df['BORÇ'], errors='coerce')
        df['ALACAK'] = pd.to_numeric(df['ALACAK'], errors='coerce')

        # 2. Hem BORÇ hem de ALACAK sütunu 'NaN' (boş) olan satırları at.
        #    Bu, tüm 'TOPLAM', 'FİŞ AÇIKLAMA', 'MAHSUP' ve boş satırları temizler.
        df_clean = df.dropna(subset=['BORÇ', 'ALACAK'], how='all').copy()
        
        # --- İSTEK: SADECE ALT HESAPLAR ---
        # 3. 'HESAP KODU'nu metin (string) olarak ele al
        df_clean['HESAP KODU'] = df_clean['HESAP KODU'].astype(str)
        
        # 4. İçinde '.' (nokta) olan HESAP KODU'larını (yani alt hesapları) tut
        df_final = df_clean[df_clean['HESAP KODU'].str.contains(r'\.', na=False)].copy()
        
        # ----------------------------------------
        
        # RAPORLAMA (LİMİTLİ)
        total_rows_raw = len(df)
        total_rows_final = len(df_final) # Artık TEMİZLENMİŞ satır sayısı
        
        cikti = f"Dosya ({file_type}) başarıyla okundu! (Toplam {total_rows_raw} ham satır) <br>"
        cikti += f"Çöp veriler (TOPLAM, Fiş Başlıkları) ayıklandı. <br>"
        cikti += f"Sadece alt hesaplar (içinde '.' olanlar) filtrelendi. **Net {total_rows_final} satır** veri bulundu. <br>"
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
