from flask import Flask, render_template, request, flash
import pandas as pd
import os
import io 

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin" 

# Toplam 244 satırsa, 500'lük bir limit bizim için çok güvenli.
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
        
        # --- İŞTE YENİ AKILLI FİLTRE BURADA ---
        
        # 1. 'HESAP KODU' sütununu sayıya çevirmeye zorla.
        #    "HESAP KODU", "00115---", "TOPLAM" gibi metinler 'NaN' (boş) olacak.
        df['HESAP KODU'] = pd.to_numeric(df['HESAP KODU'], errors='coerce')

        # 2. Sadece 'HESAP KODU' bir sayı olan (NaN olmayan) satırları tut.
        #    Bu, tüm "TOPLAM", "MAHSUP", "FİŞ AÇIKLAMA" ve boş satırları temizler.
        df = df.dropna(subset=['HESAP KODU'])

        # 3. 'HESAP KODU'nu daha temiz görünmesi için tamsayıya çevir (zorunlu değil)
        try:
            df['HESAP KODU'] = df['HESAP KODU'].astype(int)
        except Exception:
            pass # Hata olursa es geç, sorun değil
            
        # ----------------------------------------
        
        # RAPORLAMA (LİMİTLİ)
        total_rows = len(df) # Artık TEMİZLENMİŞ satır sayısı
        
        cikti = f"Dosya ({file_type}) başarıyla okundu VE TEMİZLENDİ! <br>"
        cikti += f"Çöp veriler (TOPLAM, Fiş Başlıkları) ayıklandı. **Net {total_rows} satır** veri bulundu. <br>"
        cikti += f"Sunucu için **ilk {ROW_LIMIT} satır** gösteriliyor...<br><br>"
        
        cikti += "<b>Algılanan Sütunlar:</b> " + ", ".join(df.columns) + "<br><br>"
        
        # 'NaN' gitsin (na_rep='') VE ilk 500 satırı göster
        cikti += df.head(ROW_LIMIT).to_html(na_rep='') 

        return cikti
        
    except Exception as e:
        return f"GENEL HATA: {str(e)}"
