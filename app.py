# SADELEŞTİRİLMİŞ V17 KODU: SADECE HATA DÜZELTME
from flask import Flask, render_template, request, flash, redirect, url_for, session
# ... (Diğer importlar)

app = Flask(__name__)
app.secret_key = "cokgizlibirkey-render-icin-v17-nihai" 
# ... (RULE_FILE_PATH, load_rules, MUHASEBE_KURALLARI tanımları aynı)
# ... (load_rules, MUHASEBE_KURALLARI tanımları aynı)

# ... (load_rules, MUHASEBE_KURALLARI tanımları aynı)
def load_rules():
    try:
        # Kural dosyası yükleme (Aynı)
        rules_df = pd.read_csv(RULE_FILE_PATH, sep=';', encoding='iso-8859-9')
        rules_df.columns = ['HESAP_KODU', 'HESAP_ADI', 'BAKIYE_YONU', 'BAKIYE_YONU_ING'] + list(rules_df.columns[4:])
        rules_df['HESAP_KODU'] = pd.to_numeric(rules_df['HESAP_KODU'], errors='coerce')
        rules_df = rules_df.dropna(subset=['HESAP_KODU'])
        rules_df['HESAP_KODU'] = rules_df['HESAP_KODU'].astype(int).astype(str).str[:3]
        rules_df = rules_df.drop_duplicates(subset=['HESAP_KODU']).set_index('HESAP_KODU')
        rules_df['BAKIYE_YONU'] = rules_df['BAKIYE_YONU'].str.upper().str.strip().replace({'BORÇ': 'B', 'ALACAK': 'A', 'HESAP TÜRÜNE GÖRE': 'H'})
        return rules_df['BAKIYE_YONU'].to_dict()
    except Exception as e:
        print(f"Kural dosyası yüklenirken HATA oluştu: {e}")
        return None

MUHASEBE_KURALLARI = load_rules()


@app.route('/')
def ana_sayfa():
    data_loaded = 'dataframe_json' in session
    return render_template('index.html', data_loaded=data_loaded)


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'dosya' not in request.files:
        flash("error", "HATA! Dosya Seçilmedi.") # Kategori eklendi
        return redirect(url_for('ana_sayfa'))
    
    file = request.files['dosya']
    
    if file.filename == '':
        flash("error", "HATA! Dosya seçildi ama dosya adı boş.")
        return redirect(url_for('ana_sayfa'))
    
    try:
        # Dosya okuma (Aynı)
        # ...

        # TEMİZLEME AŞAMASI (Aynı)
        # ...
        
        session['dataframe_json'] = df_final.to_json()
        
        flash("success", f"Başarılı! Dosyanız temizlendi ve denetim için hazır. Net {len(df_final)} alt hesap bulundu.")
        return redirect(url_for('ana_sayfa'))
        
    except Exception as e:
        # HATA KAYDI: Artık Hata Mesajını Gösterecek.
        flash("error", f"YÜKLEME SIRASINDA KRİTİK HATA! {str(e)}")
        return redirect(url_for('ana_sayfa'))


# ... (Diğer fonksiyonlar aynı)
@app.route('/denetle', methods=['GET'])
def denetle():
    # ... (Denetleme kodunun tamamı aynı)
    
    try:
        # ... (Analiz yapıldı)
        
        # Raporlama:
        # ...
        
        return cikti + df_final.head(ROW_LIMIT).to_html(na_rep='', justify='left')

    except Exception as e:
        flash("error", f"DENETİM MOTORU KRİTİK HATA VERDİ: {str(e)}")
        return redirect(url_for('ana_sayfa'))


@app.teardown_request
def cleanup(exception=None):
    pass
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
