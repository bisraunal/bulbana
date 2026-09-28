from django.core.management.base import BaseCommand
from listings.models import Category, Listing

class Command(BaseCommand):
    help = "Sahibinden formatında zengin, tescilli ve doğrudan çalışan Sahibinden arama/model linkleri ekler."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Kategoriler ve doğrudan çalışan Sahibinden linkleri güncelleniyor..."))

        cat_emlak, _ = Category.objects.get_or_create(
            slug="emlak",
            defaults={"name": "Emlak", "icon": "bi-house-door-fill", "description": "Konut, İş Yeri, Arsa"}
        )
        cat_vasita, _ = Category.objects.get_or_create(
            slug="vasita",
            defaults={"name": "Vasıta", "icon": "bi-car-front-fill", "description": "Otomobil, SUV, Motosiklet"}
        )
        cat_teknoloji, _ = Category.objects.get_or_create(
            slug="ikinci-el-teknoloji",
            defaults={"name": "İkinci El ve Sıfır Alışveriş", "icon": "bi-laptop-fill", "description": "Bilgisayar, Cep Telefonu, Elektronik"}
        )

        sample_listings = [
            # 📱 TELEFON İLANLARI
            {
                "category": cat_teknoloji,
                "title": "Apple iPhone 14 Pro 128GB Derin Mor Pil %89 Hatasız",
                "description": "Kılıf ve kırılmaz camla kullanıldı, darbe çizik yok. Türkiye cihazı, faturası ve kutusuyla teslim.",
                "price": 49000,
                "city": "Ankara",
                "district": "Çankaya",
                "neighborhood": "Bahçelievler",
                "image_url": "https://images.unsplash.com/photo-1678685888221-cda773a3dcdb?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=iPhone+14+Pro+128GB",
                "specs": {"Ürün Türü": "Cep Telefonu", "Marka": "Apple", "Model": "iPhone 14 Pro", "Hafıza": "128 GB", "Pil": "%89", "Kayıt": "BTK Türkiye Kayıtlı"},
                "is_verified": True,
                "verification_score": 99,
                "verification_badges": ["IMEI / BTK Tescilli", "Apple Faturası Doğrulandı"],
                "market_price_diff": "Piyasa Değerinde"
            },
            {
                "category": cat_teknoloji,
                "title": "Apple iPhone 13 128GB Gece Yarısı Siyahı Kutulu Faturalı",
                "description": "İlk sahibinden, pil sağlığı %86, Face ID ve tüm fonksiyonlar kusursuz. Uygun fiyatlı temiz telefon.",
                "price": 31500,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Moda",
                "image_url": "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=iPhone+13+128GB",
                "specs": {"Ürün Türü": "Cep Telefonu", "Marka": "Apple", "Model": "iPhone 13", "Hafıza": "128 GB", "Pil": "%86"},
                "is_verified": True,
                "verification_score": 97,
                "verification_badges": ["IMEI Tescilli", "Fatura Doğrulandı", "Param Güvende"],
                "market_price_diff": "Piyasanın %10 Altında"
            },
            {
                "category": cat_teknoloji,
                "title": "Samsung Galaxy S23 256GB Krem Renk 1 Yıl Garantili",
                "description": "Snapdragon 8 Gen 2 işlemcili, ekranında çizik dahi yok, kutusu şarj kablosu faturası tam.",
                "price": 24500,
                "city": "İzmir",
                "district": "Karşıyaka",
                "neighborhood": "Bostanlı",
                "image_url": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=Samsung+Galaxy+S23+256GB",
                "specs": {"Ürün Türü": "Cep Telefonu", "Marka": "Samsung", "Model": "Galaxy S23", "Hafıza": "256 GB", "RAM": "8 GB"},
                "is_verified": True,
                "verification_score": 98,
                "verification_badges": ["Samsung Türkiye Garantili", "Fatura Tescilli"],
                "market_price_diff": "Bütçe Dostu Fırsat"
            },
            {
                "category": cat_teknoloji,
                "title": "Xiaomi Redmi Note 12 Pro 8GB RAM 256GB Hafıza",
                "description": "Öğrenciye ve bütçe dostu arayanlara ideal, 120Hz AMOLED ekran, 67W hızlı şarj aleti yanında.",
                "price": 9500,
                "city": "İstanbul",
                "district": "Beşiktaş",
                "neighborhood": "Çarşı",
                "image_url": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=Xiaomi+Redmi+Note+12+Pro",
                "specs": {"Ürün Türü": "Cep Telefonu", "Marka": "Xiaomi", "Model": "Redmi Note 12 Pro", "Hafıza": "256 GB", "Fiyat": "Ekonomik"},
                "is_verified": True,
                "verification_score": 95,
                "verification_badges": ["Doğrulanmış İlan", "Param Güvende"],
                "market_price_diff": "Piyasanın %15 Altında"
            },

            # 💻 BİLGİSAYAR & LAPTOP İLANLARI
            {
                "category": cat_teknoloji,
                "title": "Apple MacBook Air M2 16GB RAM 512GB SSD Uzay Grisi Kusursuz",
                "description": "Yazılımcıdan temiz kullanılmış, pil sağlığı %94, kutusu ve faturası mevcut, çiziksiz garantili M2.",
                "price": 36500,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Caddebostan",
                "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=MacBook+Air+M2+16GB",
                "specs": {"Ürün Türü": "Dizüstü Bilgisayar (Laptop)", "Marka": "Apple", "Model": "MacBook Air M2", "RAM": "16 GB", "SSD": "512 GB"},
                "is_verified": True,
                "verification_score": 99,
                "verification_badges": ["Fatura Tescilli", "Seri No Doğrulanmış"],
                "market_price_diff": "Piyasanın %12 Altında"
            },
            {
                "category": cat_teknoloji,
                "title": "Lenovo Legion 5 Gaming Laptop RTX 3060 Ryzen 7 16GB RAM",
                "description": "Oyun ve 3D render için harika performans. 144Hz IPS ekran, termal bakımları yeni yapıldı.",
                "price": 28500,
                "city": "İstanbul",
                "district": "Beşiktaş",
                "neighborhood": "Levent",
                "image_url": "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=Lenovo+Legion+5+RTX+3060",
                "specs": {"Ürün Türü": "Dizüstü Bilgisayar (Laptop)", "Marka": "Lenovo", "Ekran Kartı": "RTX 3060", "RAM": "16 GB"},
                "is_verified": True,
                "verification_score": 96,
                "verification_badges": ["Donanım Test Raporlu", "Fatura Mevcut"],
                "market_price_diff": "Piyasanın %14 Altında"
            },

            # 🏠 EMLAK İLANLARI
            {
                "category": cat_emlak,
                "title": "Kadıköy Moda'da Metroya 5 Dk Balkonlu Ferah 2+1 Kiralık Daire",
                "description": "Moda sahil ve metroya yürüme mesafesinde, geniş balkonlu, kedi ve evcil hayvan dostu, aydınlık daire.",
                "price": 26000,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Moda",
                "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=Kadikoy+Moda+Kiralik+Daire+2%2B1",
                "specs": {"Ürün Türü": "Kiralık Daire", "Oda Sayısı": "2+1", "m² (Net)": 95, "Balkon": True, "Isıtma": "Kombi"},
                "is_verified": True,
                "verification_score": 98,
                "verification_badges": ["Tapu Sicil Tescilli", "Piyasa Fiyatı Onaylı"],
                "market_price_diff": "Bölgenin %8 Altında"
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
                "source_url": "https://www.sahibinden.com/arama?query_text=Besiktas+Carsi+Kiralik+Daire+1%2B1",
                "specs": {"Ürün Türü": "Kiralık Daire", "Oda Sayısı": "1+1", "m² (Net)": 55, "Eşyalı": True},
                "is_verified": True,
                "verification_score": 96,
                "verification_badges": ["Doğrulanmış İlan", "Adres Tescilli"],
                "market_price_diff": "Bölge Ortalamasında"
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
                "source_url": "https://www.sahibinden.com/arama?query_text=Ankara+Cankaya+Tunali+Kiralik+Daire",
                "specs": {"Ürün Türü": "Kiralık Daire", "Oda Sayısı": "2+1", "m² (Net)": 85, "Balkon": True},
                "is_verified": True,
                "verification_score": 97,
                "verification_badges": ["Doğrulanmış Mülk", "Fiyat Güvenceli"],
                "market_price_diff": "Fırsat Fiyatı"
            },

            # 🚗 VASITA İLANLARI
            {
                "category": cat_vasita,
                "title": "Sahibinden Hatasız Boyasız 2021 Renault Clio 1.0 TCe Otomatik Touch",
                "description": "İlk sahibinden, yetkili servis bakımlı, düşük yakıt tüketimi, şehir içi kullanım için ideal otomatik vites Clio.",
                "price": 745000,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Kozyatağı",
                "image_url": "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=Renault+Clio+1.0+TCe+Otomatik",
                "specs": {"Ürün Türü": "Otomobil", "Marka": "Renault", "Model": "Clio", "Yıl": 2021, "KM": "42.000", "Vites": "Otomatik", "Yakıt": "Benzin"},
                "is_verified": True,
                "verification_score": 99,
                "verification_badges": ["TSE Onaylı Ekspertiz", "Şasi Tescilli"],
                "market_price_diff": "Piyasanın %6 Altında"
            },
            {
                "category": cat_vasita,
                "title": "Doktordan Temiz 2020 Volkswagen Polo 1.0 TSI Comfortline DSG",
                "description": "Bakımları yeni yapıldı, muayenesi tam, tramer kaydı yok, yedek anahtarı mevcut ekonomik araç.",
                "price": 860000,
                "city": "Ankara",
                "district": "Çankaya",
                "neighborhood": "Kızılay",
                "image_url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=Volkswagen+Polo+1.0+TSI+DSG",
                "specs": {"Ürün Türü": "Otomobil", "Marka": "Volkswagen", "Model": "Polo", "Yıl": 2020, "KM": "56.000", "Vites": "Otomatik"},
                "is_verified": True,
                "verification_score": 98,
                "verification_badges": ["Ekspertiz Tescilli", "Km Doğrulandı"],
                "market_price_diff": "Piyasa Değerinde"
            },
            {
                "category": cat_vasita,
                "title": "2022 Fiat Egea 1.3 Multijet Easy Manuel Dizel Masrafsız",
                "description": "Şirket geçmişi olmayan, aile aracı olarak kullanılmış, düşük yakıtlı masrafsız Egea.",
                "price": 630000,
                "city": "İzmir",
                "district": "Bornova",
                "neighborhood": "Evka 3",
                "image_url": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com/arama?query_text=Fiat+Egea+1.3+Multijet+Easy",
                "specs": {"Ürün Türü": "Otomobil", "Marka": "Fiat", "Model": "Egea", "Yıl": 2022, "KM": "68.000", "Vites": "Manuel", "Yakıt": "Dizel"},
                "is_verified": True,
                "verification_score": 94,
                "verification_badges": ["Ruhsat Tescilli", "Servis Kayıtlı"],
                "market_price_diff": "Piyasanın %7 Altında"
            }
        ]

        for item in sample_listings:
            Listing.objects.update_or_create(
                title=item["title"],
                defaults=item
            )

        self.stdout.write(self.style.SUCCESS(f"Tebrikler! {len(sample_listings)} ilan doğrudan çalışan Sahibinden arama adresleriyle güncellendi."))
