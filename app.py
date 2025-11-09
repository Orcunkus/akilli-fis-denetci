from flask import Flask, render_template, request, flash
import pandas as pd
import os # Render için bu gerekli

# Flask uygulamasını başlat
app = Flask(__name__)
# Yüklenen dosyaların güvenliği için bir secret_key ekleyelim
app.secret_key = "cokgizlibirkey-render-icin" 

# 1. Ana Sayfa: HTML arayüzünü gösterir
@app.route('/')
def ana_sayfa():
    # 'templates' klasöründeki 'index.html' dosyasını arar
    return render_template('index.html')

# 2. Dosya Yükleme: HTML formundan gelen dosyayı işler
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'dosya' not in request.files:
        flash('Dosya seçilmedi!')
        return "Dosya seçilmedi!"

    file = request.files['dosya']

    if file.filename == '':
        flash('Dosya adı boş!')
        return "Dosya adı boş!"

    if file:
        try:
            # Dosyayı hafızada Pandas ile okuyoruz
            df = pd.read_excel(file, engine='openpyxl')
            
            # Veriyi aldığımızı kanıtlamak için ilk 5 satırı string'e çevirelim
            cikti = "Dosya başarıyla okundu! (Render.com) <br><br>"
            cikti += "Verinin İlk 5 Satırı: <br>"
            # Pandas dataframe'ini HTML tablosuna çevirir
            cikti += df.head().to_html() 

            return cikti
            
        except Exception as e:
            return f"Dosya okunurken bir hata oluştu: {str(e)}"

    return "Bir hata oluştu."

# Bu, Render'ın (Gunicorn kullanarak) uygulamayı bulması için gereklidir
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)