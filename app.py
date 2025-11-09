from flask import Flask, render_template, request, flash
import pandas as pd
import os

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
            # --- GÜNCELLEME BURADA ---
            # Pandas'a "header=4" ekleyerek 5. satırdan (index 4) okumaya başlamasını söylüyoruz.
            # İlk 4 satırı (0-3) otomatik olarak atlayacak.
            df = pd.read_excel(file, engine='openpyxl', header=4)
            
            # --- RAPORLAMA ---
            # Artık bize HESAP KODU, AÇIKLAMA gibi "gerçek" sütunları göstermesi lazım.
            cikti = "Dosya başarıyla okundu VE temizlendi! (Render.com) <br><br>"
            cikti += "Verinin (Temizlenmiş) İlk 5 Satırı: <br>"
            
            # Hata ayıklama: Sütun adlarını yazdıralım
            cikti += "<b>Algılanan Sütunlar:</b> " + ", ".join(df.columns) + "<br><br>"
            
            # DataFrame'i HTML'e çevir
            cikti += df.head().to_html() 

            return cikti
            
        except Exception as e:
            return f"Dosya okunurken bir hata oluştu: {str(e)}"

    return "Bir hata oluştu."

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
