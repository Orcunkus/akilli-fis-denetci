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
        
        # --- YENİ AKILLI FİLTRE (v6) ---
        
        # AŞAMA 1: ÇÖP VERİYİ (MAHSUP, TOPLAM, FİŞ AÇIKLAMA vb.) TEMİZLE
        # 'HESAP KODU'nu metne çevir (NaN'ları da 'nan' yapar)
        df['HESAP_KODU_STR'] = df['HESAP KODU'].astype(str)
        
        # İçinde 'MAHSUP', 'TOPLAM', 'FİŞ AÇIKLAMA', 'HESAP KODU' (tekrar eden başlık)
        # olmayan satırları tut (case=False -> büyük/küçük harf duyarsız)
        df_clean = df[
            ~df['HESAP_KODU_STR'].str.contains('MAHSUP', na=False, case=False) &
            ~df['HESAP_KODU_STR'].str.contains('TOPLAM', na=False, case=False) &
            ~df['HESAP_KODU_STR'].str.contains('FİŞ AÇIKLAMA', na=False, case=False) &
            ~df['HESAP_KODU_STR'].str.contains('HESAP KODU', na=False, case=False)
        ].copy()

        # AŞAMA 2: ANA/ARA HESAPLARI (Açıklaması boş olanlar) TEMİZLE
        # Geriye kalan temiz veriden (df_clean), 'AÇIKLAMA' ve 'DETAY' sütunları
        # aynı anda boş (NaN) olanları AT.
        df_final = df_clean.dropna(subset=['AÇIKLAMA', 'DETAY'], how='all').copy()

        # ----------------------------------------
        
        # RAPORLAMA (LİMİTLİ)
        total_rows_raw = len(df)
        total_rows_final = len(df_final) # Artık TEMİZLENMİŞ satır sayısı
        
        cikti = f"Dosya ({file_type}) başarıyla okundu! (Toplam {total_rows_raw} ham satır) <br>"
        cikti += f"Tüm çöp satırlar (TOPLAM, MAHSUP, FİŞ AÇIKLAMA) ayıklandı. <br>"
        cikti += f"Açıklaması boş olan Ana/Ara Hesaplar ayıklandı. <br>"
        cikti += f"**Net {total_rows_final} satır** gerçek işlem bulundu. <br>"
        cikti += f"Sunucu için **ilk {ROW_LIMIT} satır** gösteriliyor...<br><br>"
        
        # O geçici sütuna artık ihtiyacımız yok, tabloda görünmesin
        if 'HESAP_KODU_STR' in df_final.columns:
            df_final = df_final.drop(columns=['HESAP_KODU_STR'])
            
        cikti += "<b>Algılanan Sütunlar:</b> " + ", ".join(df_final.columns) + "<br><br>"
        
        # 'NaN' gitsin (na_rep='') VE ilk 500 satırı göster
        cikti += df_final.head(ROW_LIMIT).to_html(na_rep='') 

        return cikti
        
    except Exception as e:
        return f"GENEL HATA: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
