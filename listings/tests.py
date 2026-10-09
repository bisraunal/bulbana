import json
from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from .models import UserProfile, SearchTarget, ScrapedListing
from .services.filter_service import match_listing
from .views import (
    login_view, profile_view, add_target_view, toggle_target_view,
    api_targets_view, api_listings_view, api_cron_scan_view
)


class BulBanaCoreTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserProfile.objects.create(username="testuser", telegram_chat_id="12345678")
        self.target = SearchTarget.objects.create(
            user=self.user,
            title="Kirmizi Hasarsiz Clio",
            category="vasita",
            city="İstanbul",
            town="Kadıköy",
            search_url="https://www.sahibinden.com/otomobil-renault-clio",
            min_price=400000,
            max_price=750000,
            filter_criteria={
                "brand": "Renault",
                "model": "Clio",
                "color": "Kırmızı",
                "year_min": 2018,
                "year_max": 2023,
                "damage_status": "Ağır Hasarsız"
            },
            keywords="kırmızı, hatasız",
            negative_keywords="ağır hasar, pert, taksi"
        )

    def _add_middleware(self, request):
        """Request icin session ve messages middleware'lerini ekler."""
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)

    def test_filter_service_comprehensive_matching(self):
        good_listing = {
            'title': 'Sahibinden 2020 Model Temiz Kırmızı Hatasız Clio Touch',
            'location': 'İstanbul / Kadıköy',
            'price': '620.000 TL'
        }
        matched, reason = match_listing(good_listing, self.target)
        self.assertTrue(matched)

        bad_damage_listing = {
            'title': '2020 Kırmızı Clio Ağır Hasar Kayıtlı Masrafsız',
            'location': 'İstanbul / Kadıköy',
            'price': '500.000 TL'
        }
        matched, reason = match_listing(bad_damage_listing, self.target)
        self.assertFalse(matched)

    def test_login_flow(self):
        request = self.factory.post('/login/', {
            'username': 'ahmet',
            'telegram_chat_id': '987654'
        })
        self._add_middleware(request)
        response = login_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserProfile.objects.filter(username='ahmet').exists())

    def test_api_targets_endpoint(self):
        request = self.factory.get(f'/api/targets/?username={self.user.username}')
        response = api_targets_view(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('targets', data)
        self.assertEqual(len(data['targets']), 1)

    def test_api_cron_scan_endpoint(self):
        # Yetkisiz erisim testi
        request = self.factory.get('/api/cron/scan/?secret=wrong-secret')
        response = api_cron_scan_view(request)
        self.assertEqual(response.status_code, 403)

        # Gecerli anahtar testi
        request = self.factory.get('/api/cron/scan/?secret=bulbana-cron-secret-key-2026')
        response = api_cron_scan_view(request)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'success')

    def test_profile_update_flow(self):
        user = UserProfile.objects.create(username="burak", telegram_chat_id=None)
        request = self.factory.post('/profile/', {
            'telegram_chat_id': '555123456',
            'send_test': '0'
        })
        self._add_middleware(request)
        request.session['user_id'] = user.id
        request.session['username'] = user.username

        response = profile_view(request)
        self.assertEqual(response.status_code, 302)

        user.refresh_from_db()
        self.assertEqual(user.telegram_chat_id, '555123456')
