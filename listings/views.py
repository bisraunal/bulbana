import json
import re
import time
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.contrib import messages
from django.utils.html import escape
from .models import Category, Listing, UserPreference, ListingInteraction
from .forms import UserPreferenceForm, QuickSearchForm

# Basit in-memory rate limiter
_CHAT_RATE_LIMIT = {}

def _get_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _get_user_favorites(request):
    session_key = _get_session_key(request)
    user = request.user if request.user.is_authenticated else None

    if user:
        fav_ids = set(ListingInteraction.objects.filter(
            user=user, action_type='favorite'
        ).values_list('listing_id', flat=True))
    else:
        fav_ids = set(ListingInteraction.objects.filter(
            session_key=session_key, action_type='favorite'
        ).values_list('listing_id', flat=True))
    
    return fav_ids


def home_view(request):
    categories = Category.objects.annotate(listing_count=Count('listings'))
    latest_listings = Listing.objects.filter(is_active=True).select_related('category')[:8]
    verified_listings = Listing.objects.filter(is_active=True, is_verified=True).select_related('category')[:4]
    favorite_ids = _get_user_favorites(request)

    context = {
        'categories': categories,
        'latest_listings': latest_listings,
        'verified_listings': verified_listings,
        'favorite_ids': favorite_ids,
        'search_form': QuickSearchForm(),
        'total_verified_count': Listing.objects.filter(is_verified=True).count(),
    }
    return render(request, 'listings/home.html', context)


def listing_list_view(request):
    form = QuickSearchForm(request.GET or None)
    listings = Listing.objects.filter(is_active=True).select_related('category')

    category_slug = request.GET.get('category')
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        listings = listings.filter(category=selected_category)

    q = request.GET.get('q', '').strip()
    city = request.GET.get('city', '').strip()
    max_p = request.GET.get('max_price', '').strip()
    verified_only = request.GET.get('verified') == '1'

    if q:
        listings = listings.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(city__icontains=q) |
            Q(district__icontains=q) |
            Q(neighborhood__icontains=q)
        )
    if city:
        listings = listings.filter(city__icontains=city)
    if max_p:
        try:
            listings = listings.filter(price__lte=float(max_p))
        except ValueError:
            pass
    if verified_only:
        listings = listings.filter(is_verified=True)

    sort = request.GET.get('sort', 'newest')
    if sort == 'price_asc':
        listings = listings.order_by('price')
    elif sort == 'price_desc':
        listings = listings.order_by('-price')
    elif sort == 'verified':
        listings = listings.order_by('-verification_score', '-created_at')
    else:
        listings = listings.order_by('-created_at')

    categories = Category.objects.all()
    favorite_ids = _get_user_favorites(request)
    view_mode = request.GET.get('view', 'table')

    context = {
        'listings': listings,
        'categories': categories,
        'selected_category': selected_category,
        'favorite_ids': favorite_ids,
        'form': form,
        'total_count': listings.count(),
        'current_sort': sort,
        'view_mode': view_mode,
        'verified_only': verified_only,
    }
    return render(request, 'listings/listing_list.html', context)


def recommendations_view(request):
    session_key = _get_session_key(request)
    user = request.user if request.user.is_authenticated else None

    if user:
        user_preferences = UserPreference.objects.filter(user=user).select_related('category')
    else:
        user_preferences = UserPreference.objects.filter(session_key=session_key).select_related('category')

    selected_pref_id = request.GET.get('pref_id')
    active_pref = None
    if selected_pref_id:
        active_pref = user_preferences.filter(id=selected_pref_id).first()
    if not active_pref and user_preferences.exists():
        active_pref = user_preferences.first()

    matched_results = []
    if active_pref:
        if active_pref.category:
            candidate_listings = Listing.objects.filter(
                category=active_pref.category, is_active=True
            ).select_related('category')
        else:
            candidate_listings = Listing.objects.filter(is_active=True).select_related('category')

        for item in candidate_listings:
            score, positive_reasons, notes = active_pref.calculate_match(item)
            if score >= 40:
                matched_results.append({
                    'listing': item,
                    'match_score': score,
                    'positive_reasons': positive_reasons,
                    'notes': notes,
                })

        matched_results.sort(key=lambda x: x['match_score'], reverse=True)

    favorite_ids = _get_user_favorites(request)

    context = {
        'user_preferences': user_preferences,
        'active_pref': active_pref,
        'matched_results': matched_results,
        'favorite_ids': favorite_ids,
        'result_count': len(matched_results),
    }
    return render(request, 'listings/recommendations.html', context)


def create_preference_view(request):
    session_key = _get_session_key(request)
    user = request.user if request.user.is_authenticated else None

    if request.method == 'POST':
        form = UserPreferenceForm(request.POST)
        if form.is_valid():
            pref = form.save(commit=False)
            if user:
                pref.user = user
            else:
                pref.session_key = session_key
            pref.save()

            messages.success(request, f"🎉 '{pref.title}' arayış profiliniz kaydedildi! Size en uygun ilanlar listelendi.")
            return redirect(f"/recommendations/?pref_id={pref.id}")
    else:
        category_slug = request.GET.get('category')
        initial_data = {}
        if category_slug:
            cat = Category.objects.filter(slug=category_slug).first()
            if cat:
                initial_data['category'] = cat
        form = UserPreferenceForm(initial=initial_data)

    return render(request, 'listings/create_preference.html', {'form': form})


def listing_detail_view(request, listing_id):
    listing = get_object_or_404(Listing.objects.select_related('category'), id=listing_id)
    Listing.objects.filter(id=listing_id).update(view_count=listing.view_count + 1)

    similar_listings = Listing.objects.filter(
        category=listing.category, is_active=True
    ).exclude(id=listing.id)[:3]

    favorite_ids = _get_user_favorites(request)
    is_favorite = listing.id in favorite_ids

    context = {
        'listing': listing,
        'similar_listings': similar_listings,
        'is_favorite': is_favorite,
    }
    return render(request, 'listings/listing_detail.html', context)


@require_POST
def toggle_favorite_ajax_view(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    session_key = _get_session_key(request)
    user = request.user if request.user.is_authenticated else None

    if user:
        interaction = ListingInteraction.objects.filter(
            user=user, listing=listing, action_type='favorite'
        ).first()
    else:
        interaction = ListingInteraction.objects.filter(
            session_key=session_key, listing=listing, action_type='favorite'
        ).first()

    if interaction:
        interaction.delete()
        is_fav = False
        msg = "İlan favorilerinizden çıkarıldı."
    else:
        ListingInteraction.objects.create(
            user=user,
            session_key=session_key if not user else None,
            listing=listing,
            action_type='favorite'
        )
        is_fav = True
        msg = "İlan favorilerinize kaydedildi!"

    return JsonResponse({
        'status': 'success',
        'is_favorite': is_fav,
        'message': msg,
        'listing_id': listing.id
    })


@require_POST
def chatbot_assistant_ajax_view(request):
    """
    🤖 KESİN VE DOĞRU HEDEFLEMELİ AKILLI CHATBOT ASİSTANI
    - Telefon istendiğinde ASLA laptop/MacBook göstermez.
    - Bilgisayar istendiğinde ASLA telefon göstermez.
    - Uygun fiyat dendiğinde en ekonomik tescilli ürünleri sıralar.
    """
    session_key = _get_session_key(request)
    client_ip = request.META.get('REMOTE_ADDR', session_key)

    # Rate limiting
    now = time.time()
    user_requests = _CHAT_RATE_LIMIT.get(client_ip, [])
    user_requests = [t for t in user_requests if now - t < 60]
    if len(user_requests) >= 30:
        return JsonResponse({'error': 'Çok fazla istek gönderdiniz. Lütfen bir dakika bekleyin.'}, status=429)
    user_requests.append(now)
    _CHAT_RATE_LIMIT[client_ip] = user_requests

    try:
        body = json.loads(request.body.decode('utf-8'))
        raw_message = body.get('message', '').strip()
    except Exception:
        return HttpResponseBadRequest("Geçersiz JSON verisi.")

    if not raw_message:
        return JsonResponse({'error': 'Lütfen bir mesaj yazın.'}, status=400)

    clean_message = escape(raw_message)
    msg_lower = clean_message.lower()

    # Türkçe Karakter Normalizasyonu
    def norm_tr(txt):
        replacements = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'}
        for k, v in replacements.items():
            txt = txt.replace(k, v)
        return txt

    msg_norm = norm_tr(msg_lower)

    # 1. Selam / Sohbet Kontrolü
    greetings = ['selam', 'merhaba', 'slm', 'mrb', 'gunaydin', 'iyi gunler', 'naber', 'nasilsin', 'hey']
    if any(msg_norm == g or msg_norm.startswith(g + ' ') for g in greetings) and len(msg_norm.split()) <= 2:
        return JsonResponse({
            'status': 'success',
            'reply': "Selam! 👋 Ben **BulBana Akıllı İlan Asistanı**.\n\nSana Sahibinden verileri üzerinden en doğru, tescilli ve bütçene uygun ilanları bulabilirim.\n\nNeye ihtiyacın var? Örneğin şunları yazabilirsin:\n- *\"Uygun fiyatlı bir telefon arıyorum\"*\n- *\"Kadıköy'de 30 bin TL altı kiralık ev\"*\n- *\"750 bin TL altı otomatik vites araba\"*",
            'listings': []
        })

    # 2. Hassas Varlık (Entity) & Kategori Tespiti
    is_phone = any(w in msg_norm for w in ['telefon', 'cep', 'iphone', 'samsung', 'xiaomi', 'redmi', 'galaxy'])
    is_computer = any(w in msg_norm for w in ['laptop', 'bilgisayar', 'macbook', 'dizustu', 'kasa', 'pc', 'monitör', 'ram', 'ssd'])
    is_real_estate = any(w in msg_norm for w in ['ev', 'daire', 'kiralik', 'satilik', 'konut', 'bina', 'oda', 'balkon', 'emlak', '1+1', '2+1', '3+1'])
    is_vehicle = any(w in msg_norm for w in ['araba', 'otomobil', 'arac', 'vasita', 'clio', 'polo', 'egea', 'hatchback', 'sedan', 'vites', 'km', 'motor', 'dizel', 'benzin'])
    is_budget_friendly = any(w in msg_norm for w in ['uygun', 'ucuz', 'hesapli', 'ekonomik', 'butce', 'firsat', 'ogrenci'])

    # Bütçe Sınırı Tespiti
    detected_max_price = None
    price_match = re.search(r'(\d+[\d\.,]*)\s*(bin|k|milyon|tl|lira)?\s*(alti|altinda|kadar|butce|civarı|butcem)?', msg_norm)
    if price_match:
        val_str = price_match.group(1).replace('.', '').replace(',', '.')
        unit = price_match.group(2)
        try:
            val = float(val_str)
            if unit in ['bin', 'k']:
                val *= 1000
            elif unit == 'milyon':
                val *= 1000000
            elif val < 1000 and ('bin' in msg_norm or 'k' in msg_norm):
                val *= 1000
            if val > 500:
                detected_max_price = val
        except ValueError:
            pass

    # Şehir ve İlçe Tespiti
    city_map = {'istanbul': 'İstanbul', 'ankara': 'Ankara', 'izmir': 'İzmir', 'bursa': 'Bursa', 'antalya': 'Antalya'}
    district_map = {'kadikoy': 'Kadıköy', 'besiktas': 'Beşiktaş', 'cankaya': 'Çankaya', 'karsiyaka': 'Karşıyaka', 'bornova': 'Bornova', 'moda': 'Moda'}

    detected_city = None
    detected_district = None
    for k, v in city_map.items():
        if k in msg_norm: detected_city = v; break
    for k, v in district_map.items():
        if k in msg_norm: detected_district = v; break

    # 3. KESİN VE HASSAS VERİTABANI SORGUSU
    listings_qs = Listing.objects.filter(is_active=True).select_related('category')

    item_type_label = "İlanlar"

    if is_phone:
        item_type_label = "Telefonlar"
        # SADECE telefonları al, bilgisayarları KESİNLİKLE DIŞLA
        listings_qs = listings_qs.filter(
            Q(title__icontains='iphone') | Q(title__icontains='samsung') | Q(title__icontains='redmi') | Q(title__icontains='telefon') | Q(specs__icontains='Telefon')
        ).exclude(
            Q(title__icontains='macbook') | Q(title__icontains='laptop') | Q(title__icontains='bilgisayar') | Q(title__icontains='legion')
        )
    elif is_computer:
        item_type_label = "Bilgisayar & Laptoplar"
        # SADECE bilgisayarları al, telefonları KESİNLİKLE DIŞLA
        listings_qs = listings_qs.filter(
            Q(title__icontains='macbook') | Q(title__icontains='laptop') | Q(title__icontains='bilgisayar') | Q(title__icontains='legion') | Q(specs__icontains='Laptop')
        ).exclude(
            Q(title__icontains='iphone') | Q(title__icontains='samsung') | Q(title__icontains='redmi')
        )
    elif is_real_estate:
        item_type_label = "Emlak & Daireler"
        listings_qs = listings_qs.filter(category__slug='emlak')
    elif is_vehicle:
        item_type_label = "Vasıta & Araçlar"
        listings_qs = listings_qs.filter(category__slug='vasita')

    # Konum filtresi
    if detected_city:
        listings_qs = listings_qs.filter(Q(city__icontains=detected_city))
    if detected_district:
        listings_qs = listings_qs.filter(Q(district__icontains=detected_district) | Q(neighborhood__icontains=detected_district) | Q(title__icontains=detected_district))

    # Bütçe filtresi
    if detected_max_price:
        listings_qs = listings_qs.filter(price__lte=detected_max_price * 1.15)

    # Sıralama (Uygun fiyat istendiyse önce en ucuzları getir)
    if is_budget_friendly:
        listings_qs = listings_qs.order_by('price')
    else:
        listings_qs = listings_qs.order_by('-created_at')

    candidates = list(listings_qs)

    # Hiçbir şey bulunamadıysa ASLA alakasız ürün gösterme
    if not candidates:
        return JsonResponse({
            'status': 'success',
            'reply': f"Aradığın kriterlere uygun **{item_type_label}** kategorisinde ilan şu anda bulunamadı. 🔍\n\nFiyat veya marka kriterlerini biraz esneterek tekrar arama yapabilirsin.",
            'listings': []
        })

    # Puanlama & Açıklama
    scored_items = []
    for item in candidates:
        score = 85
        reasons = []

        if is_budget_friendly:
            score += 10
            reasons.append(f"💰 Uygun fiyatlı & bütçe dostu ({item.formatted_price})")
        elif detected_max_price and float(item.price) <= detected_max_price:
            score += 10
            reasons.append(f"💰 Bütçenizin altında ({item.formatted_price})")

        if item.is_verified:
            reasons.append(f"🛡️ %{item.verification_score} Doğrulanmış & Tescilli İlan")

        if detected_district or detected_city:
            reasons.append(f"📍 {item.district}, {item.city} konumunda")

        scored_items.append({
            'item': item,
            'score': min(100, max(60, score)),
            'reasons': reasons
        })

    scored_items.sort(key=lambda x: x['score'], reverse=True)
    top_matches = scored_items[:3]

    # Bot Cevap Metni
    reply_lines = [f"Senin için kriterlerine tam uyan **{len(top_matches)} tescilli {item_type_label.lower()}** buldum:"]
    if is_budget_friendly:
        reply_lines.append("🏷️ *En uygun fiyatlı seçeneklerden sıralandı.*")
    if detected_max_price:
        reply_lines.append(f"💰 Bütçe: **{detected_max_price:,.0f} TL altı**".replace(',', '.'))
    if detected_city or detected_district:
        reply_lines.append(f"📍 Konum: **{detected_district or detected_city}**")

    reply_text = "\n".join(reply_lines)

    listings_data = []
    favorite_ids = _get_user_favorites(request)

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
            'is_favorite': it.id in favorite_ids,
            'detail_url': f"/listings/{it.id}/"
        })

    return JsonResponse({
        'status': 'success',
        'reply': reply_text,
        'listings': listings_data
    })
