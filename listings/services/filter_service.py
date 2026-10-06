import re
from typing import Tuple, Dict, Any


def extract_number_from_price(price_str: str) -> float | None:
    """
    '650.000 TL' veya '25.500 EUR' gibi metinlerden sayısal değeri çıkarır.
    """
    if not price_str:
        return None
    # Sadece rakamları al
    clean_digits = re.sub(r'[^\d]', '', price_str)
    try:
        return float(clean_digits) if clean_digits else None
    except ValueError:
        return None


def match_listing(listing_data: Dict[str, Any], target) -> Tuple[bool, str]:
    """
    Bir ilanın kullanıcının arama kriterlerine (SearchTarget) uyup uymadığını denetler.
    Dönüş: (is_matched: bool, reason: str)
    """
    title = (listing_data.get('title') or '').lower()
    price_str = listing_data.get('price') or ''
    parsed_price = extract_number_from_price(price_str)

    # 1. Negatif Filtre Kontrolü (İstenmeyen Kelimeler - Örn: 'ağır hasar', 'pert')
    if target.negative_keywords:
        neg_words = [w.strip().lower() for w in target.negative_keywords.split(',') if w.strip()]
        for neg in neg_words:
            if neg in title:
                return False, f"İstenmeyen kelime bulundu: '{neg}'"

    # 2. Pozitif Filtre Kontrolü (Aranan Kelimeler - Örn: 'kırmızı', 'hatasız')
    if target.keywords:
        pos_words = [w.strip().lower() for w in target.keywords.split(',') if w.strip()]
        if pos_words:
            matched_any = any(pos in title for pos in pos_words)
            if not matched_any:
                return False, f"Aranan anahtar kelimeler başlıkta eşleşmedi ({target.keywords})"

    # 3. Fiyat Aralığı Kontrolü
    if parsed_price is not None:
        if target.min_price and parsed_price < float(target.min_price):
            return False, f"Fiyat ({parsed_price} TL) belirlenen minimum ({target.min_price} TL) altında."
        if target.max_price and parsed_price > float(target.max_price):
            return False, f"Fiyat ({parsed_price} TL) belirlenen maksimum ({target.max_price} TL) üzerinde."

    return True, "Kriterlere tam uyumlu!"
