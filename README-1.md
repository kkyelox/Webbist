# BIST200 Analiz Botu — Web Kurulum Rehberi

## 📁 Dosya Yapısı
```
projen/
├── web_app.py          ← Ana uygulama (bu dosya)
├── requirements.txt    ← Kütüphaneler
└── bist_logs/          ← Otomatik oluşur, tüm loglar buraya kaydedilir
    ├── gunluk_log.txt
    ├── haftalik_log.txt
    ├── guclu_al_log.txt
    ├── stonks.json
    └── model_usage.json
```

---

## 🖥️ Lokal Test (Bilgisayarında)

### 1. Python paketleri kur
```bash
pip install -r requirements.txt
```

### 2. Çalıştır
```bash
streamlit run web_app.py
```
Tarayıcıda otomatik açılır: http://localhost:8501

---

## 🌐 GitHub'a Yükleme

### 1. GitHub'a hesap aç
- github.com → Sign up

### 2. Yeni repo oluştur
- github.com'da sağ üst köşe → + → New repository
- İsim: `bist-botu`
- Public seç → Create repository

### 3. Dosyaları yükle
Repo sayfasında "uploading an existing file" linkine tıkla:
- `web_app.py` sürükle bırak
- `requirements.txt` sürükle bırak
- Commit changes tıkla

---

## 🚀 Streamlit Cloud'a Deploy (Ücretsiz, Sürekli Çalışır)

### 1. share.streamlit.io'ya git
- "Continue with GitHub" → GitHub hesabınla giriş yap

### 2. Uygulama oluştur
- "New app" tıkla
- Repository: `bist-botu`
- Branch: `main`
- Main file path: `web_app.py`

### 3. Gemini API Key'i Secrets'a ekle (GÜVENLİ YÖNTEM)
Deploy ekranında "Advanced settings" → "Secrets":
```toml
GEMINI_API_KEY = "AIzaSy..."
```

### 4. Deploy tıkla
~3 dakika bekle → https://senadiniz-bist-botu.streamlit.app adresi hazır!

---

## ⚡ Özellikler
- **Tarama sekmesi**: BIST200 tümünü tara, filtrele, sırala
- **Tek hisse**: Detaylı teknik analiz
- **AI Analiz**: Gemini ile derin analiz
- **Portföy**: Sanal yatırım simülatörü
- **Log**: bist_logs klasörüne kayıt + indirme
- **Otomatik tarama**: Sidebar'dan aç, borsa saatlerinde sürekli çalışır

---

## ⚠️ Önemli Notlar
- bist_logs klasörü script ile aynı dizinde otomatik oluşur
- Streamlit Cloud'da deploy edince loglar cloud sunucusunda saklanır
- Uygulama uyku moduna geçmesin diye https://uptimerobot.com ile URL'yi ping'leyebilirsin
- Yatırım tavsiyesi değildir!
