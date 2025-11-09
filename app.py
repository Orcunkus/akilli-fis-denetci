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
            # --- YENİ GÜNCELLEME BURADA ---
            # Header'ın 6. satırda (index 5) olduğunu anladık.
            df = pd.read_excel(file, engine='openpyxl', header=5)
            
            # --- RAPORLAMA ---
            # Artık bize HESAP KODU, AÇIKLAMA gibi "gerçek" sütunları göstermesi lazım.
            cikti = "İŞTE ŞİMDİ OLDU! (Render.com) <br><br>"
            
            # Hata ayıklama: Sütun adlarını yazdıralım
            # Artık burada "HESAP KODU", "HESAP ADI" vb. görmeliyiz.
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
