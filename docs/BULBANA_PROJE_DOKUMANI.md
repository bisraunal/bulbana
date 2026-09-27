# 🔍 BulBana — Kapsamlı Proje Dokümantasyonu & Mimari Planı

---

## 1. Proje Genel Bakışı & Amacı
**BulBana**, Sahibinden platformundaki binlerce ilan arasında tek tek kaybolmak yerine; kullanıcının bütçesine, istediği lokasyona, önceliklerine ve olmazsa olmaz kriterlerine göre Sahibinden ilanlarını tarayan ve kullanıcıya **"Uyum Skoru" (%0 - %100)** ile en uygun ilanları öneren akıllı bir eşleştirme platformudur.

---

## 2. Mimari ve Eşleştirme Motoru
* **Fiyat Puanı (%40):** Bütçe içi veya bütçe altı tam puan, bütçe aşımında orantılı ceza katsayısı.
* **Lokasyon Puanı (%30):** Hedef şehir ve ilçe birebir uyumu.
* **Özellik & Anahtar Kelime Taraması (%20):** İlan başlığı, açıklaması ve JSON formatındaki teknik donanım alanlarının aranması.
* **Öncelik Çarpanı (%10):** Kullanıcı bütçe veya konum öncelikli seçtiğinde ilgili puanların ağırlığının artırılması.

---

## 3. Veritabanı ve Deployment
* **Backend:** Python 3.11+, Django 5.x / 6.x
* **Veritabanı:** Supabase (Barındırılan PostgreSQL) & Yerel SQLite
* **Frontend:** Django Templates, Vanilla HTML5, Bootstrap 5, Modern Custom CSS, Vanilla JavaScript (Fetch API)
* **Dağıtım (Deployment):** Vercel Serverless WSGI Handler
