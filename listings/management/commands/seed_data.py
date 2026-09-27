from django.core.management.base import BaseCommand
from listings.models import Category, Listing

class Command(BaseCommand):
    help = "Sahibinden formatında gerçekçi test ilanları ve kategorileri ekler."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Kategoriler ve örnek ilanlar oluşturuluyor..."))

        # 1. Kategoriler
        cat_emlak, _ = Category.objects.get_or_create(
            slug="emlak",
            defaults={"name": "Emlak (Konut & Daire)", "icon": "bi-house-door-fill", "description": "Kiralık ve satılık daireler, villalar ve işyerleri."}
        )
        cat_vasita, _ = Category.objects.get_or_create(
            slug="vasita",
            defaults={"name": "Vasıta (Otomobil & Araç)", "icon": "bi-car-front-fill", "description": "Sıfır ve 2. el otomobiller, SUV ve motosikletler."}
        )
        cat_teknoloji, _ = Category.objects.get_or_create(
            slug="ikinci-el-teknoloji",
            defaults={"name": "İkinci El & Teknoloji", "icon": "bi-laptop-fill", "description": "Bilgisayarlar, telefonlar, monitörler ve çevre birimleri."}
        )

        sample_listings = [
            # EMLAK İLANLARI
            {
                "category": cat_emlak,
                "title": "Kadıköy Moda'da Metroya 5 Dk Balkonlu Ferah 2+1 Kiralık",
                "description": "Moda sahil ve metroya yürüme mesafesinde, geniş balkonlu, kedi ve evcil hayvan dostu, aydınlık daire. Kombili ve klimalı.",
                "price": 26000,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Moda",
                "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"oda_sayisi": "2+1", "bina_yasi": 8, "balkon": True, "pet_friendly": True, "isinma": "Kombi", "metrekare": 95}
            },
            {
                "category": cat_emlak,
                "title": "Beşiktaş Çarşı Merkezde Eşyalı Temiz 1+1 Daire",
                "description": "Üniversitelere ve vapura yakın, full eşyalı, temiz, masrafsız, hemen taşınmaya uygun merkezi 1+1.",
                "price": 22500,
                "city": "İstanbul",
                "district": "Beşiktaş",
                "neighborhood": "Sinanpaşa",
                "image_url": "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"oda_sayisi": "1+1", "esyali": True, "bina_yasi": 12, "metrekare": 60, "isinma": "Kombi"}
            },
            {
                "category": cat_emlak,
                "title": "Kadıköy Feneryolu Marmaray Yanı Site İçi Otoparklı 3+1",
                "description": "Marmaray ve Bağdat Caddesi yakını, kapalı otoparklı, asansörlü, ebeveyn banyolu lüks geniş daire.",
                "price": 42000,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Feneryolu",
                "image_url": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"oda_sayisi": "3+1", "otopark": True, "asansor": True, "metrekare": 135}
            },
            {
                "category": cat_emlak,
                "title": "İzmir Karşıyaka Bostanlı Sahile Yakın Balkonlu 2+1",
                "description": "Bostanlı tramvay durağına 3 dk, ferah çift cephe, geniş balkon, nezih muhitte kiralık.",
                "price": 24000,
                "city": "İzmir",
                "district": "Karşıyaka",
                "neighborhood": "Bostanlı",
                "image_url": "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"oda_sayisi": "2+1", "balkon": True, "metrekare": 90}
            },

            # VASITA İLANLARI
            {
                "category": cat_vasita,
                "title": "Sahibinden Hatasız Boyasız 2021 Clio 1.0 TCe Otomatik",
                "description": "İlk sahibinden, yetkili servis bakımlı, düşük yakıt tüketimi, şehir içi kullanım için ideal otomatik vites Clio.",
                "price": 745000,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Kozyatağı",
                "image_url": "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"yil": 2021, "km": 42000, "vites": "Otomatik", "yakit": "Benzin", "kasa": "Hatchback", "hasar_kaydi": "Yok"}
            },
            {
                "category": cat_vasita,
                "title": "Doktordan Temiz 2019 Polo 1.6 TDI Dizel Otomatik DSG",
                "description": "Bakımları yeni yapıldı, muayenesi tam, tramer kaydı yok, yedek anahtarı mevcut ekonomik araç.",
                "price": 820000,
                "city": "Ankara",
                "district": "Çankaya",
                "neighborhood": "Kızılay",
                "image_url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"yil": 2019, "km": 78000, "vites": "Otomatik", "yakit": "Dizel", "kasa": "Hatchback"}
            },
            {
                "category": cat_vasita,
                "title": "2020 Fiat Egea 1.4 Fire Manuel Masrafsız Aile Aracı",
                "description": "LPG uyumlu, az yakar, çok kaçar. Parçası ucuz, aileye ve ilk araca son derece uygun.",
                "price": 590000,
                "city": "İzmir",
                "district": "Bornova",
                "neighborhood": "Evka 3",
                "image_url": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"yil": 2020, "km": 65000, "vites": "Manuel", "yakit": "Benzin/LPG", "kasa": "Sedan"}
            },

            # TEKNOLOJİ İLANLARI
            {
                "category": cat_teknoloji,
                "title": "Apple MacBook Air M2 16GB RAM 512GB SSD Uzay Grisi",
                "description": "Yazılımcıdan temiz kullanılmış, pil sağlığı %94, kutusu ve faturası mevcut, çiziksiz garantili M2.",
                "price": 36500,
                "city": "İstanbul",
                "district": "Kadıköy",
                "neighborhood": "Caddebostan",
                "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"ram": "16GB", "islemci": "Apple M2", "depolama": "512GB SSD", "pil": "%94", "durum": "Kusursuz"}
            },
            {
                "category": cat_teknoloji,
                "title": "Lenovo Legion 5 Gaming Laptop RTX 3060 Ryzen 7 16GB",
                "description": "Oyun ve 3D tasarım için harika performans. 144Hz IPS ekran, termal bakımları yeni yapıldı.",
                "price": 28000,
                "city": "İstanbul",
                "district": "Beşiktaş",
                "neighborhood": "Levent",
                "image_url": "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"ekran_karti": "RTX 3060", "ram": "16GB", "islemci": "Ryzen 7", "depolama": "1TB SSD"}
            },
            {
                "category": cat_teknoloji,
                "title": "Dell 27 inç 2K QHD 165Hz IPS Pivot Oyuncu & Kod Monitörü",
                "description": "Pivot ayaklı dikey çevrilebilir, sıfır ölü piksel, HDR destekli profesyonel monitör.",
                "price": 8500,
                "city": "Ankara",
                "district": "Çankaya",
                "neighborhood": "Balgat",
                "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=800&auto=format&fit=crop&q=80",
                "source_url": "https://www.sahibinden.com",
                "specs": {"boyut": "27 inç", "cozunurluk": "2K QHD", "panel": "IPS", "yenileme": "165Hz"}
            }
        ]

        for item in sample_listings:
            Listing.objects.get_or_create(
                title=item["title"],
                defaults=item
            )

        self.stdout.write(self.style.SUCCESS(f"Tebrikler! {len(sample_listings)} örnek ilan ve kategoriler başarıyla eklendi."))
