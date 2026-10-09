# BulBana - Akıllı İlan Takip ve Anlık Bildirim Sistemi

Sahibinden üzerindeki özel kriterli ilanları (vasıta, emlak, ikinci el) otomatik tarayan ve kriterlere uygun yeni ilan tespit edildiğinde kullanıcıya Telegram üzerinden anlık bildirim gönderen açık kaynaklı asistan platformu.

[Detaylı Proje Dokümanı](docs/PROJECT_PLAN.md)

---

## Temel Özellikler

* **Kullanıcı Yönetimi:** Kullanıcı adı ile sade oturum ve profil yönetimi.
* **Kapsamlı Kriter Tanımlama:** Marka, model, yıl aralığı, kilometre, vites, yakıt, renk, hasarsızlık durumu (ağır hasar hariç tutma), emlak oda sayısı, m2 ve fiyat aralığı filtreleme.
* **Akıllı Filtreleme ve Tarama Motoru:** Arka planda periyodik çalışan, ilan başlık ve özelliklerini kriterlerle karşılaştıran servis.
* **Anlık Telegram Bildirimi:** Eşleşen yeni ilan tespit edildiğinde fotoğraflı, detaylı ve doğrudan linkli bildirim.
* **Mobil Uyumlu Web Paneli:** Modern ve duyarlı (responsive) kontrol paneli arayüzü.

---

## Kurulum ve Çalıştırma

### 1. Bağımlılıkların Yüklenmesi
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Veritabanı Migrasyonları
```bash
python manage.py migrate
```

### 3. Sunucuyu Başlatma
```bash
python manage.py runserver
```

### 4. Tarama Motorunu Çalıştırma
```bash
# Tek seferlik tarama:
python manage.py run_scanner

# 5 dakikada bir otomatik döngü:
python manage.py run_scanner --loop --interval 5
```

---

## Testlerin Çalıştırılması

```bash
python manage.py test
```
