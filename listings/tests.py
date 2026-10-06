from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from .models import UserProfile, SearchTarget, ScrapedListing
from .services.filter_service import match_listing
from .views import login_view, add_target_view, toggle_target_view


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
        # 1. Kriterlere tam uyan ilan (2020 Model, İstanbul / Kadıköy, Kırmızı, 620 bin TL)
        good_listing = {
            'title': 'Sahibinden 2020 Model Temiz Kırmızı Hatasız Clio Touch',
            'location': 'İstanbul / Kadıköy',
            'price': '620.000 TL'
        }
        matched, reason = match_listing(good_listing, self.target)
        self.assertTrue(matched)

        # 2. Ağır hasarlı ilan -> Otomatik reddedilmeli!
        bad_damage_listing = {
            'title': '2020 Kırmızı Clio Ağır Hasar Kayıtlı Masrafsız',
            'location': 'İstanbul / Kadıköy',
            'price': '500.000 TL'
        }
        matched, reason = match_listing(bad_damage_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("İstenmeyen kelime", reason)

        # 3. Yıl kriterinin altında kalan ilan (2015 Model) -> Reddedilmeli!
        old_year_listing = {
            'title': '2015 Kırmızı Hatasız Clio Joy',
            'location': 'İstanbul / Kadıköy',
            'price': '450.000 TL'
        }
        matched, reason = match_listing(old_year_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("Yıl", reason)

        # 4. Fiyat limitinin üzerinde olan ilan (850 bin TL) -> Reddedilmeli!
        expensive_listing = {
            'title': '2022 Kırmızı Hatasız Clio Icon Paket',
            'location': 'İstanbul / Kadıköy',
            'price': '850.000 TL'
        }
        matched, reason = match_listing(expensive_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("maksimum", reason)

    def test_badge_list_generation(self):
        badges = self.target.get_badge_list()
        self.assertTrue(any('İstanbul' in b for b in badges))
        self.assertTrue(any('Renault' in b for b in badges))
        self.assertTrue(any('Kırmızı' in b for b in badges))

    def test_login_flow(self):
        request = self.factory.post('/login/', {
            'username': 'ahmet',
            'telegram_chat_id': '987654'
        })
        self._add_middleware(request)
        response = login_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserProfile.objects.filter(username='ahmet').exists())

    def test_add_target_comprehensive_form(self):
        request = self.factory.post('/targets/add/', {
            'title': 'Kadıköy 2+1 Daire',
            'category': 'emlak',
            'city': 'İstanbul',
            'town': 'Kadıköy',
            'prop_type': 'Kiralık Daire',
            'room_count': '2+1',
            'm2_min': '80',
            'min_price': '20000',
            'max_price': '35000',
            'keywords': 'balkonlu, kombili',
            'negative_keywords': 'bodrum kat, kot',
            'balcony': 'true'
        })
        self._add_middleware(request)
        request.session['user_id'] = self.user.id
        request.session['username'] = self.user.username

        response = add_target_view(request)
        self.assertEqual(response.status_code, 302)
        
        created_target = SearchTarget.objects.get(title='Kadıköy 2+1 Daire')
        self.assertEqual(created_target.category, 'emlak')
        self.assertEqual(created_target.filter_criteria.get('room_count'), '2+1')
        self.assertTrue(created_target.filter_criteria.get('balcony'))
