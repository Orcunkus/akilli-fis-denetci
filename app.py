from flask import Flask, render_template, request, flash
import pandas as pd
import os
import io # CSV okumak için gerekebilir

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

    if file:
        try:
            filename = file.filename
            df = None # DataFrame'i önce boş tanımlayalım
            file_type = ""

            # --- YENİ AKILLI KOD ---
            # 1. Dosya uzantısını kontrol et
            if filename.endswith('.csv'):
                file_type = "CSV"
                # CSV okuyucuyu çalıştır.
                # Türkçe Yevmiye Defterleri genelde Excel'den gelir ve ; (noktalı virgül) ile ayrılır.
                # Başlık atlama (skiprows) Excel ile aynı (header=5 yerine skiprows=6)
                # Not: CSV'de satır sayımı 0'dan değil 1'den başlar, bu yüzden 6 satır atla diyoruz.
                try:
                    df = pd.read_csv(file, sep=';', skiprows=6, encoding='latin1')
                except Exception as e_csv:
                    # Hata olursa, belki de virgülledir veya UTF-8'dir?
                    file.seek(0) # Dosyayı başa sar
                    try:
                        df = pd.read_csv(file, sep=',', skiprows=6, encoding='utf-8')
                    except Exception as e_csv_2:
                         return f"CSV dosyası okunamadı. (Noktalı virgül ve virgül denendi). Hata: {str(e_csv_2)}"

            elif filename.endswith('.xlsx'):
                file_type = "Excel"
                # Eski kodumuz, Excel için çalışmaya devam ediyor
                df = pd.read_excel(file, engine='openpyxl', header=5)
            
            else:
                return "Desteklenmeyen dosya formatı. Lütfen .xlsx veya .csv yükleyin."
            
            # --- İSTEDİĞİN GÜNCELLEMELER ---
            
            # 1. Toplam satır sayısını al
            total_rows = len(df)
            
            cikti = f"Dosya ({file_type}) başarıyla okundu! **Toplam {total_rows} satır** yüklendi. <br><br>"
            cikti += "<b>Algılanan Sütunlar:</b> " + ", ".join(df.columns) + "<br><br>"
            
            # 2. .head() kaldırıldı (hepsini yükle) ve na_rep='' eklendi ('NaN' gitsin)
            cikti += df.to_html(na_rep='')

            return cikti
            
        except Exception as e:
            return f"Genel bir hata oluştu: {str(e)}"

    return "Bir hata oluştu."

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
