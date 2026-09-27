from django.core.management.base import BaseCommand
from listings.models import Category, Listing

class Command(BaseCommand):
    help = "Sahibinden formatında tescilli ve doğrulanmış geniş test ilanları ekler."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Kategoriler ve tescilli ilanlar güncelleniyor..."))

        # 1. Kategoriler
        cat_emlak, _ = Category.objects.get_or_create(
            slug="emlak",
            defaults={"name": "Emlak", "icon": "bi-house-door-fill", "description": "Konut, İş Yeri, Arsa, Projeler, Bina"}
        )
        cat_vasita, _ = Category.objects.get_or_create(
            slug="vasita",
            defaults={"name": "Vasıta", "icon": "bi-car-front-fill", "description": "Otomobil, Arazi, SUV & Pickup, Motosiklet"}
        )
        cat_teknoloji, _ = Category.objects.get_or_create(
            slug="ikinci-el-teknoloji",
            defaults={"name": "İkinci El ve Sıfır Alışveriş", "icon": "bi-laptop-fill", "description": "Bilgisayar, Cep Telefonu, Fotoğraf & Kamera, Ev Elektroniği"}
        )

        sample_listings = [
            # EMLAK - İSTANBUL
            {
                "category": cat_emlak,
                "title": "Kadıköy Moda'da Metroya 5 Dk Balkonlu Ferah 2+1 Kiralık Daire",
                "description": "Moda sahil ve metroya yürüme mesafesinde, geniş balkonlu, kedi ve evcil hayvan dostu, aydınlık daire. Kombili ve klimalı.",
                "price": 26000,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Moda",
                "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Oda Sayısı": "2+1", "m² (Net)": 95, "Bina Yaşı": "5-10", "Bulunduğu Kat": "3. Kat", "Isıtma": "Kombi (Doğalgaz)", "Balkon": True, "Evcil Hayvan": "Kabul Edilir"},
                "is_verified": True,
                "verification_score": 98,
                "verification_badges": ["Tapu Sicil Tescilli", "Doğrulanmış Ev Sahibi", "Piyasa Fiyatı Onaylı"],
                "market_price_diff": "Bölge Ortalamasının %8 Altında"
            },
            {
                "category": cat_emlak,
                "title": "Kadıköy Caferağa'da Sahibinden Asansörlü 3+1 Kombili Satılık",
                "description": "Kadıköy rıhtıma ve Boğa Heykeline çok yakın, nezih sokakta, çift balkonlu, ebeveyn banyolu lüks daire.",
                "price": 6450000,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Caferağa",
                "image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Oda Sayısı": "3+1", "m² (Net)": 125, "Bina Yaşı": 4, "Bulunduğu Kat": "2. Kat", "Isıtma": "Yerden Isıtma", "Balkon": True, "Asansör": True},
                "is_verified": True,
                "verification_score": 100,
                "verification_badges": ["E-Devlet Tapu Onaylı", "Ekspertiz Raporlu", "Deprem Yönetmeliğine Uygun"],
                "market_price_diff": "Piyasa Fiyatında"
            },
            {
                "category": cat_emlak,
                "title": "Beşiktaş Çarşı Merkezde Eşyalı Temiz 1+1 Kiralık",
                "description": "Üniversitelere ve vapura yakın, full eşyalı, temiz, masrafsız, hemen taşınmaya uygun merkezi 1+1 daire.",
                "price": 22500,
                "city": "İstanbul",
                "district": "Beşiktaş",
                "neighborhood": "Sinanpaşa",
                "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Oda Sayısı": "1+1", "m² (Net)": 55, "Eşyalı": True, "Isıtma": "Kombi (Doğalgaz)"},
                "is_verified": True,
                "verification_score": 96,
                "verification_badges": ["Doğrulanmış İlan", "Fatura & Adres Tescilli"],
                "market_price_diff": "Bölge Ortalamasında"
            },
            {
                "category": cat_emlak,
                "title": "İzmir Karşıyaka Bostanlı Sahile 2 Dk Balkonlu 2+1",
                "description": "Bostanlı tramvaya yakın, geniş balkonlu, önü açık, aydınlık ve masrafsız kiralık daire.",
                "price": 24000,
                "city": "İzmir",
                "district": "Karşıyaka",
                "neighborhood": "Bostanlı",
                "image_url": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Oda Sayısı": "2+1", "m² (Net)": 90, "Balkon": True, "Isıtma": "Kombi"},
                "is_verified": True,
                "verification_score": 95,
                "verification_badges": ["Tapu Tescilli", "Fiyat Güvenceli"],
                "market_price_diff": "Bölgenin %5 Altında"
            },
            {
                "category": cat_emlak,
                "title": "Ankara Çankaya Tunalı Hilmi Yakını Masrafsız 2+1 Daire",
                "description": "Kuğulu Park ve Tunalı caddesine yürüme mesafesinde, kombili, bakımlı merkezi konut.",
                "price": 19500,
                "city": "Ankara",
                "district": "Çankaya",
                "neighborhood": "Kavaklıdere",
                "image_url": "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Oda Sayısı": "2+1", "m² (Net)": 85, "Balkon": True, "Isıtma": "Merkezi"},
                "is_verified": True,
                "verification_score": 97,
                "verification_badges": ["Doğrulanmış Mülk", "Piyasa Değerleme Tescilli"],
                "market_price_diff": "Fırsat Fiyatı"
            },

            # VASITA - OTOMOBİL
            {
                "category": cat_vasita,
                "title": "Sahibinden Hatasız Boyasız 2021 Renault Clio 1.0 TCe Otomatik Touch",
                "description": "İlk sahibinden, yetkili servis bakımlı, düşük yakıt tüketimi, şehir içi kullanım için ideal otomatik vites Clio. Tramer yok.",
                "price": 745000,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Kozyatağı",
                "image_url": "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Yıl": 2021, "KM": "42.000", "Vites Tipi": "Otomatik", "Yakıt Tipi": "Benzin", "Kasa Tipi": "Hatchback", "Hasar Kaydı (Tramer)": "0 TL (Yok)"},
                "is_verified": True,
                "verification_score": 99,
                "verification_badges": ["TSE Onaylı Ekspertiz Raporlu", "Şasi/Plaka Tescilli", "Km Doğrulanmış"],
                "market_price_diff": "Piyasanın %6 Altında"
            },
            {
                "category": cat_vasita,
                "title": "Doktordan Temiz 2020 Volkswagen Polo 1.0 TSI Comfortline DSG",
                "description": "Bakımları yeni yapıldı, muayenesi tam, tramer kaydı yok, yedek anahtarı mevcut ekonomik ve serilikte 1 numara araç.",
                "price": 860000,
                "city": "Ankara",
                "district": "Çankaya",
                "neighborhood": "Kızılay",
                "image_url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Yıl": 2020, "KM": "56.000", "Vites Tipi": "Otomatik", "Yakıt Tipi": "Benzin", "Kasa Tipi": "Hatchback", "Boya/Değişen": "Hatasız"},
                "is_verified": True,
                "verification_score": 98,
                "verification_badges": ["Ekspertiz Tescilli", "Tramer Kaydı Temiz", "Muayenesi Tam"],
                "market_price_diff": "Piyasa Değerinde"
            },
            {
                "category": cat_vasita,
                "title": "2022 Fiat Egea 1.3 Multijet Easy Manuel Dizel Masrafsız",
                "description": "Şirket geçmişi olmayan, aile aracı olarak kullanılmış, düşük yakıtlı, parça sıkıntısı olmayan tertemiz Egea.",
                "price": 630000,
                "city": "İzmir",
                "district": "Bornova",
                "neighborhood": "Evka 3",
                "image_url": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Yıl": 2022, "KM": "68.000", "Vites Tipi": "Manuel", "Yakıt Tipi": "Dizel", "Kasa Tipi": "Sedan"},
                "is_verified": True,
                "verification_score": 94,
                "verification_badges": ["Ruhsat Tescilli", "Servis Bakım Kayıtlı"],
                "market_price_diff": "Piyasanın %7 Altında"
            },

            # TEKNOLOJİ & İKİNCİ EL
            {
                "category": cat_teknoloji,
                "title": "Apple MacBook Air M2 16GB RAM 512GB SSD Uzay Grisi Kusursuz",
                "description": "Yazılımcıdan temiz kullanılmış, pil sağlığı %94, kutusu ve faturası mevcut, çiziksiz garantili M2.",
                "price": 36500,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Caddebostan",
                "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"İşlemci": "Apple M2", "RAM": "16 GB", "SSD Kapasitesi": "512 GB", "Pil Sağlığı": "%94", "Garanti": "Devam Ediyor (6 Ay)"},
                "is_verified": True,
                "verification_score": 99,
                "verification_badges": ["Fatura Tescilli", "Seri No / Apple Doğrulanmış", "Param Güvende Onaylı"],
                "market_price_diff": "Sıfır Fiyatına Göre %35 Tasarruf"
            },
            {
                "category": cat_teknoloji,
                "title": "Lenovo Legion 5 Gaming Laptop RTX 3060 Ryzen 7 16GB RAM",
                "description": "Oyun ve 3D render için harika performans. 144Hz IPS ekran, termal bakımları yetkili serviste yeni yapıldı.",
                "price": 28500,
                "city": "İstanbul",
                "district": "Beşiktaş",
                "neighborhood": "Levent",
                "image_url": "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Ekran Kartı": "NVIDIA RTX 3060", "İşlemci": "AMD Ryzen 7 5800H", "RAM": "16 GB", "SSD": "1 TB NVMe", "Ekran": "15.6 inç 144Hz"},
                "is_verified": True,
                "verification_score": 96,
                "verification_badges": ["Fatura & Kutu Mevcut", "Donanım Test Raporlu"],
                "market_price_diff": "Piyasanın %14 Altında"
            },
            {
                "category": cat_teknoloji,
                "title": "Apple iPhone 14 Pro 128GB Derin Mor Pil %89 Hatasız",
                "description": "Kılıf ve kırılmaz camla kullanıldı, darbe çizik yok. Türkiye cihazı, faturası ve kutusuyla teslim.",
                "price": 49000,
                "city": "Ankara",
                "district": "Çankaya",
                "neighborhood": "Bahçelievler",
                "image_url": "https://images.unsplash.com/photo-1678685888221-cda773a3dcdb?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"Model": "iPhone 14 Pro", "Hafıza": "128 GB", "Pil Sağlığı": "%89", "Kayıt": "BTK Türkiye Kayıtlı"},
                "is_verified": True,
                "verification_score": 99,
                "verification_badges": ["IMEI / BTK Tescilli", "Apple Faturası Doğrulandı"],
                "market_price_diff": "Piyasa Değerinde"
            }
        ]

        for item in sample_listings:
            Listing.objects.update_or_create(
                title=item["title"],
                defaults=item
            )

        self.stdout.write(self.style.SUCCESS(f"Tebrikler! {len(sample_listings)} tescilli ve zengin ilan başarıyla güncellendi."))
