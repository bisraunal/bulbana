import re
import urllib.parse
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kategori Adı")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    icon = models.CharField(max_length=50, default="bi-tag", verbose_name="İkon")
    description = models.TextField(blank=True, verbose_name="Açıklama")

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ['name']

    def __str__(self):
        return self.name


class Listing(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="listings", verbose_name="Kategori")
    title = models.CharField(max_length=250, verbose_name="İlan Başlığı")
    description = models.TextField(blank=True, verbose_name="İlan Açıklaması")
    price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Fiyat (TL)")
    city = models.CharField(max_length=100, verbose_name="İl")
    district = models.CharField(max_length=100, verbose_name="İlçe")
    neighborhood = models.CharField(max_length=100, blank=True, verbose_name="Mahalle / Semt")
    image_url = models.URLField(max_length=500, blank=True, verbose_name="İlan Görseli URL")
    source_url = models.URLField(max_length=500, blank=True, verbose_name="Sahibinden İlan Linki")
    
    # Teknik Özellikler
    specs = models.JSONField(default=dict, blank=True, verbose_name="Teknik Parametreler")
    
    # 🛡️ DOĞRULUK VE TESCİL SİSTEMİ
    is_verified = models.BooleanField(default=True, verbose_name="Tescilli / Doğrulanmış İlan mı?")
    verification_score = models.PositiveSmallIntegerField(default=95, verbose_name="Doğruluk & Güven Puanı (%0-100)")
    verification_badges = models.JSONField(
        default=list, blank=True, 
        verbose_name="Tescil Rozetleri (Örn: Tapu Doğrulandı, Ekspertiz Onaylı, Piyasa Fiyatı Test Edildi)"
    )
    market_price_diff = models.CharField(
        max_length=100, blank=True, default="Piyasa Fiyatında", 
        verbose_name="Piyasa Fiyat Kıyaslaması (Örn: Piyasanın %10 Altında)"
    )

    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    view_count = models.PositiveIntegerField(default=0, verbose_name="Görüntülenme Sayısı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    class Meta:
        verbose_name = "İlan"
        verbose_name_plural = "İlanlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.category.name}] {self.title} - {self.price:,.0f} TL"

    @property
    def formatted_price(self):
        return f"{self.price:,.0f} TL".replace(",", ".")

    @property
    def sahibinden_link(self):
        """
        Sahibinden üzerinde garantili ve hatasız çalışan doğrudan arama/ilan linki üretir.
        """
        if self.source_url and "sahibinden.com" in self.source_url:
            return self.source_url
        query = f"{self.title} {self.city} {self.district}".strip()
        encoded = urllib.parse.quote_plus(query)
        return f"https://www.sahibinden.com/arama?query_text={encoded}"


class UserPreference(models.Model):
    PRIORITY_CHOICES = [
        ('balanced', 'Dengeli (Fiyat + Konum + Özellikler)'),
        ('price', 'Öncelik: Uygun Fiyat & Bütçe'),
        ('location', 'Öncelik: Konum & Lokasyon'),
        ('specs', 'Öncelik: Donanım & Nitelikler'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="preferences", verbose_name="Kullanıcı")
    session_key = models.CharField(max_length=100, null=True, blank=True, verbose_name="Misafir Oturumu")
    
    title = models.CharField(max_length=150, verbose_name="Arayış Başlığı")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name="user_preferences", verbose_name="Aranan Kategori")
    
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Min Bütçe")
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Max Bütçe")
    
    target_city = models.CharField(max_length=100, blank=True, verbose_name="Hedef İl")
    target_district = models.CharField(max_length=100, blank=True, verbose_name="Hedef İlçe")
    
    keywords = models.CharField(max_length=255, blank=True, verbose_name="Anahtar Kelimeler")
    preferred_specs = models.JSONField(default=dict, blank=True, verbose_name="Parametreler")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='balanced', verbose_name="Öncelik")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    class Meta:
        verbose_name = "Kullanıcı Arayış Profili"
        verbose_name_plural = "Kullanıcı Arayış Profilleri"
        ordering = ['-created_at']

    def calculate_match(self, listing):
        def normalize_tr(text):
            if not text:
                return ""
            t = str(text).lower()
            replacements = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'İ': 'i'}
            for k, v in replacements.items():
                t = t.replace(k, v)
            return t

        score = 80
        positive_reasons = []
        notes = []

        if self.category and self.category_id != listing.category_id:
            score -= 30
            notes.append("Farklı kategori")
        elif self.category:
            positive_reasons.append(f"📁 Doğru kategori: {listing.category.name}")

        listing_price = float(listing.price)
        max_p = float(self.max_price) if self.max_price else None
        min_p = float(self.min_price) if self.min_price else None

        if max_p and min_p:
            if min_p <= listing_price <= max_p:
                score += 15
                positive_reasons.append(f"💰 Tam bütçenize uygun ({listing.formatted_price})")
            elif listing_price < min_p:
                positive_reasons.append(f"🏷️ Bütçenizin altında hesaplı fiyat")
            else:
                diff_pct = ((listing_price - max_p) / max_p) * 100
                score -= min(40, int(diff_pct * 0.8))
                notes.append(f"⚠️ Bütçenizi %{int(diff_pct)} aşıyor")
        elif max_p:
            if listing_price <= max_p:
                score += 15
                positive_reasons.append(f"💰 Bütçenizin altında ({listing.formatted_price})")
            else:
                diff_pct = ((listing_price - max_p) / max_p) * 100
                score -= min(40, int(diff_pct * 0.8))
                notes.append(f"⚠️ Bütçenizi %{int(diff_pct)} aşıyor")

        target_city_norm = normalize_tr(self.target_city)
        target_dist_norm = normalize_tr(self.target_district)
        listing_city_norm = normalize_tr(listing.city)
        listing_dist_norm = normalize_tr(listing.district)

        if target_city_norm:
            if target_city_norm in listing_city_norm or listing_city_norm in target_city_norm:
                if target_dist_norm and (target_dist_norm in listing_dist_norm or listing_dist_norm in target_dist_norm):
                    score += 15
                    positive_reasons.append(f"📍 Birebir hedef konumunuzda ({listing.district}, {listing.city})")
                else:
                    score += 8
                    positive_reasons.append(f"📍 Aradığınız şehirde ({listing.city})")
            else:
                score -= 20
                notes.append(f"Farklı şehir ({listing.city})")

        if self.keywords:
            raw_kws = [k.strip() for k in re.split(r'[,; ]+', self.keywords) if k.strip()]
            full_text_norm = normalize_tr(f"{listing.title} {listing.description} {' '.join(str(v) for v in listing.specs.values())}")
            
            matched = []
            for kw in raw_kws:
                kw_norm = normalize_tr(kw)
                if len(kw_norm) >= 2 and kw_norm in full_text_norm:
                    matched.append(kw)

            if matched:
                score += min(20, len(matched) * 8)
                positive_reasons.append(f"✨ Kriterler bulundu: {', '.join(matched)}")

        if listing.is_verified:
            positive_reasons.append(f"🛡️ %{listing.verification_score} Doğrulanmış & Tescilli İlan")

        final_score = max(10, min(100, int(score)))
        return final_score, positive_reasons, notes


class ListingInteraction(models.Model):
    ACTION_CHOICES = [
        ('favorite', 'Favoriye Eklendi'),
        ('dismiss', 'İlgilenmiyorum'),
        ('clicked', 'İlana Göz Atıldı'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="listing_interactions", verbose_name="Kullanıcı")
    session_key = models.CharField(max_length=100, null=True, blank=True, verbose_name="Misafir Oturumu")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="interactions", verbose_name="İlan")
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Etkileşim")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "İlan Etkileşimi"
        verbose_name_plural = "İlan Etkileşimleri"
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'listing', 'action_type'],
                condition=Q(user__isnull=False),
                name='unique_user_listing_action'
            ),
            models.UniqueConstraint(
                fields=['session_key', 'listing', 'action_type'],
                condition=Q(session_key__isnull=False),
                name='unique_session_listing_action'
            ),
        ]
