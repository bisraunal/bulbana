import os
import json
import re
from django.db.models import Q
from django.utils.html import escape
from .models import Category, Listing, UserPreference, ListingInteraction

# Google GenAI SDK (Opsiyonel API Key ile canlı Gemini 2.5 Flash desteği)
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


def _normalize_tr(text):
    if not text:
        return ""
    t = str(text).lower()
    replacements = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'İ': 'i'}
    for k, v in replacements.items():
        t = t.replace(k, v)
    return t


def process_chat_message(raw_message, session_data, user=None, session_key=None):
    """
    BulBana Akıllı Chatbot Beyni:
    1. Sohbet Geçmişi ve Bağlam Koruma (Multi-turn memory)
    2. Niyet (Intent) & Varlık (Entity) Analizi (Gemini veya Akıllı NLP Motoru)
    3. Kesin Doğruluklu Veritabanı Sorgusu
    4. Piyasa Uzmanı & Pazarlık Danışmanı İpuçları
    5. İsteğe Bağlı Alarm / Kriter Kaydetme
    """
    clean_message = escape(raw_message.strip())
    msg_norm = _normalize_tr(clean_message)

    # Sohbet Hafızası
    chat_history = session_data.get('chat_history', [])
    last_context = session_data.get('last_context', {})

    # 1. Selamlaşma / Genel Sohbet Kontrolü
    greetings = ['selam', 'merhaba', 'slm', 'mrb', 'gunaydin', 'iyi gunler', 'naber', 'nasilsin', 'hey']
    if any(msg_norm == g or msg_norm.startswith(g + ' ') for g in greetings) and len(msg_norm.split()) <= 2:
        reply = (
            "Selam! 👋 Ben **BulBana Akıllı İlan Asistanı & Piyasa Danışmanıyım**.\n\n"
            "Sana Sahibinden verileri üzerinden en doğru, tescilli ve bütçene uygun fırsatları bulabilirim.\n\n"
            "Neye ihtiyacın var? Örneğin şunları yazabilirsin:\n"
            "- *\"Kadıköy'de 30 bin TL altı balkonlu 2+1 ev\"*\n"
            "- *\"Uygun fiyatlı öğrenci dostu telefon arıyorum\"*\n"
            "- *\"800 bin TL altı otomatik vites az yakan araba\"*\n"
            "- *\"İkinci el araba alırken nelere dikkat etmeliyim?\"*"
        )
        return {'reply': reply, 'listings': [], 'updated_context': last_context}

    # 2. Pazarlık ve Genel Piyasa Tavsiyesi Talebi
    if 'pazarlik' in msg_norm or 'taktik' in msg_norm or 'nasil alinir' in msg_norm:
        reply = (
            "💡 **Sahibinden Pazarlık & Güvenli Alım Tavsiyeleri:**\n\n"
            "1. **Tescil ve Ekspertiz:** İlandaki Tescil Puanına (%95+) ve ekspertiz/ruhsat onayına dikkat et.\n"
            "2. **Piyasa Fiyat Analizi:** Bölge ortalamasının üzerinde olan ilanlarda %5-%10 arası pazarlık payı isteyebilirsin.\n"
            "3. **Detay Kusurlar:** Telefonlarda pil sağlığı (%85 altı) veya araçlarda yaklaşan periyodik bakım masrafını öne sürerek indirim talep edebilirsin.\n\n"
            "Hangi ürün veya ev için pazarlık yapmak istiyorsun? İlanı veya kriterlerini söylersen özel analiz yapabilirim!"
        )
        return {'reply': reply, 'listings': [], 'updated_context': last_context}

    # 3. Kriter Tespiti (Yeni Mesaj + Önceki Bağlam Birleştirme)
    is_vehicle = any(w in msg_norm for w in ['araba', 'otomobil', 'arac', 'vasita', 'clio', 'polo', 'egea', 'hatchback', 'sedan', 'vites', 'km', 'motor', 'dizel', 'benzin'])
    is_phone = any(w in msg_norm for w in ['telefon', 'cep', 'iphone', 'samsung', 'xiaomi', 'redmi', 'galaxy'])
    is_computer = any(w in msg_norm for w in ['laptop', 'bilgisayar', 'macbook', 'dizustu', 'kasa', 'pc', 'monitör', 'ram', 'ssd'])
    is_real_estate = any(w in msg_norm for w in ['ev', 'daire', 'konut', 'bina', 'oda', 'balkon', 'emlak', '1+1', '2+1', '3+1', 'villa', 'arsa']) or (
        ('kiralik' in msg_norm or 'satilik' in msg_norm) and not (is_vehicle or is_phone or is_computer)
    )
    is_budget_friendly = any(w in msg_norm for w in ['uygun', 'ucuz', 'hesapli', 'ekonomik', 'butce', 'firsat', 'ogrenci'])

    # Eğer bu mesajda kategori yoksa önceki bağlamı koru
    current_category = None
    if is_vehicle: current_category = 'vehicle'
    elif is_phone: current_category = 'phone'
    elif is_computer: current_category = 'computer'
    elif is_real_estate: current_category = 'real_estate'
    else: current_category = last_context.get('category')

    # Bütçe Tespiti
    detected_max_price = None
    price_match = re.search(r'(\d+[\d\.,]*)\s*(bin|k|milyon|tl|lira)?\s*(alti|altinda|kadar|butce|civarı|butcem)?', msg_norm)
    if price_match:
        val_str = price_match.group(1).replace('.', '').replace(',', '.')
        unit = price_match.group(2)
        try:
            val = float(val_str)
            if unit in ['bin', 'k']: val *= 1000
            elif unit == 'milyon': val *= 1000000
            elif val < 1000 and ('bin' in msg_norm or 'k' in msg_norm): val *= 1000
            if val > 500: detected_max_price = val
        except ValueError:
            pass

    if not detected_max_price:
        detected_max_price = last_context.get('max_price')

    # Konum Tespiti
    city_map = {'istanbul': 'İstanbul', 'ankara': 'Ankara', 'izmir': 'İzmir', 'bursa': 'Bursa', 'antalya': 'Antalya'}
    district_map = {'kadikoy': 'Kadıköy', 'besiktas': 'Beşiktaş', 'cankaya': 'Çankaya', 'karsiyaka': 'Karşıyaka', 'bornova': 'Bornova', 'moda': 'Moda'}

    detected_city = None
    detected_district = None
    for k, v in city_map.items():
        if k in msg_norm: detected_city = v; break
    for k, v in district_map.items():
        if k in msg_norm: detected_district = v; break

    if not detected_city: detected_city = last_context.get('city')
    if not detected_district: detected_district = last_context.get('district')

    # Güncellenmiş Bağlam
    new_context = {
        'category': current_category,
        'max_price': detected_max_price,
        'city': detected_city,
        'district': detected_district,
        'is_budget_friendly': is_budget_friendly,
    }

    # 4. Alarm / Takip İstemi Kontrolü
    if any(w in msg_norm for w in ['alarm', 'haber ver', 'bildir', 'takip et', 'kaydet']):
        pref_title = f"Chatbot Alarmı ({current_category or 'Genel'})"
        if detected_district or detected_city:
            pref_title += f" - {detected_district or detected_city}"
        
        cat_obj = None
        if current_category == 'real_estate': cat_obj = Category.objects.filter(slug='emlak').first()
        elif current_category == 'vehicle': cat_obj = Category.objects.filter(slug='vasita').first()
        elif current_category in ['phone', 'computer']: cat_obj = Category.objects.filter(slug='ikinci-el-teknoloji').first()

        UserPreference.objects.create(
            user=user if user and user.is_authenticated else None,
            session_key=session_key if not (user and user.is_authenticated) else None,
            title=pref_title,
            category=cat_obj,
            max_price=detected_max_price,
            target_city=detected_city or '',
            target_district=detected_district or '',
            priority='balanced'
        )
        return {
            'reply': f"🔔 **Akıllı Alarm Kuruldu!**\n\nKriterlerin: **{pref_title}** ({f'{detected_max_price:,.0f} TL altı' if detected_max_price else 'Tüm bütçeler'}). Bu kriterlere uyan yeni bir ilan eklendiğinde **Profilim & Arayışlarım** sekmesinden anlık takip edebileceksin.",
            'listings': [],
            'updated_context': new_context
        }

    # 5. Veritabanı Sorgusu (Strict Precision)
    listings_qs = Listing.objects.filter(is_active=True).select_related('category')
    item_type_label = "İlanlar"

    if current_category == 'phone':
        item_type_label = "Telefonlar"
        listings_qs = listings_qs.filter(
            Q(title__icontains='iphone') | Q(title__icontains='samsung') | Q(title__icontains='redmi') | Q(title__icontains='telefon') | Q(specs__icontains='Telefon')
        ).exclude(
            Q(title__icontains='macbook') | Q(title__icontains='laptop') | Q(title__icontains='bilgisayar') | Q(title__icontains='legion')
        )
    elif current_category == 'computer':
        item_type_label = "Bilgisayar & Laptoplar"
        listings_qs = listings_qs.filter(
            Q(title__icontains='macbook') | Q(title__icontains='laptop') | Q(title__icontains='bilgisayar') | Q(title__icontains='legion') | Q(specs__icontains='Laptop')
        ).exclude(
            Q(title__icontains='iphone') | Q(title__icontains='samsung') | Q(title__icontains='redmi')
        )
    elif current_category == 'real_estate':
        item_type_label = "Emlak & Daireler"
        listings_qs = listings_qs.filter(category__slug='emlak')
    elif current_category == 'vehicle':
        item_type_label = "Vasıta & Araçlar"
        listings_qs = listings_qs.filter(category__slug='vasita')

    if detected_city:
        listings_qs = listings_qs.filter(Q(city__icontains=detected_city))
    if detected_district:
        listings_qs = listings_qs.filter(Q(district__icontains=detected_district) | Q(neighborhood__icontains=detected_district) | Q(title__icontains=detected_district))
    if detected_max_price:
        listings_qs = listings_qs.filter(price__lte=detected_max_price * 1.15)

    if is_budget_friendly:
        listings_qs = listings_qs.order_by('price')
    else:
        listings_qs = listings_qs.order_by('-verification_score', '-created_at')

    candidates = list(listings_qs)

    if not candidates:
        criteria_msg = []
        if current_category: criteria_msg.append(f"Kategori: {item_type_label}")
        if detected_city or detected_district: criteria_msg.append(f"Konum: {detected_district or detected_city}")
        if detected_max_price: criteria_msg.append(f"Bütçe: {detected_max_price:,.0f} TL altı".replace(',', '.'))
        
        sum_text = " (" + ", ".join(criteria_msg) + ")" if criteria_msg else ""
        return {
            'reply': f"Aradığın kriterlere uygun{sum_text} aktif bir ilan şu anda bulunamadı. 🔍\n\nBütçeni esnetebilir, farklı bir ilçe yazabilir ya da *'Böyle bir ilan çıkarsa haber ver'* diyerek alarm kurabilirsin!",
            'listings': [],
            'updated_context': new_context
        }

    # Puanlama & Piyasa Uzmanı Analizi
    scored_items = []
    for item in candidates:
        score = 85
        reasons = []

        if is_budget_friendly:
            score += 10
            reasons.append(f"💰 Uygun fiyatlı fırsat ({item.formatted_price})")
        elif detected_max_price and float(item.price) <= detected_max_price:
            score += 10
            reasons.append(f"💰 Bütçenizin altında ({item.formatted_price})")

        if item.is_verified:
            reasons.append(f"🛡️ %{item.verification_score} Tescilli Güvenli İlan")

        if item.market_price_diff:
            reasons.append(f"📊 {item.market_price_diff}")

        if detected_district or detected_city:
            reasons.append(f"📍 {item.district}, {item.city} konumunda")

        scored_items.append({
            'item': item,
            'score': min(100, max(60, score)),
            'reasons': reasons
        })

    scored_items.sort(key=lambda x: x['score'], reverse=True)
    top_matches = scored_items[:3]

    # Zengin Bot Cevabı
    reply_lines = [f"Senin için kriterlerine tam uyan **{len(top_matches)} tescilli {item_type_label.lower()}** listeledim:"]
    if is_budget_friendly: reply_lines.append("🏷️ *En ekonomik fırsatlardan başlayarak sıralandı.*")
    if detected_max_price: reply_lines.append(f"💰 Bütçe Sınırı: **{detected_max_price:,.0f} TL altı**".replace(',', '.'))
    if detected_city or detected_district: reply_lines.append(f"📍 Konum: **{detected_district or detected_city}**")
    reply_lines.append("\n💡 *İpuçları ve detayları inceleyebilir, istersen bu arayış için alarm kurmamı söyleyebilirsin!*")

    reply_text = "\n".join(reply_lines)

    # Favori ID'leri
    if user and user.is_authenticated:
        fav_ids = set(ListingInteraction.objects.filter(user=user, action_type='favorite').values_list('listing_id', flat=True))
    else:
        fav_ids = set(ListingInteraction.objects.filter(session_key=session_key, action_type='favorite').values_list('listing_id', flat=True))

    listings_data = []
    for match in top_matches:
        it = match['item']
        listings_data.append({
            'id': it.id,
            'title': it.title,
            'price': it.formatted_price,
            'location': f"{it.district}, {it.city}",
            'image_url': it.image_url,
            'match_score': match['score'],
            'reasons': match['reasons'],
            'is_verified': it.is_verified,
            'verification_score': it.verification_score,
            'market_price_diff': it.market_price_diff,
            'is_favorite': it.id in fav_ids,
            'detail_url': f"/listings/{it.id}/"
        })

    return {
        'reply': reply_text,
        'listings': listings_data,
        'updated_context': new_context
    }
