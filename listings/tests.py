from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from .models import UserProfile, SearchTarget, ScrapedListing
from .services.filter_service import match_listing, extract_number_from_price
from .views import login_view, add_target_view, dashboard_view, toggle_target_view


class BulBanaCoreTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = UserProfile.objects.create(username="testuser", telegram_chat_id="12345678")
        self.target = SearchTarget.objects.create(
            user=self.user,
            title="Kirmizi Hasarsiz Clio",
            category="vasita",
            search_url="https://www.sahibinden.com/otomobil-renault-clio",
            min_price=400000,
            max_price=750000,
            keywords="kirmizi, hatasiz",
            negative_keywords="agir hasar, pert, taksi"
        )

    def _add_middleware(self, request):
        """Request icin session ve messages middleware'lerini ekler."""
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)

    def test_filter_service_positive_and_negative_matching(self):
        # 1. Kriterlere tam uyan ilan
        good_listing = {
            'title': 'Sahibinden Temiz Kirmizi Hatasiz Clio Touch',
            'price': '620.000 TL'
        }
        matched, reason = match_listing(good_listing, self.target)
        self.assertTrue(matched)

        # 2. Negatif kelime iceren ilan (agir hasarli) -> Reddedilmeli!
        bad_listing = {
            'title': 'Kirmizi Clio Agir Hasar Kayitli Masrafsiz',
            'price': '500.000 TL'
        }
        matched, reason = match_listing(bad_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("İstenmeyen kelime", reason)

        # 3. Fiyat limitinin disinda olan ilan -> Reddedilmeli!
        expensive_listing = {
            'title': 'Kirmizi Hatasiz Clio Icon Paket',
            'price': '850.000 TL'
        }
        matched, reason = match_listing(expensive_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("maksimum", reason)

    def test_login_flow(self):
        request = self.factory.post('/login/', {
            'username': 'ahmet',
            'telegram_chat_id': '987654'
        })
        self._add_middleware(request)
        response = login_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserProfile.objects.filter(username='ahmet').exists())

    def test_add_target_flow(self):
        request = self.factory.post('/targets/add/', {
            'title': 'Kadikoy 2+1 Daire',
            'category': 'emlak',
            'search_url': 'https://www.sahibinden.com/kiralik-daire-istanbul-kadikoy',
            'min_price': 20000,
            'max_price': 35000,
            'keywords': 'balkonlu, kombili',
            'negative_keywords': 'bodrum kat, kot'
        })
        self._add_middleware(request)
        request.session['user_id'] = self.user.id
        request.session['username'] = self.user.username

        response = add_target_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SearchTarget.objects.filter(title='Kadikoy 2+1 Daire').exists())

    def test_toggle_target(self):
        request = self.factory.get(f'/targets/{self.target.id}/toggle/')
        self._add_middleware(request)
        request.session['user_id'] = self.user.id
        request.session['username'] = self.user.username

        response = toggle_target_view(request, self.target.id)
        self.assertEqual(response.status_code, 302)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
