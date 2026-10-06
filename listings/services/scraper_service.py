import re
import requests
from bs4 import BeautifulSoup
from django.utils import timezone
import logging
from listings.models import SearchTarget, ScrapedListing
from .filter_service import match_listing
from .telegram_service import send_telegram_notification

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}


def parse_sahibinden_html(html_content: str, base_url: str = "https://www.sahibinden.com"):
    """
    Sahibinden arama sonuçları sayfasındaki ilan satırlarını ayrıştırır.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    listings = []

    # İlan satırları genellikle searchResultsItem sınıfına sahiptir
    items = soup.select('tr.searchResultsItem') or soup.select('table#searchResultsTable tbody tr')

    for item in items:
        # Reklam veya başlık satırlarını atla
        if 'nativeAd' in item.get('class', []) or 'searchResultsPromoTitle' in item.get('class', []):
            continue

        external_id = item.get('data-id')
        
        # Başlık ve Link
        title_tag = item.select_one('a.classifiedTitle') or item.select_one('td.searchResultsTitleValue a')
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        href = title_tag.get('href', '')
        if not href:
            continue

        listing_url = href if href.startswith('http') else f"{base_url}{href}"
        if not external_id:
            # Href içerisinden ilan no çıkarma (örn: /ilan/...-123456789/detay)
            id_match = re.search(r'-(\d+)(?:/|$)', href)
            external_id = id_match.group(1) if id_match else str(abs(hash(listing_url)))

        # Fiyat
        price_tag = item.select_one('td.searchResultsPriceValue') or item.select_one('div.classified-price')
        price = price_tag.get_text(strip=True) if price_tag else "Fiyat Belirtilmemiş"

        # Konum (İl / İlçe)
        loc_tag = item.select_one('td.searchResultsLocationValue')
        location = " / ".join(loc_tag.stripped_strings) if loc_tag else ""

        # Tarih
        date_tag = item.select_one('td.searchResultsDateValue')
        published_date = " ".join(date_tag.stripped_strings) if date_tag else ""

        # Görsel
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
    Belirli bir arama hedefini (SearchTarget) tarar, eşleşenleri kaydeder ve Telegram bildirimi atar.
    """
    if not target.is_active or not target.search_url:
        return {'status': 'skipped', 'message': 'Hedef aktif değil veya URL eksik.'}

    try:
        response = requests.get(target.search_url, headers=DEFAULT_HEADERS, timeout=15)
        if response.status_code != 200:
            logger.warning(f"URL taranamadı ({response.status_code}): {target.search_url}")
            return {'status': 'error', 'message': f'HTTP {response.status_code} hatası'}

        raw_listings = parse_sahibinden_html(response.text)
        new_matched_count = 0
        notified_count = 0

        for item in raw_listings:
            # 1. Mükerrer kontrolü: Bu ilan daha önce bu hedef için kaydedilmiş mi?
            if ScrapedListing.objects.filter(target=target, external_id=item['external_id']).exists():
                continue

            # 2. Filtre ve Kriter Kontrolü (Pozitif/Negatif kelimeler ve fiyat)
            is_matched, reason = match_listing(item, target)
            if not is_matched:
                continue

            # 3. Eşleşen İlanı Veritabanına Kaydet
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

            # 4. Telegram Bildirimi Gönder
            if target.user.telegram_chat_id:
                sent = send_telegram_notification(target.user.telegram_chat_id, listing)
                if sent:
                    listing.is_notified = True
                    listing.save()
                    notified_count += 1

        # Son tarama zamanını güncelle
        target.last_checked_at = timezone.now()
        target.save()

        return {
            'status': 'success',
            'scanned_total': len(raw_listings),
            'new_matched': new_matched_count,
            'notified': notified_count
        }

    except Exception as e:
        logger.error(f"Hedef tarama hatası ({target.title}): {str(e)}")
        return {'status': 'error', 'message': str(e)}


def scan_all_active_targets():
    """Tüm aktif hedefleri sırayla tarar (Zamanlayıcı tarafından çağrılır)."""
    active_targets = SearchTarget.objects.filter(is_active=True)
    results = []
    for target in active_targets:
        res = scan_target(target)
        results.append({'target': target.title, 'result': res})
    return results
