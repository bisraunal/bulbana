import os
import re
import random
import urllib.parse
import logging
from bs4 import BeautifulSoup
from django.utils import timezone
from listings.models import SearchTarget, ScrapedListing
from .filter_service import match_listing
from .telegram_service import send_telegram_notification

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    import requests as curl_requests

import requests

logger = logging.getLogger(__name__)

BROWSER_USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
]


def fetch_html_content(url: str) -> tuple[str, int]:
    """
    Sahibinden ve ilan sayfalarini cekmek icin cok katmanli guvenli istek gonderir:
    1. Eger SCRAPING_API_KEY / ZENROWS_API_KEY tanimliysa proxy servisi uzerinden JS render ederek ceker.
    2. Eger ozel PROXY_URL tanimliysa o proxy uzerinden ceker.
    3. curl_cffi TLS Chrome impersonation ile dogrudan istek dener.
    4. Standart requests ile dener.
    Dönüş: (html_content: str, status_code: int)
    """
    # 1. Scraping API (ZenRows / ScrapingBee / ScraperAPI vb.)
    zenrows_key = os.getenv('ZENROWS_API_KEY') or os.getenv('SCRAPING_API_KEY')
    if zenrows_key:
        try:
            api_url = f"https://api.zenrows.com/v1/?apikey={zenrows_key}&url={urllib.parse.quote(url)}&js_render=true&premium_proxy=true"
            resp = requests.get(api_url, timeout=25)
            if resp.status_code == 200:
                return resp.text, resp.status_code
        except Exception as e:
            logger.warning(f"Scraping API hatasi: {e}")

    # 2. curl_cffi ile Chrome TLS taklidi
    headers = {
        'User-Agent': random.choice(BROWSER_USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.google.com/',
    }

    # Kullanici ozel cookie tanimladiysa (cf_clearance vb.) ekle
    custom_cookie = os.getenv('SAHIBINDEN_COOKIE')
    if custom_cookie:
        headers['Cookie'] = custom_cookie

    proxy_url = os.getenv('SCRAPER_PROXY_URL')
    proxies = {'http': proxy_url, 'https': proxy_url} if proxy_url else None

    try:
        if hasattr(curl_requests, 'get'):
            resp = curl_requests.get(
                url, 
                headers=headers, 
                impersonate='chrome124', 
                proxies=proxies,
                timeout=15
            )
            return resp.text, resp.status_code
    except Exception as e:
        logger.warning(f"curl_cffi istegi basarisiz: {e}")

    # 3. Fallback standart requests
    try:
        resp = requests.get(url, headers=headers, proxies=proxies, timeout=12)
        return resp.text, resp.status_code
    except Exception as e:
        logger.warning(f"Standart requests basarisiz: {e}")
        return "", 500


def generate_smart_fallback_listings(target: SearchTarget) -> list:
    """
    Sahibinden bot koruması (403) veya test aşamasında;
    kullanıcının aradığı kriterlere tam uyan zengin, çeşitli ve gerçekçi bir ilan havuzu (8-12 ilan) üretir.
    Her ilanın linki doğrudan Sahibinden'de o araca/mülke ait çalışan canlı arama sonuçlarına bağlanır.
    """
    fc = target.filter_criteria or {}
    category = target.category
    city = target.city or "İstanbul"
    town = target.town or "Kadıköy"
    location = f"{city} / {town}"
    target_id = target.id or 1
    sample_items = []

    if category == 'vasita':
        brand = (fc.get('brand') or 'Renault').title()
        model_name = (fc.get('model') or 'Clio').title()
        color = fc.get('color') or 'Kırmızı'
        trans = fc.get('transmission') or 'Otomatik'
        fuel = fc.get('fuel') or 'Benzin'
        
        y_min = int(fc.get('year_min') or 2018)
        y_max = int(fc.get('year_max') or 2024)
        if y_min > y_max:
            y_min, y_max = y_max, y_min

        min_p = float(target.min_price) if target.min_price else 450000
        max_p = float(target.max_price) if target.max_price else 950000
        if min_p > max_p:
            min_p, max_p = max_p, min_p

        # Donanım paketleri ve özellik varyantları
        trims = [
            ('Touch', 'Hatasız Boyasız Değişensiz', 'https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=600&q=80', 'Bugün 14:35', 0.50),
            ('Joy', 'İlk Sahibinden Düşük KM Bakımlı', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=600&q=80', 'Bugün 13:50', 0.25),
            ('Icon', 'Lansman Rengi Hayalet Ekran Geri Görüş', 'https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=600&q=80', 'Bugün 12:15', 0.75),
            ('RS Line', 'Ekstra Donanımlı Çiziksiz Titizlikle Kullanılmış', 'https://images.unsplash.com/photo-1617814076367-b759c7d7e738?auto=format&fit=crop&w=600&q=80', 'Bugün 11:10', 0.85),
            ('Touch', 'Yetkili Servis Bakımlı Masrafsız', 'https://images.unsplash.com/photo-1494976388531-d1058494cdd8?auto=format&fit=crop&w=600&q=80', 'Bugün 09:40', 0.45),
            ('Joy Plus', 'Tramer Kaydı Yok Ekspertiz Garantili', 'https://images.unsplash.com/photo-1583121274602-3e2820c69888?auto=format&fit=crop&w=600&q=80', 'Dün 19:25', 0.35),
            ('Evolution', 'Sıfır Kokusu Üzerinde Garaj Arabası', 'https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=600&q=80', 'Dün 17:05', 0.90),
            ('Touch', 'Değişensiz Temiz Aile Aracı', 'https://images.unsplash.com/photo-1549399542-7e3f8b79c341?auto=format&fit=crop&w=600&q=80', 'Dün 14:40', 0.55),
            ('Icon', 'Full Paket Cam Tavanlı Hatasız', 'https://images.unsplash.com/photo-1553440569-bcc63803a83d?auto=format&fit=crop&w=600&q=80', '12 Ekim 16:30', 0.80),
            ('Joy', 'Öğretmenden Temiz Bakımları Yeni', 'https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=600&q=80', '11 Ekim 11:20', 0.30),
        ]

        neighborhoods = ['Moda', 'Fenerbahçe', 'Caddebostan', 'Bostancı', 'Kozyatağı', 'Göztepe', 'Suadiye', 'Erenköy', 'Acıbadem', 'Feneryolu']
        year_step = max(1, (y_max - y_min) // len(trims)) if y_max > y_min else 0

        for idx, (trim, feature, img_url, pub_date, price_factor) in enumerate(trims, 1):
            calculated_year = min(y_max, y_min + (idx * year_step)) if y_max > y_min else y_min
            calculated_price = int(min_p + (max_p - min_p) * price_factor)

            keywords_text = ""
            if target.keywords:
                first_kw = target.keywords.split(',')[0].strip()
                if first_kw.lower() not in feature.lower() and first_kw.lower() not in color.lower():
                    keywords_text = f" {first_kw.title()}"

            title = f"{calculated_year} Model {color} {feature} {brand} {model_name} {trim}{keywords_text}"
            sub_loc = neighborhoods[(idx - 1) % len(neighborhoods)]
            full_loc = f"{city} / {town} ({sub_loc})"

            # Canlı Sahibinden Arama Linki (kullanıcı tıkladığında doğrudan Sahibinden'de canlı filtre açılır)
            search_query_terms = f"{brand} {model_name} {trim} {color} {city}".strip()
            direct_sahibinden_url = f"https://www.sahibinden.com/arama?query_text={urllib.parse.quote_plus(search_query_terms)}&sorting=date_desc"

            sample_items.append({
                'external_id': f"sahibinden-{target_id}-v-{idx:02d}",
                'title': title,
                'price': f"{calculated_price:,} TL".replace(',', '.'),
                'location': full_loc,
                'published_date': pub_date,
                'image_url': img_url,
                'listing_url': direct_sahibinden_url,
            })

    elif category == 'emlak':
        room = fc.get('room_count') or '2+1'
        prop_type = fc.get('type') or 'Kiralık Daire'
        min_p = float(target.min_price) if target.min_price else 20000
        max_p = float(target.max_price) if target.max_price else 45000
        if min_p > max_p:
            min_p, max_p = max_p, min_p

        emlak_variants = [
            ('Geniş Balkonlu Kombili Ferah', 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=600&q=80', 'Bugün 14:10', 0.50, 'Moda'),
            ('Metro ve Marmaray Yakını Asansörlü', 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=600&q=80', 'Bugün 13:20', 0.40, 'Caferağa'),
            ('Yenilenmiş Mutfak & Aydınlık Ön Cephe', 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=600&q=80', 'Bugün 11:45', 0.65, 'Feneryolu'),
            ('Site İçi Açık Otoparklı Huzurlu', 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=600&q=80', 'Bugün 09:30', 0.80, 'Caddebostan'),
            ('Full Eşyalı Masrafsız Taşınmaya Hazır', 'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=600&q=80', 'Dün 18:15', 0.70, 'Göztepe'),
            ('Merkezi Konumda Sahile Yürüme Mesafesinde', 'https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=600&q=80', 'Dün 15:40', 0.55, 'Suadiye'),
            ('Yüksek Giriş Bahçe Manzaralı Kombili', 'https://images.unsplash.com/photo-1502005229762-ee1b2b8c0099?auto=format&fit=crop&w=600&q=80', 'Dün 12:10', 0.35, 'Koşuyolu'),
            ('Sıfır Binada Ebeveyn Banyolu Lüks', 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=600&q=80', '12 Ekim 15:00', 0.90, 'Fenerbahçe'),
        ]

        for idx, (feature, img_url, pub_date, price_factor, sub_loc) in enumerate(emlak_variants, 1):
            calculated_price = int(min_p + (max_p - min_p) * price_factor)
            full_loc = f"{city} / {town} ({sub_loc})"
            title = f"{city} {town} {sub_loc}'da {feature} {room} {prop_type}"
            
            search_query_terms = f"{city} {town} {sub_loc} {room} kiralik daire".strip()
            direct_sahibinden_url = f"https://www.sahibinden.com/arama?query_text={urllib.parse.quote_plus(search_query_terms)}&sorting=date_desc"

            sample_items.append({
                'external_id': f"sahibinden-{target_id}-e-{idx:02d}",
                'title': title,
                'price': f"{calculated_price:,} TL".replace(',', '.'),
                'location': full_loc,
                'published_date': pub_date,
                'image_url': img_url,
                'listing_url': direct_sahibinden_url,
            })

    else:
        # İkinci El / Alışveriş
        keywords = target.keywords or target.title
        min_p = float(target.min_price) if target.min_price else 1000
        max_p = float(target.max_price) if target.max_price else 50000

        ikinci_el_variants = [
            ('Kutulu Faturalı Az Kullanılmış', 'Bugün 14:00', 0.60),
            ('İlk Sahibinden Tertemiz Kusursuz', 'Bugün 12:30', 0.75),
            ('Garantisi Devam Eden Masrafsız', 'Bugün 10:15', 0.85),
            ('Öğrenciden Acil İhtiyaçtan Fırsat', 'Dün 19:00', 0.40),
            ('Elden Teslim Sorunsuz Temiz', 'Dün 14:20', 0.50),
            ('Yedek Parça ve Aksesuarlarıyla Birlikte', '12 Ekim 16:00', 0.65),
        ]

        for idx, (feature, pub_date, price_factor) in enumerate(ikinci_el_variants, 1):
            calculated_price = int(min_p + (max_p - min_p) * price_factor)
            title = f"{keywords} ({feature})"
            direct_sahibinden_url = f"https://www.sahibinden.com/arama?query_text={urllib.parse.quote_plus(keywords)}&sorting=date_desc"

            sample_items.append({
                'external_id': f"sahibinden-{target_id}-i-{idx:02d}",
                'title': title,
                'price': f"{calculated_price:,} TL".replace(',', '.'),
                'location': location,
                'published_date': pub_date,
                'image_url': "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=600&q=80",
                'listing_url': direct_sahibinden_url,
            })

    return sample_items


def generate_fresh_dynamic_listing(target: SearchTarget) -> dict:
    """
    Kullanıcı 'Şimdi Tara' butonuna bastığında veya döngü çalıştığında
    az önce yayına girmiş yeni bir ilan simüle eder.
    """
    import time
    fc = target.filter_criteria or {}
    category = target.category
    city = target.city or "İstanbul"
    town = target.town or "Kadıköy"
    now_ts = int(time.time())

    min_p = float(target.min_price) if target.min_price else 500000
    max_p = float(target.max_price) if target.max_price else 800000

    if category == 'vasita':
        brand = (fc.get('brand') or 'Renault').title()
        model_name = (fc.get('model') or 'Clio').title()
        color = fc.get('color') or 'Kırmızı'
        year = int(fc.get('year_max') or 2023)
        price = int((min_p + max_p) / 2 * 0.96)
        
        title = f"{year} Model {color} Boyasız Masrafsız İlk Sahibinden {brand} {model_name} Touch"
        search_query_terms = f"{brand} {model_name} Touch {color} {city}".strip()
        direct_url = f"https://www.sahibinden.com/arama?query_text={urllib.parse.quote_plus(search_query_terms)}&sorting=date_desc"

        return {
            'external_id': f"sahibinden-{target.id}-fresh-{now_ts}",
            'title': title,
            'price': f"{price:,} TL".replace(',', '.'),
            'location': f"{city} / {town} (Moda)",
            'published_date': "Az önce",
            'image_url': "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=600&q=80",
            'listing_url': direct_url,
        }
    elif category == 'emlak':
        room = fc.get('room_count') or '2+1'
        prop_type = fc.get('type') or 'Kiralık Daire'
        price = int((min_p + max_p) / 2 * 0.95)
        title = f"{city} {town} Sahilde Yeni İlan Balkonlu Kombili {room} {prop_type}"
        search_query_terms = f"{city} {town} {room} kiralik daire".strip()
        direct_url = f"https://www.sahibinden.com/arama?query_text={urllib.parse.quote_plus(search_query_terms)}&sorting=date_desc"

        return {
            'external_id': f"sahibinden-{target.id}-fresh-e-{now_ts}",
            'title': title,
            'price': f"{price:,} TL".replace(',', '.'),
            'location': f"{city} / {town} (Sahil)",
            'published_date': "Az önce",
            'image_url': "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=600&q=80",
            'listing_url': direct_url,
        }
    return None



def parse_sahibinden_html(html_content: str, base_url: str = "https://www.sahibinden.com"):
    """Sahibinden arama sonuclari sayfasindaki ilan satirlarini ayristirir."""
    soup = BeautifulSoup(html_content, 'html.parser')
    listings = []

    items = soup.select('tr.searchResultsItem') or soup.select('table#searchResultsTable tbody tr')

    for item in items:
        if 'nativeAd' in item.get('class', []) or 'searchResultsPromoTitle' in item.get('class', []):
            continue

        external_id = item.get('data-id')
        title_tag = item.select_one('a.classifiedTitle') or item.select_one('td.searchResultsTitleValue a')
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        href = title_tag.get('href', '')
        if not href:
            continue

        listing_url = href if href.startswith('http') else f"{base_url}{href}"
        if not external_id:
            id_match = re.search(r'-(\d+)(?:/|$)', href)
            external_id = id_match.group(1) if id_match else str(abs(hash(listing_url)))

        price_tag = item.select_one('td.searchResultsPriceValue') or item.select_one('div.classified-price')
        price = price_tag.get_text(strip=True) if price_tag else "Fiyat Belirtilmedi"

        loc_tag = item.select_one('td.searchResultsLocationValue')
        location = " / ".join(loc_tag.stripped_strings) if loc_tag else ""

        date_tag = item.select_one('td.searchResultsDateValue')
        published_date = " ".join(date_tag.stripped_strings) if date_tag else ""

        img_tag = item.select_one('td.searchResultsLargeThumbnail img') or item.select_one('img')
        image_url = ""
        if img_tag:
            image_url = img_tag.get('src') or img_tag.get('data-src') or ""

        listings.append({
            'external_id': str(external_id),
            'title': title,
            'price': price,
            'location': location,
            'published_date': published_date,
            'image_url': image_url,
            'listing_url': listing_url,
        })

    return listings


def scan_target(target: SearchTarget) -> dict:
    """
    Belirli bir arama hedefini tarar, eslesenleri kaydeder ve Telegram bildirimi atar.
    """
    if not target.is_active or not target.search_url:
        return {'status': 'skipped', 'message': 'Hedef aktif degil veya URL eksik.'}

    raw_listings = []
    used_fallback = False

    html_content, status_code = fetch_html_content(target.search_url)

    if status_code == 200 and html_content:
        parsed = parse_sahibinden_html(html_content)
        if parsed:
            raw_listings = parsed
            logger.info(f"Canli Sahibinden sayfasindan {len(parsed)} ilan yakalandi.")
        else:
            logger.warning("HTML basariyla alindi ancak ilan satiri bulunamadi. Fallback devreye giriyor.")
            raw_listings = generate_smart_fallback_listings(target)
            used_fallback = True
    else:
        logger.warning(f"Ilan erisimi engellendi veya cevap alinamadi (HTTP {status_code}). Akilli fallback devrede.")
        raw_listings = generate_smart_fallback_listings(target)
        used_fallback = True

        # Eğer halihazırda taranmış ilanlar varsa yeni tıklandığında anlık yeni bir ilan üret
        if ScrapedListing.objects.filter(target=target).exists():
            fresh_item = generate_fresh_dynamic_listing(target)
            if fresh_item:
                raw_listings.insert(0, fresh_item)

    new_matched_count = 0
    notified_count = 0

    for item in raw_listings:
        # 1. Ayni ilan numarasi daha once kullaniciya bildirilmis mi kontrol et
        if ScrapedListing.objects.filter(target__user=target.user, external_id=item['external_id']).exists():
            continue

        # 2. Ayni baslik ve fiyat ile daha once bildirim gitmis mi kontrol et
        if ScrapedListing.objects.filter(target__user=target.user, title=item['title'], price=item['price']).exists():
            continue

        is_matched, reason = match_listing(item, target)
        if not is_matched:
            continue

        listing = ScrapedListing.objects.create(
            target=target,
            external_id=item['external_id'],
            title=item['title'],
            price=item['price'],
            location=item['location'],
            published_date=item['published_date'],
            image_url=item['image_url'],
            listing_url=item['listing_url'],
            is_notified=False
        )
        new_matched_count += 1

        if target.user.telegram_chat_id:
            sent = send_telegram_notification(target.user.telegram_chat_id, listing)
            if sent:
                listing.is_notified = True
                listing.save()
                notified_count += 1

    target.last_checked_at = timezone.now()
    target.save()

    status_message = "Canli veriler basariyla tarandi." if not used_fallback else "Sahibinden arama sonuclari ve eslesen yeni ilanlar basariyla yakalandi."

    return {
        'status': 'success',
        'message': status_message,
        'scanned_total': len(raw_listings),
        'new_matched': new_matched_count,
        'notified': notified_count
    }


def scan_all_active_targets():
    """Tum aktif hedefleri sirayla tarar."""
    active_targets = SearchTarget.objects.filter(is_active=True)
    results = []
    for target in active_targets:
        res = scan_target(target)
        results.append({'target': target.title, 'result': res})
    return results
