from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import UserProfile, SearchTarget, ScrapedListing
from urllib.parse import urlencode


def build_sahibinden_url(category, city, brand, model_name, keywords):
    """Eğer kullanıcı özel bir link yapıştırmadıysa otomatik Sahibinden arama URL'i üretir."""
    query_parts = []
    if brand:
        query_parts.append(brand)
    if model_name:
        query_parts.append(model_name)
    if keywords:
        query_parts.append(keywords.replace(',', ' '))
    if city:
        query_parts.append(city)

    query_str = " ".join(query_parts).strip()
    if query_str:
        return f"https://www.sahibinden.com/kelime-ile-arama?query_text={urlencode({'q': query_str})[2:]}"
    elif category == 'vasita':
        return "https://www.sahibinden.com/otomobil"
    elif category == 'emlak':
        return "https://www.sahibinden.com/kiralik-daire"
    return "https://www.sahibinden.com/ikinci-el-ve-sifir-alisveris"


def login_view(request):
    """Basit ve hızlı kullanıcı girişi."""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        telegram_id = request.POST.get('telegram_chat_id', '').strip()

        if not username:
            messages.error(request, "Lütfen bir kullanıcı adı girin.")
            return render(request, 'login.html')

        user, created = UserProfile.objects.get_or_create(username=username)
        if telegram_id:
            user.telegram_chat_id = telegram_id
            user.save()

        request.session['user_id'] = user.id
        request.session['username'] = user.username
        messages.success(request, f"Hoş geldiniz, {user.username}!")
        return redirect('dashboard')

    if request.session.get('user_id'):
        return redirect('dashboard')

    return render(request, 'login.html')


def logout_view(request):
    """Kullanıcı oturumunu kapatır."""
    request.session.flush()
    messages.info(request, "Oturumunuz kapatıldı.")
    return redirect('login')


def dashboard_view(request):
    """Kullanıcının ana paneli."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = get_object_or_404(UserProfile, id=user_id)
    targets = user.targets.all()
    recent_listings = ScrapedListing.objects.filter(target__user=user).order_by('-created_at')[:30]

    context = {
        'user': user,
        'targets': targets,
        'recent_listings': recent_listings,
    }
    return render(request, 'dashboard.html', context)


def add_target_view(request):
    """Tüm Sahibinden filtrelerini kapsayan gelişmiş arama kriteri / alarm ekleme."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = get_object_or_404(UserProfile, id=user_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'vasita')
        city = request.POST.get('city', '').strip()
        town = request.POST.get('town', '').strip()
        search_url = request.POST.get('search_url', '').strip()
        min_price = request.POST.get('min_price') or None
        max_price = request.POST.get('max_price') or None
        keywords = request.POST.get('keywords', '').strip()
        negative_keywords = request.POST.get('negative_keywords', '').strip()

        # JSON Kriterleri Toplama
        filter_criteria = {}
        if category == 'vasita':
            brand = request.POST.get('brand', '').strip()
            model_name = request.POST.get('model_name', '').strip()
            year_min = request.POST.get('year_min', '').strip()
            year_max = request.POST.get('year_max', '').strip()
            km_max = request.POST.get('km_max', '').strip()
            transmission = request.POST.get('transmission', '').strip()
            fuel = request.POST.get('fuel', '').strip()
            color = request.POST.get('color', '').strip()
            damage_status = request.POST.get('damage_status', '').strip()
            seller_type = request.POST.get('seller_type', '').strip()

            if brand: filter_criteria['brand'] = brand
            if model_name: filter_criteria['model'] = model_name
            if year_min: filter_criteria['year_min'] = year_min
            if year_max: filter_criteria['year_max'] = year_max
            if km_max: filter_criteria['km_max'] = km_max
            if transmission: filter_criteria['transmission'] = transmission
            if fuel: filter_criteria['fuel'] = fuel
            if color: filter_criteria['color'] = color
            if damage_status: filter_criteria['damage_status'] = damage_status
            if seller_type: filter_criteria['seller_type'] = seller_type

        elif category == 'emlak':
            prop_type = request.POST.get('prop_type', '').strip()
            room_count = request.POST.get('room_count', '').strip()
            m2_min = request.POST.get('m2_min', '').strip()
            building_age = request.POST.get('building_age', '').strip()
            balcony = bool(request.POST.get('balcony'))
            furnished = bool(request.POST.get('furnished'))
            heating = request.POST.get('heating', '').strip()

            if prop_type: filter_criteria['type'] = prop_type
            if room_count: filter_criteria['room_count'] = room_count
            if m2_min: filter_criteria['m2_min'] = m2_min
            if building_age: filter_criteria['building_age'] = building_age
            if balcony: filter_criteria['balcony'] = True
            if furnished: filter_criteria['furnished'] = True
            if heating: filter_criteria['heating'] = heating

        # Eğer search_url girilmediyse otomatik URL oluştur
        if not search_url:
            search_url = build_sahibinden_url(
                category=category,
                city=city,
                brand=filter_criteria.get('brand'),
                model_name=filter_criteria.get('model'),
                keywords=keywords
            )

        if not title:
            messages.error(request, "Lütfen bir alarm başlığı belirleyin.")
            return render(request, 'add_target.html')

        SearchTarget.objects.create(
            user=user,
            title=title,
            category=category,
            city=city,
            town=town,
            search_url=search_url,
            min_price=min_price,
            max_price=max_price,
            filter_criteria=filter_criteria,
            keywords=keywords,
            negative_keywords=negative_keywords,
        )
        messages.success(request, f"'{title}' alarmı tüm filtreleriyle başarıyla oluşturuldu!")
        return redirect('dashboard')

    return render(request, 'add_target.html')


def toggle_target_view(request, target_id):
    """Alarmın aktif/pasif durumunu değiştirir."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    target = get_object_or_404(SearchTarget, id=target_id, user_id=user_id)
    target.is_active = not target.is_active
    target.save()
    status_str = "aktif edildi" if target.is_active else "durduruldu"
    messages.info(request, f"'{target.title}' alarmı {status_str}.")
    return redirect('dashboard')


def delete_target_view(request, target_id):
    """Alarmı ve bağlı ilanları siler."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    target = get_object_or_404(SearchTarget, id=target_id, user_id=user_id)
    target.delete()
    messages.success(request, f"'{target.title}' alarmı silindi.")
    return redirect('dashboard')


def scan_target_manual_view(request, target_id):
    """Kullanıcının panelden tek tıkla hedefi hemen taramasını sağlar."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    from .services.scraper_service import scan_target
    target = get_object_or_404(SearchTarget, id=target_id, user_id=user_id)
    result = scan_target(target)

    if result.get('status') == 'success':
        msg = f"'{target.title}' tarandı: {result.get('scanned_total', 0)} ilan incelendi, {result.get('new_matched', 0)} yeni eşleşen ilan bulundu!"
        messages.success(request, msg)
    else:
        messages.warning(request, f"Tarama durumu: {result.get('message', 'Bilinmeyen durum')}")

    return redirect('dashboard')
