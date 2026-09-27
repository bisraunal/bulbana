import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.contrib import messages
from .models import Category, Listing, UserPreference, ListingInteraction
from .forms import UserPreferenceForm, QuickSearchForm

def _get_session_key(request):
    """Kullanıcının session anahtarını garantiler."""
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _get_user_favorites(request):
    """Giriş yapmış veya misafir kullanıcının favorilediği ilan ID listesini döner."""
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
    """Ana sayfa: Karşılama, Hızlı Arama, Kategoriler ve Öne Çıkan İlanlar."""
    categories = Category.objects.annotate(listing_count=Count('listings'))
    latest_listings = Listing.objects.filter(is_active=True).select_related('category')[:6]
    favorite_ids = _get_user_favorites(request)

    context = {
        'categories': categories,
        'latest_listings': latest_listings,
        'favorite_ids': favorite_ids,
        'search_form': QuickSearchForm(),
    }
    return render(request, 'listings/home.html', context)


def listing_list_view(request):
    """Tüm ilanların listelendiği, filtrelendiği ve arandığı akış sayfası."""
    form = QuickSearchForm(request.GET or None)
    listings = Listing.objects.filter(is_active=True).select_related('category')

    category_slug = request.GET.get('category')
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        listings = listings.filter(category=selected_category)

    if form.is_valid():
        q = form.cleaned_data.get('q')
        cat = form.cleaned_data.get('category')
        city = form.cleaned_data.get('city')
        max_p = form.cleaned_data.get('max_price')

        if q:
            listings = listings.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(city__icontains=q) |
                Q(district__icontains=q)
            )
        if cat:
            listings = listings.filter(category=cat)
        if city:
            listings = listings.filter(city__icontains=city)
        if max_p:
            listings = listings.filter(price__lte=max_p)

    sort = request.GET.get('sort', 'newest')
    if sort == 'price_asc':
        listings = listings.order_by('price')
    elif sort == 'price_desc':
        listings = listings.order_by('-price')
    else:
        listings = listings.order_by('-created_at')

    categories = Category.objects.all()
    favorite_ids = _get_user_favorites(request)

    context = {
        'listings': listings,
        'categories': categories,
        'selected_category': selected_category,
        'favorite_ids': favorite_ids,
        'form': form,
        'total_count': listings.count(),
        'current_sort': sort,
    }
    return render(request, 'listings/listing_list.html', context)


def recommendations_view(request):
    """
    Kullanıcının Arayış / Tercih Profillerine göre ilanları puanlayıp 
    'Uyum Yüzdesi' ve 'Neden Senin İçin Uygun?' açıklamalarıyla sunan öneri motoru.
    """
    session_key = _get_session_key(request)
    user = request.user if request.user.is_authenticated else None

    # Kullanıcının kayıtlı arayış profilleri
    if user:
        user_preferences = UserPreference.objects.filter(user=user).select_related('category')
    else:
        user_preferences = UserPreference.objects.filter(session_key=session_key).select_related('category')

    # Aktif profili belirle (veya en sonuncuyu al)
    selected_pref_id = request.GET.get('pref_id')
    active_pref = None
    if selected_pref_id:
        active_pref = user_preferences.filter(id=selected_pref_id).first()
    if not active_pref and user_preferences.exists():
        active_pref = user_preferences.first()

    matched_results = []
    if active_pref:
        # İlgili kategorideki tüm aktif ilanları çek
        candidate_listings = Listing.objects.filter(
            category=active_pref.category,
            is_active=True
        ).select_related('category')

        # Gizlenen ilanları filtrele
        if user:
            dismissed_ids = ListingInteraction.objects.filter(
                user=user, action_type='dismiss'
            ).values_list('listing_id', flat=True)
        else:
            dismissed_ids = ListingInteraction.objects.filter(
                session_key=session_key, action_type='dismiss'
            ).values_list('listing_id', flat=True)
        
        candidate_listings = candidate_listings.exclude(id__in=dismissed_ids)

        # Her ilan için uyum puanını ve nedenlerini hesapla
        for item in candidate_listings:
            score, positive_reasons, notes = active_pref.calculate_match(item)
            matched_results.append({
                'listing': item,
                'match_score': score,
                'positive_reasons': positive_reasons,
                'notes': notes,
            })

        # Skora göre büyükten küçüğe sırala
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
    """Yeni Arayış / Tercih Profili Oluşturma Sihirbazı."""
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

            messages.success(request, f"🎉 '{pref.title}' arayış profiliniz oluşturuldu! Size en uygun ilanlar hazırlandı.")
            return redirect(f"/recommendations/?pref_id={pref.id}")
    else:
        # URL'den gelen kategori varsa formu onunla ön-doldur
        category_slug = request.GET.get('category')
        initial_data = {}
        if category_slug:
            cat = Category.objects.filter(slug=category_slug).first()
            if cat:
                initial_data['category'] = cat
        form = UserPreferenceForm(initial=initial_data)

    return render(request, 'listings/create_preference.html', {'form': form})


def listing_detail_view(request, listing_id):
    """Tekil İlan Detay Görünümü."""
    listing = get_object_or_404(Listing.objects.select_related('category'), id=listing_id)
    
    # Görüntülenme sayısını artır
    Listing.objects.filter(id=listing_id).update(view_count=listing.view_count + 1)

    # Benzer İlanlar (Aynı kategoriden)
    similar_listings = Listing.objects.filter(
        category=listing.category,
        is_active=True
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
    """AJAX ile tek tıkla ilanı favorilere ekleme / çıkarma."""
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
        msg = "İlan favorilerinize eklendi!"

    return JsonResponse({
        'status': 'success',
        'is_favorite': is_fav,
        'message': msg,
        'listing_id': listing.id
    })
