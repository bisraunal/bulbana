from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import UserProfile, SearchTarget, ScrapedListing


def login_view(request):
    """
    Basit ve hızlı kullanıcı girişi.
    Kullanıcı sadece kullanıcı adını girerek giriş yapar veya yeni profil oluşturulur.
    """
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
    """
    Kullanıcının ana paneli:
    - Tanımlı arama hedefleri (SearchTarget)
    - Sahibinden'den yakalanan ve eşleşen son ilanlar
    """
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
    """Yeni arama kriteri / alarm ekleme."""
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')

    user = get_object_or_404(UserProfile, id=user_id)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'vasita')
        search_url = request.POST.get('search_url', '').strip()
        min_price = request.POST.get('min_price') or None
        max_price = request.POST.get('max_price') or None
        keywords = request.POST.get('keywords', '').strip()
        negative_keywords = request.POST.get('negative_keywords', '').strip()

        if not title or not search_url:
            messages.error(request, "Lütfen alarm başlığı ve Sahibinden arama linkini girin.")
            return render(request, 'add_target.html')

        SearchTarget.objects.create(
            user=user,
            title=title,
            category=category,
            search_url=search_url,
            min_price=min_price,
            max_price=max_price,
            keywords=keywords,
            negative_keywords=negative_keywords,
        )
        messages.success(request, f"'{title}' alarmı başarıyla oluşturuldu!")
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
        messages.warning(request, f"Tarama uyarısı: {result.get('message', 'Bilinmeyen durum')}")

    return redirect('dashboard')

