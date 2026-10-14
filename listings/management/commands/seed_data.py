from django.core.management.base import BaseCommand
from listings.models import UserProfile, SearchTarget, ScrapedListing


class Command(BaseCommand):
    help = "BulBana için örnek kullanıcı, arama hedefleri ve eşleşen ilan verileri oluşturur."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Örnek BulBana verileri oluşturuluyor..."))

        user, _ = UserProfile.objects.get_or_create(
            username="demo_user",
            defaults={"telegram_chat_id": "123456789"}
        )

        target1, _ = SearchTarget.objects.get_or_create(
            user=user,
            title="Kırmızı Hatasız Clio 2020+",
            defaults={
                "category": "vasita",
                "city": "İstanbul",
                "town": "Kadıköy",
                "min_price": 500000,
                "max_price": 750000,
                "search_url": "https://www.sahibinden.com/kelime-ile-arama?query_text=Renault+Clio+K%C4%B1rm%C4%B1z%C4%B1",
                "filter_criteria": {
                    "brand": "Renault",
                    "model": "Clio",
                    "color": "Kırmızı",
                    "year_min": "2020",
                    "transmission": "Otomatik",
                    "fuel": "Benzin",
                    "damage_status": "Ağır Hasarsız"
                },
                "keywords": "kırmızı, hatasız",
                "negative_keywords": "ağır hasar, pert, taksi",
                "is_active": True
            }
        )

        target2, _ = SearchTarget.objects.get_or_create(
            user=user,
            title="Kadıköy 2+1 Balkonlu Kiralık Daire",
            defaults={
                "category": "emlak",
                "city": "İstanbul",
                "town": "Kadıköy",
                "min_price": 25000,
                "max_price": 40000,
                "search_url": "https://www.sahibinden.com/kelime-ile-arama?query_text=%C4%B0stanbul+Kad%C4%B1k%C3%B6y+2%2B1+kiralik+daire",
                "filter_criteria": {
                    "type": "Kiralık Daire",
                    "room_count": "2+1",
                    "m2_min": "85",
                    "balcony": True
                },
                "keywords": "balkonlu, aydınlık",
                "negative_keywords": "bodrum, kot",
                "is_active": True
            }
        )

        ScrapedListing.objects.get_or_create(
            target=target1,
            external_id="sahibinden-demo-101",
            defaults={
                "title": "Sahibinden 2021 Model Kırmızı Hatasız Boyasız Renault Clio Otomatik",
                "price": "635.000 TL",
                "location": "İstanbul / Kadıköy",
                "published_date": "Bugün 13:45",
                "image_url": "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=600&q=80",
                "listing_url": "https://www.sahibinden.com/kelime-ile-arama?query_text=Renault+Clio+K%C4%B1rm%C4%B1z%C4%B1",
                "is_notified": True
            }
        )

        ScrapedListing.objects.get_or_create(
            target=target2,
            external_id="sahibinden-demo-102",
            defaults={
                "title": "Kadıköy Moda Merkezde Balkonlu Kombili Ferah 2+1 Kiralık Daire",
                "price": "32.000 TL",
                "location": "İstanbul / Kadıköy",
                "published_date": "Bugün 14:10",
                "image_url": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=600&q=80",
                "listing_url": "https://www.sahibinden.com/kelime-ile-arama?query_text=%C4%B0stanbul+Kad%C4%B1k%C3%B6y+2%2B1+kiralik+daire",
                "is_notified": True
            }
        )

        self.stdout.write(self.style.SUCCESS("[OK] Örnek veriler başarıyla yüklendi! demo_user kullanıcısı ile giriş yapabilirsiniz."))
