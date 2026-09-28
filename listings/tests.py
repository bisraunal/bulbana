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


class ChatbotAndSecurityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat_emlak = Category.objects.create(name="Emlak", slug="emlak")
        self.cat_tekno = Category.objects.create(name="Teknoloji", slug="ikinci-el-teknoloji")

        self.phone = Listing.objects.create(
            category=self.cat_tekno,
            title="Apple iPhone 13 128GB",
            price=31000,
            city="İstanbul",
            district="Kadıköy",
            is_active=True
        )

        self.laptop = Listing.objects.create(
            category=self.cat_tekno,
            title="Lenovo Legion 5 Laptop",
            price=28000,
            city="İstanbul",
            district="Beşiktaş",
            is_active=True
        )

    def test_chatbot_greeting_does_not_return_random_listings(self):
        """Selam yazıldığında rastgele ilan dönmediğini, samimi sohbet döndüğünü doğrular."""
        response = self.client.post(
            reverse('chatbot_assistant_ajax'),
            data=json.dumps({'message': 'selam'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['listings']), 0)
        self.assertIn("Selam", data['reply'])

    def test_chatbot_strict_phone_search(self):
        """Telefon arandığında kesinlikle laptopları dışlayıp sadece telefon getirdiğini doğrular."""
        response = self.client.post(
            reverse('chatbot_assistant_ajax'),
            data=json.dumps({'message': 'uygun fiyatlı bir telefon arıyorum'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data['listings']), 0)
        for item in data['listings']:
            self.assertIn("iPhone", item['title'])
            self.assertNotIn("Laptop", item['title'])
            self.assertNotIn("Lenovo", item['title'])

    def test_chatbot_xss_protection(self):
        """XSS ve zararlı HTML enjeksiyonlarının temizlendiğini doğrular."""
        payload = "<script>alert('XSS')</script> Kadıköy kiralık ev"
        response = self.client.post(
            reverse('chatbot_assistant_ajax'),
            data=json.dumps({'message': payload}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("<script>", response.json()['reply'])

    def test_favorite_ajax_toggle(self):
        """Tek tıkla favorileme AJAX fonksiyonunu test eder."""
        response = self.client.post(reverse('toggle_favorite_ajax', args=[self.phone.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_favorite'])

        response2 = self.client.post(reverse('toggle_favorite_ajax', args=[self.phone.id]))
        self.assertEqual(response2.status_code, 200)
        self.assertFalse(response2.json()['is_favorite'])
