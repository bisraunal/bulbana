import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.test import TestCase, Client
from django.core.management import call_command
from django.urls import reverse
from io import StringIO
from copy import copy
from django.template.context import BaseContext

# Python 3.14 + Django 5.1 compatibility patch for test client template context copy
def _patched_base_context_copy(self):
    duplicate = object.__new__(self.__class__)
    duplicate.__dict__.update(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate

BaseContext.__copy__ = _patched_base_context_copy

from .models import UserProfile, SearchTarget, ScrapedListing
from .forms import SearchTargetForm, UserProfileForm
from .services.filter_service import extract_number_from_price, match_listing
from .services.telegram_service import send_telegram_notification, send_telegram_test_message
from .services.scraper_service import (
    parse_sahibinden_html, generate_smart_fallback_listings,
    scan_target, scan_all_active_targets
)


class BulBanaModelTests(TestCase):
    """BulBana veri modelleri ve metod testleri."""

    def setUp(self):
        self.user = UserProfile.objects.create(username="testpilot", telegram_chat_id="998877")

    def test_user_profile_str_and_ordering(self):
        self.assertEqual(str(self.user), "testpilot")
        user2 = UserProfile.objects.create(username="neweruser")
        users = list(UserProfile.objects.all())
        # En yeni eklenen en başta olmalı (-created_at)
        self.assertEqual(users[0], user2)

    def test_search_target_str_and_cascade(self):
        target = SearchTarget.objects.create(
            user=self.user,
            title="Kadıköy 2+1",
            category="emlak"
        )
        self.assertEqual(str(target), "testpilot - Kadıköy 2+1")

        # User silindiğinde target da silinmeli (CASCADE)
        self.user.delete()
        self.assertFalse(SearchTarget.objects.filter(id=target.id).exists())

    def test_search_target_badges_vasita(self):
        target = SearchTarget.objects.create(
            user=self.user,
            title="Temiz Megane",
            category="vasita",
            city="İzmir",
            town="Bornova",
            filter_criteria={
                "brand": "Renault",
                "model": "Megane",
                "year_min": 2019,
                "year_max": 2022,
                "km_max": 80000,
                "transmission": "Otomatik",
                "fuel": "Dizel",
                "color": "Beyaz",
                "damage_status": "Ağır Hasarsız"
            }
        )
        badges = target.get_badge_list()
        self.assertIn("Konum: İzmir / Bornova", badges)
        self.assertIn("Renault Megane", badges)
        self.assertIn("2019-2022 Model", badges)
        self.assertIn("Max 80000 KM", badges)
        self.assertIn("Otomatik", badges)
        self.assertIn("Dizel", badges)
        self.assertIn("Renk: Beyaz", badges)
        self.assertIn("Ağır Hasarsız", badges)

    def test_search_target_badges_emlak(self):
        target = SearchTarget.objects.create(
            user=self.user,
            title="Balkonlu Daire",
            category="emlak",
            city="Ankara",
            filter_criteria={
                "type": "Kiralık Daire",
                "room_count": "3+1",
                "m2_min": 110,
                "balcony": True,
                "furnished": True
            }
        )
        badges = target.get_badge_list()
        self.assertIn("Konum: Ankara", badges)
        self.assertIn("Kiralık Daire", badges)
        self.assertIn("3+1", badges)
        self.assertIn("Min 110 m²", badges)
        self.assertIn("Balkonlu", badges)
        self.assertIn("Eşyalı", badges)

    def test_scraped_listing_str_and_unique_constraint(self):
        target = SearchTarget.objects.create(user=self.user, title="Alarm 1")
        listing = ScrapedListing.objects.create(
            target=target,
            external_id="123456",
            title="Megane Touch",
            price="800.000 TL",
            listing_url="https://sahibinden.com/123456"
        )
        self.assertEqual(str(listing), "[123456] Megane Touch - 800.000 TL")

        # Aynı hedef ve aynı external_id ile mükerrer eklenemez
        with self.assertRaises(Exception):
            ScrapedListing.objects.create(
                target=target,
                external_id="123456",
                title="Megane Touch Farklı Başlık",
                price="850.000 TL",
                listing_url="https://sahibinden.com/123456"
            )


class BulBanaFormTests(TestCase):
    """Django Forms validasyon testleri."""

    def test_search_target_form_valid(self):
        data = {
            'title': 'Otomatik Polo',
            'category': 'vasita',
            'city': 'İstanbul',
            'town': 'Beşiktaş',
            'min_price': 600000,
            'max_price': 900000,
            'search_url': 'https://www.sahibinden.com/polo',
            'keywords': 'polo, dsg',
            'negative_keywords': 'pert',
            'is_active': True
        }
        form = SearchTargetForm(data=data)
        self.assertTrue(form.is_valid())

    def test_search_target_form_price_validation(self):
        # Negatif minimum fiyat
        form = SearchTargetForm(data={'title': 'Test', 'min_price': -100})
        self.assertFalse(form.is_valid())
        self.assertIn('min_price', form.errors)

        # Min fiyat > Max fiyat
        form = SearchTargetForm(data={'title': 'Test', 'min_price': 1000, 'max_price': 500})
        self.assertFalse(form.is_valid())
        self.assertIn('max_price', form.errors)

    def test_user_profile_form(self):
        form = UserProfileForm(data={'username': 'yeni_kullanici', 'telegram_chat_id': '12345'})
        self.assertTrue(form.is_valid())


class BulBanaFilterServiceTests(TestCase):
    """Kapsamlı ilan filtreleme ve eşleştirme motoru testleri."""

    def setUp(self):
        self.user = UserProfile.objects.create(username="filteruser")
        self.target = SearchTarget.objects.create(
            user=self.user,
            title="Kırmızı Temiz Clio",
            category="vasita",
            city="İstanbul",
            town="Kadıköy",
            min_price=500000,
            max_price=750000,
            filter_criteria={
                "color": "Kırmızı",
                "year_min": 2019,
                "year_max": 2023,
                "damage_status": "Ağır Hasarsız"
            },
            keywords="kırmızı, hatasız",
            negative_keywords="ağır hasar, pert, taksi"
        )

    def test_extract_number_from_price(self):
        self.assertEqual(extract_number_from_price("650.000 TL"), 650000.0)
        self.assertEqual(extract_number_from_price("25.500 EUR"), 25500.0)
        self.assertEqual(extract_number_from_price("1.250.000"), 1250000.0)
        self.assertIsNone(extract_number_from_price("Fiyat Belirtilmedi"))
        self.assertIsNone(extract_number_from_price(""))
        self.assertIsNone(extract_number_from_price(None))

    def test_match_listing_perfect_match(self):
        listing = {
            'title': 'Sahibinden 2021 Model Kırmızı Hatasız Clio Touch',
            'location': 'İstanbul / Kadıköy',
            'price': '640.000 TL'
        }
        matched, reason = match_listing(listing, self.target)
        self.assertTrue(matched)
        self.assertIn("uyumlu", reason.lower())

    def test_match_listing_negative_keywords_rejected(self):
        listing = {
            'title': '2021 Kırmızı Clio Ağır Hasar Kayıtlı Fırsat',
            'location': 'İstanbul / Kadıköy',
            'price': '550.000 TL'
        }
        matched, reason = match_listing(listing, self.target)
        self.assertFalse(matched)
        self.assertIn("İstenmeyen kelime", reason)

    def test_match_listing_city_mismatch(self):
        listing = {
            'title': '2021 Kırmızı Hatasız Clio',
            'location': 'Ankara / Çankaya',
            'price': '640.000 TL'
        }
        matched, reason = match_listing(listing, self.target)
        self.assertFalse(matched)
        self.assertIn("İl uyuşmuyor", reason)

    def test_match_listing_town_mismatch(self):
        listing = {
            'title': '2021 Kırmızı Hatasız Clio',
            'location': 'İstanbul / Beşiktaş',
            'price': '640.000 TL'
        }
        matched, reason = match_listing(listing, self.target)
        self.assertFalse(matched)
        self.assertIn("İlçe uyuşmuyor", reason)

    def test_match_listing_price_limits(self):
        # Min fiyattan düşük
        low_listing = {
            'title': '2021 Kırmızı Hatasız Clio',
            'location': 'İstanbul / Kadıköy',
            'price': '450.000 TL'
        }
        matched, reason = match_listing(low_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("minimum", reason)

        # Max fiyattan yüksek
        high_listing = {
            'title': '2021 Kırmızı Hatasız Clio',
            'location': 'İstanbul / Kadıköy',
            'price': '850.000 TL'
        }
        matched, reason = match_listing(high_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("maksimum", reason)

    def test_match_listing_year_limits(self):
        # 2017 Model (min 2019 bekleniyor)
        old_listing = {
            'title': '2017 Model Kırmızı Hatasız Clio',
            'location': 'İstanbul / Kadıköy',
            'price': '600.000 TL'
        }
        matched, reason = match_listing(old_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("Yıl", reason)

    def test_match_listing_year_max_exceeded(self):
        new_listing = {
            'title': '2025 Model Kırmızı Hatasız Clio',
            'location': 'İstanbul / Kadıköy',
            'price': '600.000 TL'
        }
        matched, reason = match_listing(new_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("maksimum", reason)

    def test_match_listing_keywords_not_in_title(self):
        diff_listing = {
            'title': '2021 Model Mavi Boyalı Clio',
            'location': 'İstanbul / Kadıköy',
            'price': '600.000 TL'
        }
        matched, reason = match_listing(diff_listing, self.target)
        self.assertFalse(matched)
        self.assertIn("Aranan kriter kelimeleri", reason)



class BulBanaTelegramServiceTests(TestCase):
    """Telegram bildirim servisi testleri."""

    def setUp(self):
        self.user = UserProfile.objects.create(username="teleuser", telegram_chat_id="11223344")
        self.target = SearchTarget.objects.create(user=self.user, title="Alarm Test")
        self.listing = ScrapedListing.objects.create(
            target=self.target,
            external_id="888111",
            title="Test İlanı",
            price="500.000 TL",
            location="İstanbul",
            image_url="https://images.unsplash.com/sample.jpg",
            listing_url="https://sahibinden.com/888111"
        )

    @patch('listings.services.telegram_service.os.getenv')
    def test_missing_token_or_chat_id_fails_silently(self, mock_getenv):
        mock_getenv.return_value = None
        result = send_telegram_notification("11223344", self.listing)
        self.assertFalse(result)

        result_test = send_telegram_test_message("11223344", "teleuser")
        self.assertFalse(result_test)

    @patch('listings.services.telegram_service.requests.post')
    @patch('listings.services.telegram_service.os.getenv')
    def test_send_photo_notification_success(self, mock_getenv, mock_post):
        mock_getenv.return_value = "fake-token"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_post.return_value = mock_resp

        result = send_telegram_notification("11223344", self.listing)
        self.assertTrue(result)
        self.assertIn("sendPhoto", mock_post.call_args[0][0])

    @patch('listings.services.telegram_service.requests.post')
    @patch('listings.services.telegram_service.os.getenv')
    def test_send_text_notification_when_no_image(self, mock_getenv, mock_post):
        mock_getenv.return_value = "fake-token"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_post.return_value = mock_resp

        self.listing.image_url = ""
        result = send_telegram_notification("11223344", self.listing)
        self.assertTrue(result)
        self.assertIn("sendMessage", mock_post.call_args[0][0])

    @patch('listings.services.telegram_service.requests.post')
    @patch('listings.services.telegram_service.os.getenv')
    def test_send_telegram_test_message_success(self, mock_getenv, mock_post):
        mock_getenv.return_value = "fake-token"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_post.return_value = mock_resp

        result = send_telegram_test_message("11223344", "teleuser")
        self.assertTrue(result)

    @patch('listings.services.telegram_service.requests.post')
    @patch('listings.services.telegram_service.os.getenv')
    def test_send_telegram_notification_api_failure(self, mock_getenv, mock_post):
        mock_getenv.return_value = "fake-token"
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": False, "description": "Chat not found"}
        mock_post.return_value = mock_resp

        result = send_telegram_notification("11223344", self.listing)
        self.assertFalse(result)

    @patch('listings.services.telegram_service.requests.post')
    @patch('listings.services.telegram_service.os.getenv')
    def test_send_telegram_notification_exception(self, mock_getenv, mock_post):
        mock_getenv.return_value = "fake-token"
        mock_post.side_effect = Exception("Connection refused")

        result = send_telegram_notification("11223344", self.listing)
        self.assertFalse(result)

    @patch('listings.services.telegram_service.requests.post')
    @patch('listings.services.telegram_service.os.getenv')
    def test_send_telegram_test_message_exception(self, mock_getenv, mock_post):
        mock_getenv.return_value = "fake-token"
        mock_post.side_effect = Exception("Connection error")

        result = send_telegram_test_message("11223344", "teleuser")
        self.assertFalse(result)



class BulBanaScraperServiceTests(TestCase):
    """Web scraping ve fallback motoru testleri."""

    def setUp(self):
        self.user = UserProfile.objects.create(username="scraperuser", telegram_chat_id="555")
        self.target = SearchTarget.objects.create(
            user=self.user,
            title="Otomatik Renault",
            category="vasita",
            city="İstanbul",
            town="Kadıköy",
            search_url="https://www.sahibinden.com/otomobil-renault",
            is_active=True
        )

    def test_parse_sahibinden_html_mock_table(self):
        sample_html = """
        <table id="searchResultsTable">
            <tbody>
                <tr class="searchResultsItem" data-id="987654321">
                    <td class="searchResultsLargeThumbnail">
                        <img src="https://image.sahibinden.com/1.jpg" />
                    </td>
                    <td class="searchResultsTitleValue">
                        <a class="classifiedTitle" href="/ilan/vasita-otomobil-987654321/detay">2020 Renault Megane</a>
                    </td>
                    <td class="searchResultsPriceValue">720.000 TL</td>
                    <td class="searchResultsDateValue">14 Ekim 2026</td>
                    <td class="searchResultsLocationValue">İstanbul / Kadıköy</td>
                </tr>
                <tr class="searchResultsItem nativeAd">
                    <td>Reklam Satırı</td>
                </tr>
            </tbody>
        </table>
        """
        listings = parse_sahibinden_html(sample_html)
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0]['external_id'], '987654321')
        self.assertEqual(listings[0]['title'], '2020 Renault Megane')
        self.assertEqual(listings[0]['price'], '720.000 TL')
        self.assertIn('İstanbul', listings[0]['location'])

    def test_generate_smart_fallback_listings_vasita(self):
        fallbacks = generate_smart_fallback_listings(self.target)
        self.assertGreaterEqual(len(fallbacks), 1)
        self.assertIn("sahibinden-mock", fallbacks[0]['external_id'])
        self.assertIn("TL", fallbacks[0]['price'])

    def test_generate_smart_fallback_listings_emlak(self):
        emlak_target = SearchTarget.objects.create(
            user=self.user,
            title="Kiralık Kadıköy",
            category="emlak",
            city="İstanbul",
            town="Moda",
            search_url="https://sahibinden.com/emlak"
        )
        fallbacks = generate_smart_fallback_listings(emlak_target)
        self.assertGreaterEqual(len(fallbacks), 1)
        self.assertIn("Moda", fallbacks[0]['title'])

    @patch('listings.services.scraper_service.send_telegram_notification')
    @patch('listings.services.scraper_service.fetch_html_content')
    def test_scan_target_saves_and_notifies(self, mock_fetch, mock_notify):
        mock_fetch.return_value = ("", 403)  # Bot koruması simülasyonu -> fallback devreye girer
        mock_notify.return_value = True

        result = scan_target(self.target)
        self.assertEqual(result['status'], 'success')
        self.assertGreaterEqual(result['new_matched'], 1)
        self.assertTrue(ScrapedListing.objects.filter(target=self.target).exists())

        # İkinci taramada aynı ilan mükerrer eklenmemeli (Deduplication)
        result2 = scan_target(self.target)
        self.assertEqual(result2['new_matched'], 0)

    def test_scan_target_skipped_when_inactive(self):
        self.target.is_active = False
        self.target.save()
        result = scan_target(self.target)
        self.assertEqual(result['status'], 'skipped')

    @patch('listings.services.scraper_service.scan_target')
    def test_scan_all_active_targets(self, mock_scan):
        mock_scan.return_value = {'status': 'success'}
        SearchTarget.objects.create(
            user=self.user,
            title="Pasif Hedef",
            is_active=False
        )
        results = scan_all_active_targets()
        self.assertEqual(len(results), 1)
        mock_scan.assert_called_once_with(self.target)



class BulBanaViewAndApiTests(TestCase):
    """Panel arayüzü ve REST API uç nokta testleri."""

    def setUp(self):
        self.client = Client()
        self.user = UserProfile.objects.create(username="webuser", telegram_chat_id="777888")
        self.target = SearchTarget.objects.create(
            user=self.user,
            title="Takip 1",
            category="vasita",
            city="İstanbul",
            town="Kadıköy",
            search_url="https://sahibinden.com/arama"
        )

    def _login_user(self):
        session = self.client.session
        session['user_id'] = self.user.id
        session['username'] = self.user.username
        session.save()

    def test_login_view_get_and_post(self):
        # GET Login sayfası
        resp = self.client.get(reverse('login'))
        self.assertEqual(resp.status_code, 200)

        # POST Boş Kullanıcı Adı
        resp_fail = self.client.post(reverse('login'), {'username': ''})
        self.assertEqual(resp_fail.status_code, 200)

        # POST Başarılı Giriş
        resp_success = self.client.post(reverse('login'), {'username': 'yeni_uye', 'telegram_chat_id': '123'})
        self.assertEqual(resp_success.status_code, 302)
        self.assertTrue(UserProfile.objects.filter(username='yeni_uye').exists())

    def test_logout_view(self):
        self._login_user()
        resp = self.client.get(reverse('logout'))
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn('user_id', self.client.session)

    def test_dashboard_view_authenticated(self):
        self._login_user()
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('targets', resp.context)
        self.assertIn('recent_listings', resp.context)

    def test_dashboard_view_unauthenticated_redirects(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp.url)

    @patch('listings.services.telegram_service.send_telegram_test_message')
    def test_profile_view_update_with_test_message(self, mock_test_msg):
        mock_test_msg.return_value = True
        self._login_user()

        resp = self.client.post(reverse('profile'), {
            'telegram_chat_id': '999000',
            'send_test': '1'
        })
        self.assertEqual(resp.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_chat_id, '999000')
        mock_test_msg.assert_called_once_with('999000', self.user.username)

    def test_add_target_view_vasita(self):
        self._login_user()
        post_data = {
            'title': 'Kırmızı Clio Alarmı',
            'category': 'vasita',
            'city': 'İstanbul',
            'town': 'Kadıköy',
            'brand': 'Renault',
            'model_name': 'Clio',
            'year_min': '2020',
            'year_max': '2023',
            'color': 'Kırmızı',
            'damage_status': 'Ağır Hasarsız',
            'min_price': '500000',
            'max_price': '750000',
            'keywords': 'hatasız'
        }
        resp = self.client.post(reverse('add_target'), post_data)
        self.assertEqual(resp.status_code, 302)
        new_target = SearchTarget.objects.get(title='Kırmızı Clio Alarmı')
        self.assertEqual(new_target.category, 'vasita')
        self.assertEqual(new_target.filter_criteria.get('brand'), 'Renault')
        self.assertIn('sahibinden.com', new_target.search_url)

    def test_toggle_and_delete_target_view(self):
        self._login_user()
        target_id = self.target.id

        # Toggle (Aktif -> Pasif)
        resp_toggle = self.client.get(reverse('toggle_target', args=[target_id]))
        self.assertEqual(resp_toggle.status_code, 302)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)

        # Delete
        resp_delete = self.client.get(reverse('delete_target', args=[target_id]))
        self.assertEqual(resp_delete.status_code, 302)
        self.assertFalse(SearchTarget.objects.filter(id=target_id).exists())

    @patch('listings.services.scraper_service.scan_target')
    def test_scan_target_manual_view(self, mock_scan):
        mock_scan.return_value = {'status': 'success', 'scanned_total': 5, 'new_matched': 2}
        self._login_user()

        resp = self.client.get(reverse('scan_target', args=[self.target.id]))
        self.assertEqual(resp.status_code, 302)
        mock_scan.assert_called_once_with(self.target)

    def test_api_targets_endpoint(self):
        resp = self.client.get(f"{reverse('api_targets')}?username={self.user.username}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('targets', data)
        self.assertEqual(len(data['targets']), 1)

    def test_api_listings_endpoint(self):
        ScrapedListing.objects.create(
            target=self.target,
            external_id="555444",
            title="Örnek İlan",
            price="600.000 TL",
            listing_url="https://sahibinden.com/555444"
        )
        resp = self.client.get(f"{reverse('api_listings')}?username={self.user.username}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('listings', data)
        self.assertEqual(len(data['listings']), 1)

    @patch('listings.services.scraper_service.scan_all_active_targets')
    def test_api_cron_scan_endpoint(self, mock_scan_all):
        mock_scan_all.return_value = [{'target': 'Takip 1', 'result': 'success'}]

        # Yanlış anahtar -> 403
        resp_unauth = self.client.get(f"{reverse('api_cron_scan')}?secret=wrong")
        self.assertEqual(resp_unauth.status_code, 403)

        # Doğru anahtar -> 200
        resp_auth = self.client.get(f"{reverse('api_cron_scan')}?secret=bulbana-cron-secret-key-2026")
        self.assertEqual(resp_auth.status_code, 200)
        data = resp_auth.json()
        self.assertEqual(data['status'], 'success')

    def test_api_targets_endpoint_missing_username(self):
        resp = self.client.get(reverse('api_targets'))
        self.assertEqual(resp.status_code, 400)

    def test_api_listings_endpoint_missing_username(self):
        resp = self.client.get(reverse('api_listings'))
        self.assertEqual(resp.status_code, 400)

    def test_profile_view_get(self):
        self._login_user()
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 200)

    def test_add_target_view_get(self):
        self._login_user()
        resp = self.client.get(reverse('add_target'))
        self.assertEqual(resp.status_code, 200)

    def test_add_target_view_missing_title(self):
        self._login_user()
        resp = self.client.post(reverse('add_target'), {'title': ''})
        self.assertEqual(resp.status_code, 200)

    def test_add_target_view_emlak(self):
        self._login_user()
        post_data = {
            'title': 'Moda 2+1 Emlak',
            'category': 'emlak',
            'city': 'İstanbul',
            'town': 'Kadıköy',
            'prop_type': 'Kiralık Daire',
            'room_count': '2+1',
            'm2_min': '85',
            'building_age': '0-5',
            'balcony': '1',
            'furnished': '1',
            'heating': 'Kombi',
            'min_price': '20000',
            'max_price': '35000'
        }
        resp = self.client.post(reverse('add_target'), post_data)
        self.assertEqual(resp.status_code, 302)
        target = SearchTarget.objects.get(title='Moda 2+1 Emlak')
        self.assertEqual(target.category, 'emlak')
        self.assertEqual(target.filter_criteria.get('room_count'), '2+1')
        self.assertTrue(target.filter_criteria.get('balcony'))

    @patch('listings.services.scraper_service.scan_target')
    def test_scan_target_manual_view_warning(self, mock_scan):
        mock_scan.return_value = {'status': 'failed', 'message': 'Hata olustu'}
        self._login_user()
        resp = self.client.get(reverse('scan_target', args=[self.target.id]))
        self.assertEqual(resp.status_code, 302)


class BulBanaCommandTests(TestCase):
    """Management command CLI testleri."""

    @patch('listings.management.commands.run_scanner.scan_all_active_targets')
    def test_run_scanner_command_single_run(self, mock_scan_all):
        mock_scan_all.return_value = [{'target': 'Test', 'result': 'ok'}]
        out = StringIO()
        call_command('run_scanner', stdout=out)
        output = out.getvalue()
        self.assertIn("[BulBana] Ilan Tarama Motoru Baslatildi!", output)
        self.assertIn("Tarama tamamlandi", output)
        mock_scan_all.assert_called_once()

    def test_seed_data_command(self):
        out = StringIO()
        call_command('seed_data', stdout=out)
        output = out.getvalue()
        self.assertIn("Örnek veriler başarıyla yüklendi", output)
        self.assertTrue(UserProfile.objects.filter(username="demo_user").exists())
        self.assertTrue(SearchTarget.objects.filter(title__contains="Clio").exists())

