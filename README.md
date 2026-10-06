# BulBana - Akilli Ilan Takip ve Anlik Bildirim Sistemi

Sahibinden uzerindeki ozel kriterli ilanlari (vasita, emlak, ikinci el) otomatik tarayan ve kriterlere uygun yeni ilan tespit edildiginde kullaniciya Telegram uzerinden anlik bildirim gonderen acik kaynakli asistan platformu.

[Detayli Proje Dokumani](docs/PROJECT_PLAN.md)

---

## Temel Ozellikler

* **Kullanici Yonetimi:** Kullanici adi ile sade oturum ve profil yonetimi.
* **Kapsamli Kriter Tanimlama:** Marka, model, yil araligi, kilometre, vites, yakit, renk, hasarsizlik durumu (agir hasar haric tutma), emlak oda sayisi, m2 ve fiyat araligi filtreleme.
* **Akilli Filtreleme ve Tarama Motoru:** Arka planda periyodik calisan, ilan baslik ve ozelliklerini kriterlerle karsilastiran servis.
* **Anlik Telegram Bildirimi:** Eslesen yeni ilan tespit edildiginde fotografli, detayli ve dogrudan linkli bildirim.
* **Mobil Uyumlu Web Paneli:** Modern ve responsive kontrol paneli arayuzu.

---

## Kurulum ve Calistirma

### 1. Bagimliliklarin Yuklenmesi
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Veritabani Migrasyonlari
```bash
python manage.py migrate
```

### 3. Sunucuyu Baslatma
```bash
python manage.py runserver
```

### 4. Tarama Motorunu Calistirma
```bash
# Tek seferlik tarama:
python manage.py run_scanner

# 5 dakikada bir otomatik dongu:
python manage.py run_scanner --loop --interval 5
```

---

## Testlerin Calistirilmasi

```bash
python manage.py test
```
