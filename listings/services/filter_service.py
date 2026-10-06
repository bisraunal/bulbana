import re
from typing import Tuple, Dict, Any


def extract_number_from_price(price_str: str) -> float | None:
    """
    '650.000 TL' veya '25.500 EUR' gibi metinlerden sayısal değeri çıkarır.
    """
    if not price_str:
        return None
    clean_digits = re.sub(r'[^\d]', '', price_str)
    try:
        return float(clean_digits) if clean_digits else None
    except ValueError:
        return None


def match_listing(listing_data: Dict[str, Any], target) -> Tuple[bool, str]:
    """
    Bir ilanın kullanıcının kapsamlı arama kriterlerine (SearchTarget ve filter_criteria)
    uyup uymadığını denetler.
    Dönüş: (is_matched: bool, reason: str)
    """
    title = (listing_data.get('title') or '').lower()
    location = (listing_data.get('location') or '').lower()
    price_str = listing_data.get('price') or ''
    parsed_price = extract_number_from_price(price_str)
    fc = target.filter_criteria or {}
    attributes = listing_data.get('attributes') or {}

    # 1. Negatif Filtre Kontrolü (İstenmeyen Kelimeler - Örn: 'ağır hasar', 'pert', 'taksi')
    negative_words = []
    if target.negative_keywords:
        negative_words.extend([w.strip().lower() for w in target.negative_keywords.split(',') if w.strip()])
    
    # Eğer filtre kriterlerinde 'Ağır Hasarsız' seçildiyse otomatik ekle
    damage_status = fc.get('damage_status')
    if damage_status and 'ağır hasar' in damage_status.lower():
        negative_words.extend(['ağır hasar', 'pert', 'taksi çıkması'])

    for neg in negative_words:
        if neg in title or neg in location:
            return False, f"İstenmeyen kelime bulundu: '{neg}'"

    # 2. Şehir & İlçe Lokasyon Kontrolü
    if target.city:
        city_lower = target.city.lower()
        if city_lower not in location and city_lower not in title:
            # Eğer konum bilgisi varsa ve uyuşmuyorsa
            if location:
                return False, f"İl uyuşmuyor: '{target.city}' bekleniyordu, gelen: '{location}'"

    if target.town:
        town_lower = target.town.lower()
        if town_lower not in location and town_lower not in title:
            if location:
                return False, f"İlçe uyuşmuyor: '{target.town}'"

    # 3. Pozitif Filtre Kontrolü (Aranan Kelimeler - Örn: 'kırmızı', 'hatasız')
    positive_words = []
    if target.keywords:
        positive_words.extend([w.strip().lower() for w in target.keywords.split(',') if w.strip()])

    # JSON kriterlerindeki marka/model/renk/vites/oda sayısı da aranabilir
    if fc.get('color'):
        positive_words.append(fc['color'].lower())
    if fc.get('room_count'):
        positive_words.append(fc['room_count'].lower())

    if positive_words:
        matched_any = any(pos in title for pos in positive_words)
        if not matched_any:
            return False, f"Aranan kriter kelimeleri başlıkta bulunamadı ({', '.join(positive_words)})"

    # 4. Fiyat Sınırları Kontrolü
    if parsed_price is not None:
        if target.min_price and parsed_price < float(target.min_price):
            return False, f"Fiyat ({parsed_price:,.0f} TL) minimum ({target.min_price:,.0f} TL) altında."
        if target.max_price and parsed_price > float(target.max_price):
            return False, f"Fiyat ({parsed_price:,.0f} TL) maksimum ({target.max_price:,.0f} TL) üzerinde."

    # 5. Yıl Kontrolü (Başlıktan veya özelliklerden yıl tespiti)
    year_min = fc.get('year_min')
    year_max = fc.get('year_max')
    if year_min or year_max:
        # Başlıktan 4 basamaklı yıl tespiti (1990 - 2030)
        year_match = re.search(r'\b(19\d\d|20\d\d)\b', title)
        if year_match:
            found_year = int(year_match.group(1))
            if year_min and found_year < int(year_min):
                return False, f"Yıl ({found_year}) minimum ({year_min}) altında."
            if year_max and found_year > int(year_max):
                return False, f"Yıl ({found_year}) maksimum ({year_max}) üzerinde."

    return True, "Kapsamlı kriterlere tam uyumlu!"
