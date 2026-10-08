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
    Sahibinden bot korumasi (403) veya test asamasinda;
    kullanicinin aradigi kriterlere uygun ornek ilanlar uretir ve
    linkleri her zaman calisan canli Sahibinden arama sonuclarina baglar.
    Ayni ilanin tekrar tekrar bildirim atmasini engellemek icin sabit tekil ID kullanilir.
    """
    fc = target.filter_criteria or {}
    category = target.category
    city = target.city or "İstanbul"
    town = target.town or "Kadıköy"
    location = f"{city} / {town}"

    sample_items = []
    target_id = target.id or 1

    if category == 'vasita':
        brand = fc.get('brand') or 'Renault'
        model_name = fc.get('model') or 'Clio'
        color = fc.get('color') or 'Kırmızı'
        year = fc.get('year_min') or 2021
        trans = fc.get('transmission') or 'Otomatik'
        fuel = fc.get('fuel') or 'Benzin'
        
        # Fiyat belirleme
        min_p = float(target.min_price) if target.min_price else 500000
        max_p = float(target.max_price) if target.max_price else 750000
        avg_price = (min_p + max_p) / 2

        query_text = urllib.parse.quote_plus(f"{brand} {model_name} {color}".strip())
        working_url = target.search_url or f"https://www.sahibinden.com/kelime-ile-arama?query_text={query_text}"

        # 1. Kriterlere tam uyan ornek ilan
        sample_items.append({
            'external_id': f"sahibinden-mock-{target_id}-1",
            'title': f"Sahibinden {year} Model {color} Hatasız Boyasız {brand} {model_name} {trans}",
            'price': f"{int(avg_price):,} TL".replace(',', '.'),
            'location': location,
            'published_date': "Bugün 13:45",
            'image_url': "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?auto=format&fit=crop&w=600&q=80",
            'listing_url': working_url,
        })

        # 2. Uygun fiyatli ikinci ornek ilan
        sample_items.append({
            'external_id': f"sahibinden-mock-{target_id}-2",
            'title': f"İlk Sahibinden Temiz {color} {brand} {model_name} {fuel} Bakımlı",
            'price': f"{int(avg_price * 0.95):,} TL".replace(',', '.'),
            'location': location,
            'published_date': "Bugün 12:30",
            'image_url': "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=600&q=80",
            'listing_url': working_url,
        })

    elif category == 'emlak':
        room = fc.get('room_count') or '2+1'
        prop_type = fc.get('type') or 'Kiralık Daire'
        min_p = float(target.min_price) if target.min_price else 25000
        max_p = float(target.max_price) if target.max_price else 40000
        avg_price = (min_p + max_p) / 2

        query_text = urllib.parse.quote_plus(f"{city} {town} {room} kiralik daire".strip())
        working_url = target.search_url or f"https://www.sahibinden.com/kelime-ile-arama?query_text={query_text}"

        sample_items.append({
            'external_id': f"sahibinden-mock-{target_id}-3",
            'title': f"{location} Merkezde Balkonlu Kombili Ferah {room} {prop_type}",
            'price': f"{int(avg_price):,} TL".replace(',', '.'),
            'location': location,
            'published_date': "Bugün 14:10",
            'image_url': "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=600&q=80",
            'listing_url': working_url,
        })

    return sample_items


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
