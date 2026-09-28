import json
import urllib.parse
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Category, Listing, UserPreference, ListingInteraction

class ListingModelTests(TestCase):
    def setUp(self):
        self.category_emlak = Category.objects.create(name="Emlak", slug="emlak")
        self.category_tekno = Category.objects.create(name="Teknoloji", slug="ikinci-el-teknoloji")
        
        self.listing_ev = Listing.objects.create(
            category=self.category_emlak,
            title="Kadıköy Moda 2+1 Kiralık",
            description="Balkonlu kombili ferah daire",
            price=25000,
            city="İstanbul",
            district="Kadıköy",
            neighborhood="Moda",
            specs={"Oda Sayısı": "2+1", "Balkon": True},
            is_verified=True,
            verification_score=98,
            verification_badges=["Tapu Tescilli"]
        )

        self.listing_phone = Listing.objects.create(
            category=self.category_tekno,
            title="Apple iPhone 14 Pro 128GB",
            description="Kutulu faturalı temiz telefon",
            price=48000,
            city="İstanbul",
            district="Kadıköy",
            specs={"Ürün Türü": "Cep Telefonu"},
            is_verified=True
        )

        self.listing_laptop = Listing.objects.create(
            category=self.category_tekno,
            title="Apple MacBook Air M2 16GB",
            description="Kusursuz dizüstü bilgisayar",
            price=36000,
            city="İstanbul",
            district="Kadıköy",
            specs={"Ürün Türü": "Dizüstü Bilgisayar"}
        )

    def test_sahibinden_link_generator(self):
        """Dinamik sahibinden_link özelliğinin düzgün çalıştığını doğrular."""
        link = self.listing_ev.sahibinden_link
        decoded_link = urllib.parse.unquote(link)
        self.assertIn("sahibinden.com", decoded_link)
        self.assertIn("Kadıköy", decoded_link)

    def test_matching_algorithm(self):
        """Arayış kriterleri ile ilan eşleştirme skorunu test eder."""
        pref = UserPreference.objects.create(
            title="Kadıköy Ev Arayışım",
            category=self.category_emlak,
            min_price=20000,
            max_price=30000,
            target_city="İstanbul",
            target_district="Kadıköy",
            keywords="balkon"
        )
        score, reasons, notes = pref.calculate_match(self.listing_ev)
        self.assertGreaterEqual(score, 80)
        self.assertTrue(any("bütçe" in r.lower() or "bütçenize" in r.lower() for r in reasons))
        self.assertTrue(any("konum" in r.lower() or "kadıköy" in r.lower() for r in reasons))


class PrecisionAndStrictIsolationTests(TestCase):
    """
    Şehir ve Kategori İzolasyonu Testleri:
    - Araba arandığında ev/telefon ASLA çıkmamalı.
    - Ankara seçildiğinde İstanbul ASLA çıkmamalı.
    """
    def setUp(self):
        self.client = Client()
        self.cat_emlak = Category.objects.create(name="Emlak", slug="emlak")
        self.cat_vasita = Category.objects.create(name="Vasıta", slug="vasita")
        self.cat_tekno = Category.objects.create(name="Teknoloji", slug="ikinci-el-teknoloji")

        # İstanbul İlanları
        self.istanbul_ev = Listing.objects.create(
            category=self.cat_emlak,
            title="Kadıköy Moda Kiralık Daire",
            price=26000,
            city="İstanbul",
            district="Kadıköy",
            is_active=True
        )
        self.istanbul_araba = Listing.objects.create(
            category=self.cat_vasita,
            title="Renault Clio Otomatik",
            price=750000,
            city="İstanbul",
            district="Kadıköy",
            is_active=True
        )
        self.istanbul_telefon = Listing.objects.create(
            category=self.cat_tekno,
            title="iPhone 13 128GB",
            price=31000,
            city="İstanbul",
            district="Kadıköy",
            specs={"Ürün Türü": "Cep Telefonu"},
            is_active=True
        )

        # Ankara İlanları
        self.ankara_ev = Listing.objects.create(
            category=self.cat_emlak,
            title="Çankaya Tunalı Kiralık Daire",
            price=20000,
            city="Ankara",
            district="Çankaya",
            is_active=True
        )
        self.ankara_araba = Listing.objects.create(
            category=self.cat_vasita,
            title="Volkswagen Polo DSG",
            price=850000,
            city="Ankara",
            district="Çankaya",
            is_active=True
        )

    def test_car_search_only_returns_vehicles(self):
        """Araba arandığında SADECE vasıtaların geldiğini, ev ve telefonun kesinlikle çıkmadığını test eder."""
        response = self.client.post(
            reverse('chatbot_assistant_ajax'),
            data=json.dumps({'message': 'araba arıyorum otomatik vites'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data['listings']), 0)
        
        for item in data['listings']:
            # Başlıkta araba modelleri olmalı, ev veya telefon asla olmamalı
            title = item['title'].lower()
            self.assertTrue(any(car in title for car in ['clio', 'polo', 'renault', 'volkswagen', 'araba']))
            self.assertNotIn("kiralık", title)
            self.assertNotIn("daire", title)
            self.assertNotIn("iphone", title)

    def test_ankara_search_never_returns_istanbul(self):
        """Ankara belirtildiğinde KESİNLİKLE İstanbul'un çıkmadığını test eder."""
        response = self.client.post(
            reverse('chatbot_assistant_ajax'),
            data=json.dumps({'message': 'Ankara Çankaya kiralık ev'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data['listings']), 0)

        for item in data['listings']:
            self.assertIn("Ankara", item['location'])
            self.assertNotIn("İstanbul", item['location'])
            self.assertNotIn("Kadıköy", item['location'])

    def test_combined_city_and_product_precision(self):
        """'Ankara'da araba' sorgusunda sadece Ankara'daki araçların geldiğini test eder."""
        response = self.client.post(
            reverse('chatbot_assistant_ajax'),
            data=json.dumps({'message': 'Ankara da satılık araba'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data['listings']), 0)

        for item in data['listings']:
            self.assertIn("Ankara", item['location'])
            self.assertIn("Polo", item['title'])
            self.assertNotIn("Clio", item['title']) # Clio İstanbul'da, çıkmamalı!

    def test_xss_protection(self):
        """XSS ve zararlı HTML enjeksiyonlarının temizlendiğini doğrular."""
        payload = "<script>alert('XSS')</script> Kadıköy kiralık ev"
        response = self.client.post(
            reverse('chatbot_assistant_ajax'),
            data=json.dumps({'message': payload}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script>", response.json()['reply'])

    def test_greeting_behavior(self):
        """Selam yazıldığında rastgele ilan dönmediğini, karşılama mesajı döndüğünü test eder."""
        response = self.client.post(
            reverse('chatbot_assistant_ajax'),
            data=json.dumps({'message': 'selam'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['listings']), 0)
        self.assertIn("Selam", data['reply'])
