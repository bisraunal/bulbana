# 🔍 BulBana — Sahibinden Akıllı İlan Öneri & Eşleştirme Platformu

---

## 1. Proje Genel Bakışı & Amacı
**BulBana**, Sahibinden platformundaki binlerce ilan arasında tek tek kaybolmak yerine; kullanıcının bütçesine, istediği lokasyona, önceliklerine ve olmazsa olmaz kriterlerine göre Sahibinden ilanlarını tarayan ve kullanıcıya **"Uyum Skoru" (%0 - %100)** ile en uygun ilanları öneren akıllı bir eşleştirme platformudur.

- **Ana Felsefe:** Manuel arama yorgunluğuna son; akıllı kriter eşleştirme ve anında sonuç.
- **Odak Kategoriler:** Emlak (Kiralık/Satılık Daireler), Vasıta (Otomobil, SUV, Motosiklet), İkinci El & Teknoloji (Laptop, Telefon, Donanım).

---

## 2. Temel Özellikler & Fonksiyonlar

### 2.1. Arayış Sihirbazı (`UserPreference`)
Kullanıcılar ister üye olarak ister misafir olarak arayış profilleri oluşturabilir:
- **Kategori Seçimi:** Emlak, Vasıta veya Teknoloji.
- **Bütçe Aralığı:** Minimum ve maksimum hedef fiyat (TL).
- **Hedef Lokasyon:** Şehir ve ilçe/semt bazlı hedefleme.
- **Olmazsa Olmaz Özellikler:** Virgülle ayrılmış anahtar kelimeler *(Örn: "balkon, metro, kedi dostu, otomatik vites, 16gb ram")*.
- **Öncelik Modu:** *Dengeli*, *Bütçe/Fiyat Odaklı*, *Konum Odaklı* veya *Özellik/Donanım Odaklı*.

### 2.2. Akıllı Puanlama & Eşleştirme Motoru
Sistem, girilen kriterleri Sahibinden ilanlarıyla karşılaştırarak dinamik bir puan üretir:
* **Fiyat Analizi (%40):** Bütçe sınırına göre tam uyum veya bütçe aşım ceza puanı.
* **Lokasyon Analizi (%30):** Şehir ve ilçe birebir eşleşme katsayısı.
* **Özellik & Kelime Taraması (%20):** İlan başlığı, açıklaması ve teknik parametreler (`specs` JSON) taranarak anahtar kelimelerin bulunması.
* **Öncelik Katsayısı (%10):** Kullanıcının seçtiği önceliğe göre skora pozitif çarpan eklenmesi.

### 2.3. "Neden Senin İçin Uygun?" Akıllı Rozetleri
Her önerilen ilanın altında kullanıcının kriterleriyle neden eşleştiği görsel olarak listelenir:
* 🎯 *Bütçenizin 4.000 TL altında (26.000 TL)*
* 📍 *Hedeflediğiniz Kadıköy Moda konumunda*
* ✨ *Aradığınız kriterler mevcut: balkon, kedi dostu, metro*

### 2.4. Tek Tıkla Favorileme (AJAX)
Kullanıcılar sayfa yenilenmeden ilan kartlarındaki kalp ikonuna tıklayarak ilanları favorilerine kaydedebilir ve profillerinden yönetebilir.

---

## 3. Teknoloji Yığını (Tech Stack)

```mermaid
flowchart TD
    subgraph Frontend["Modern UI & Client Side"]
        HTML["HTML5 & Django Templates"]
        CSS["Custom CSS3 & Bootstrap 5 & Icons"]
        JS["Vanilla JS (Fetch API & AJAX Favorileme)"]
    end

    subgraph Backend["Backend Core"]
        Django["Python 3.11+ / Django 5.x"]
        Auth["Django Standard Auth & Session Engine"]
        Matcher["Akıllı Kriter Eşleştirme Motoru"]
    end

    subgraph Database["Database"]
        Postgres["Supabase PostgreSQL (Transaction Pooler)"]
        SQLite["Local SQLite3 (Geliştirme Modu)"]
    end

    subgraph Hosting["Deployment"]
        Vercel["Vercel Serverless (WSGI Handler)"]
    end

    Frontend --> Backend
    Backend --> Matcher
    Backend --> Postgres
    Backend -. Yerel Test .-> SQLite
    Backend -. Deployed on .-> Vercel
```

---

## 4. Veritabanı Mimarisi (ER Diyagramı)

```mermaid
erDiagram
    AUTH_USER ||--o{ USER_PREFERENCE : creates
    AUTH_USER ||--o{ LISTING_INTERACTION : performs
    CATEGORY ||--|{ LISTING : contains
    CATEGORY ||--o{ USER_PREFERENCE : targets
    LISTING ||--o{ LISTING_INTERACTION : receives

    CATEGORY {
        int id PK
        string name "Kategori Adı"
        string slug "URL Slug"
        string icon "Bootstrap İkon"
    }

    LISTING {
        int id PK
        int category_id FK
        string title "İlan Başlığı"
        decimal price "Fiyat (TL)"
        string city "İl"
        string district "İlçe"
        string image_url "Görsel URL"
        string source_url "Sahibinden İlan Linki"
        json specs "Teknik Parametreler"
        boolean is_active "Aktif mi?"
    }

    USER_PREFERENCE {
        int id PK
        int user_id FK "Opsiyonel (Giriş yapılmışsa)"
        string session_key "Misafir oturumu"
        string title "Arayış Başlığı"
        int category_id FK
        decimal min_price
        decimal max_price
        string target_city
        string keywords "Anahtar Kelimeler"
        string priority "Öncelik Modu"
    }

    LISTING_INTERACTION {
        int id PK
        int user_id FK
        string session_key
        int listing_id FK
        string action_type "favorite / dismiss / clicked"
    }
```

---

## 5. Proje Dizin Yapısı

```text
bulbana/
│
├── core/                       # Django Proje Çekirdeği
│   ├── settings.py             # Supabase, WhiteNoise ve güvenlik ayarları
│   ├── urls.py                 # Kök URL yönlendiricisi
│   └── wsgi.py                 # Vercel serverless entrypoint
│
├── listings/                   # İlanlar & Akıllı Öneri Uygulaması
│   ├── models.py               # Category, Listing, UserPreference, ListingInteraction
│   ├── views.py                # Home, ListingList, Recommendations, Detail, AJAX Favorite
│   ├── forms.py                # UserPreferenceForm, QuickSearchForm
│   ├── urls.py                 # listings URL rotaları
│   ├── admin.py                # Django Admin konfigürasyonu
│   └── management/commands/
│       └── seed_data.py        # Gerçekçi Sahibinden örnek ilanları yükleme komutu
│
├── accounts/                   # Kullanıcı Yönetimi
│   ├── forms.py                # Register & Login formları
│   ├── views.py                # Kayıt, Giriş, Profil & Dashboard
│   └── urls.py                 # accounts URL rotaları
│
├── static/                     # Statik Dosyalar
│   ├── css/
│   │   └── style.css           # Özel renk paleti ve modern kart stilleri
│   └── js/
│       └── favorite.js         # Tek tıkla favorileme AJAX scripti
│
├── templates/                  # HTML Şablonları
│   ├── base.html               # Ortak Navbar, Footer, Toast ve Fontlar
│   ├── listings/
│   │   ├── home.html           # Karşılama, vitrin ve kategori kartları
│   │   ├── listing_list.html   # İlan arama ve filtreleme kataloğu
│   │   ├── listing_detail.html # Detaylı ilan sayfası & Sahibinden butonu
│   │   ├── recommendations.html# Uyum puanlı akıllı öneriler sayfası
│   │   └── create_preference.html # Arayış sihirbazı
│   └── accounts/
│       ├── login.html          # Giriş sayfası
│       ├── register.html       # Kayıt ol sayfası
│       └── profile.html        # Profil & arayış/favori yönetim paneli
│
├── vercel.json                 # Vercel Dağıtım Yapılandırması
├── build_files.sh              # Vercel statik dosya derleme scripti
├── requirements.txt            # Python Bağımlılıkları
├── .env.example                # Ortam değişkenleri şablonu
└── manage.py
```

---

## 6. Kurulum ve Çalıştırma (Lokal Geliştirme)

### 1. Depoyu Klonlayın ve Klasöre Girin:
```bash
git clone https://github.com/bisraunal/bulbana.git
cd bulbana
```

### 2. Sanal Ortamı Oluşturun ve Bağımlılıkları Yükleyin:
```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Çevre Değişkenlerini Tanımlayın (`.env`):
`.env.example` dosyasını `.env` olarak kopyalayın:
```ini
SECRET_KEY=gizli_anahtariniz
DEBUG=True
ALLOWED_HOSTS=*
# Canlı Supabase için (İsteğe bağlı):
# DATABASE_URL=postgresql://postgres.xxx:parola@aws-0-pooler.supabase.com:6543/postgres?sslmode=require
```

### 4. Veritabanını Migrate Edin ve Örnek İlanları Yükleyin:
```bash
python manage.py migrate
python manage.py seed_data
```

### 5. Sunucuyu Başlatın:
```bash
python manage.py runserver
```
Tarayıcınızdan `http://127.0.0.1:8000` adresine giderek platformu kullanabilirsiniz!

---

## 7. Canlıya Alma (Vercel & Supabase Dağıtımı)

1. **Supabase Hazırlığı:** Supabase üzerinde PostgreSQL veritabanı oluşturun ve connection string'i (Pooler - Port 6543) alın.
2. **GitHub Senkronizasyonu:** Kodları GitHub deponuza (`main` dalına) gönderin.
3. **Vercel Proje Oluşturma:** Vercel Dashboard'dan GitHub deponuzu seçin (`Import`).
4. **Environment Variables:** Vercel ayarlarında `DATABASE_URL`, `SECRET_KEY`, ve `DEBUG=False` değişkenlerini tanımlayın.
5. **Deploy:** Vercel otomatik olarak `build_files.sh` ile statik dosyaları derleyip projeyi canlıya alacaktır.
