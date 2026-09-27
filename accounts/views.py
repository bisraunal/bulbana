from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .forms import UserRegisterForm, UserLoginForm
from listings.models import UserPreference, ListingInteraction, Listing

def register_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Anonim aramaları kullanıcı hesabına aktar (Varsa)
            session_key = request.session.session_key
            if session_key:
                UserPreference.objects.filter(session_key=session_key, user__isnull=True).update(user=user)
                ListingInteraction.objects.filter(session_key=session_key, user__isnull=True).update(user=user)

            login(request, user)
            messages.success(request, f"Hoş geldiniz @{user.username}! Hesabınız başarıyla oluşturuldu.")
            return redirect('profile')
    else:
        form = UserRegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Anonim aramaları ve favorileri kullanıcı hesabına aktar
            session_key = request.session.session_key
            if session_key:
                UserPreference.objects.filter(session_key=session_key, user__isnull=True).update(user=user)
                ListingInteraction.objects.filter(session_key=session_key, user__isnull=True).update(user=user)

            messages.success(request, f"Tekrar hoş geldiniz @{user.username}!")
            next_url = request.GET.get('next') or 'profile'
            return redirect(next_url)
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Başarıyla çıkış yaptınız. Görüşmek üzere!")
    return redirect('home')


@login_required
def profile_view(request):
    # Kullanıcının arayış profilleri
    preferences = UserPreference.objects.filter(user=request.user).select_related('category')
    
    # Kullanıcının favorilediği ilanlar
    favorite_interactions = ListingInteraction.objects.filter(
        user=request.user,
        action_type='favorite'
    ).select_related('listing', 'listing__category')
    
    favorite_listings = [fi.listing for fi in favorite_interactions]

    context = {
        'user': request.user,
        'preferences': preferences,
        'favorite_listings': favorite_listings,
        'pref_count': preferences.count(),
        'fav_count': len(favorite_listings),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
@require_POST
def delete_preference_view(request, pref_id):
    pref = get_object_or_404(UserPreference, id=pref_id, user=request.user)
    title = pref.title
    pref.delete()
    messages.success(request, f"'{title}' arayış profili başarıyla silindi.")
    return redirect('profile')
