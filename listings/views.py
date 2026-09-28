import json
import time
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.contrib import messages
from .models import Category, Listing, UserPreference, ListingInteraction, ChatbotFeedback
from .forms import UserPreferenceForm, QuickSearchForm
from .ai_engine import process_chat_message, generate_negotiation_advice, compare_listings_ai

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
    🤖 AKILLI CHATBOT ASİSTANI (Multi-turn Context & AI Engine)
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

    # Session Hafızası
    session_data = {
        'chat_history': request.session.get('chat_history', []),
        'last_context': request.session.get('last_context', {}),
    }

    result = process_chat_message(
        raw_message=raw_message,
        session_data=session_data,
        user=request.user,
        session_key=session_key
    )

    # Güncellenmiş bağlamı oturuma kaydet
    request.session['last_context'] = result.get('updated_context', {})
    request.session.modified = True

    return JsonResponse({
        'status': 'success',
        'reply': result['reply'],
        'listings': result['listings']
    })


@require_POST
def ai_compare_listings_ajax_view(request):
    """
    ⚖️ İKİ VEYA ÜÇ İLANI YAPAY ZEKA İLE KARŞILAŞTIRMA ENDPOINT'İ
    """
    try:
        body = json.loads(request.body.decode('utf-8'))
        listing_ids = body.get('listing_ids', [])
    except Exception:
        return HttpResponseBadRequest("Geçersiz JSON verisi.")

    if not listing_ids or len(listing_ids) < 2:
        return JsonResponse({'error': 'Karşılaştırma için en az 2 ilan seçmelisiniz.'}, status=400)

    result = compare_listings_ai(listing_ids[:3])
    if 'error' in result:
        return JsonResponse({'error': result['error']}, status=400)

    return JsonResponse({
        'status': 'success',
        'data': result
    })


@require_POST
def ai_generate_negotiation_ajax_view(request, listing_id):
    """
    💬 İLAN ÖZELİNDE AI DESTEKLİ PAZARLIK & TEKLİF MESAJI OLUŞTURUCU
    """
    listing = get_object_or_404(Listing, id=listing_id)
    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
        target_price = body.get('target_price')
    except Exception:
        target_price = None

    advice = generate_negotiation_advice(listing, target_price=target_price)
    return JsonResponse({
        'status': 'success',
        'data': advice
    })


@require_POST
def chatbot_feedback_ajax_view(request):
    """
    👍 / 👎 Chatbot Cevap Puanlama & Geri Bildirim Endpoint'i
    """
    session_key = _get_session_key(request)
    user = request.user if request.user.is_authenticated else None

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
        feedback_type = body.get('feedback', '').strip()
        user_query = body.get('user_query', '').strip()
        bot_reply = body.get('bot_reply', '').strip()
    except Exception:
        return HttpResponseBadRequest("Geçersiz JSON verisi.")

    if feedback_type not in ['positive', 'negative']:
        return JsonResponse({'error': 'Geçersiz geri bildirim türü.'}, status=400)

    feedback = ChatbotFeedback.objects.create(
        user=user,
        session_key=session_key if not user else None,
        feedback_type=feedback_type,
        user_query=user_query,
        bot_reply=bot_reply
    )

    return JsonResponse({
        'status': 'success',
        'message': 'Geri bildiriminiz için teşekkürler! ⭐',
        'id': feedback.id
    })


