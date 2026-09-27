from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Kategori Adı")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    icon = models.CharField(max_length=50, default="bi-tag", verbose_name="İkon (Bootstrap/Heroicon)")
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
    source_url = models.URLField(max_length=500, blank=True, verbose_name="Sahibinden / Kaynak İlan Linki")
    
    # Esnek özellikler: {"oda_sayisi": "2+1", "balkon": True, "vites": "Otomatik", "yakit": "Benzin", "ram": "16GB"}
    specs = models.JSONField(default=dict, blank=True, verbose_name="Teknik Özellikler / Parametreler")
    
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


class UserPreference(models.Model):
    PRIORITY_CHOICES = [
        ('balanced', 'Dengeli (Fiyat + Konum + Özellikler)'),
        ('price', 'Öncelik: Uygun Fiyat & Bütçe'),
        ('location', 'Öncelik: Konum & Lokasyon'),
        ('specs', 'Öncelik: Donanım & Özel Nitelikler'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="preferences", verbose_name="Kullanıcı")
    session_key = models.CharField(max_length=100, null=True, blank=True, verbose_name="Misafir Oturumu")
    
    title = models.CharField(max_length=150, verbose_name="Arayış Başlığı (Örn: Kadıköy 2+1 Ev)")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="user_preferences", verbose_name="Aranan Kategori")
    
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Minimum Bütçe (TL)")
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Maksimum Bütçe (TL)")
    
    target_city = models.CharField(max_length=100, blank=True, verbose_name="Hedef İl")
    target_district = models.CharField(max_length=100, blank=True, verbose_name="Hedef İlçe")
    
    # Aranılan anahtar kelimeler / etiketler (virgülle ayrılmış: "balkon, metro, kedi, temiz")
    keywords = models.CharField(max_length=255, blank=True, verbose_name="Önemli Anahtar Kelimeler (virgülle)")
    
    # Tercih edilen ek özellikler
    preferred_specs = models.JSONField(default=dict, blank=True, verbose_name="Tercih Edilen Parametreler")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='balanced', verbose_name="Öncelik Durumu")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Güncellenme Tarihi")

    class Meta:
        verbose_name = "Kullanıcı Arayış Profili"
        verbose_name_plural = "Kullanıcı Arayış Profilleri"
        ordering = ['-created_at']

    def __str__(self):
        owner = f"@{self.user.username}" if self.user else f"Misafir ({self.session_key[:8]}...)"
        return f"{owner} -> {self.title} ({self.category.name})"

    def calculate_match(self, listing):
        """
        Kullanıcı arayış kriterleri ile verilen ilanı karşılaştırır.
        Dönüş: (match_score: int 0-100, positive_reasons: list, notes: list)
        """
        # Kategori uyumsuzsa direkt 0 puan
        if self.category_id != listing.category_id:
            return 0, [], ["Kategori uyuşmuyor"]

        score = 100
        positive_reasons = []
        notes = []

        # 1. Fiyat Değerlendirmesi (Ağırlık: %40)
        listing_price = float(listing.price)
        max_p = float(self.max_price) if self.max_price else None
        min_p = float(self.min_price) if self.min_price else None

        if max_p and min_p:
            if min_p <= listing_price <= max_p:
                positive_reasons.append(f"🎯 Tam bütçenize uygun ({listing.formatted_price})")
            elif listing_price < min_p:
                positive_reasons.append(f"💰 Bütçenizin altında cazip fiyat")
            else:
                diff_pct = ((listing_price - max_p) / max_p) * 100
                penalty = min(35, int(diff_pct * 1.2))
                score -= penalty
                notes.append(f"⚠️ Bütçenizi %{int(diff_pct)} aşıyor")
        elif max_p:
            if listing_price <= max_p:
                positive_reasons.append(f"🎯 Bütçe sınırınızın altında ({listing.formatted_price})")
            else:
                diff_pct = ((listing_price - max_p) / max_p) * 100
                penalty = min(35, int(diff_pct * 1.2))
                score -= penalty
                notes.append(f"⚠️ Bütçenizi %{int(diff_pct)} aşıyor")

        # 2. Lokasyon Değerlendirmesi (Ağırlık: %30)
        if self.target_city:
            if self.target_city.lower() == listing.city.lower():
                if self.target_district:
                    if self.target_district.lower() == listing.district.lower():
                        positive_reasons.append(f"📍 Hedef konumunuzda ({listing.district}, {listing.city})")
                    else:
                        score -= 15
                        notes.append(f"Farklı ilçe ({listing.district})")
                else:
                    positive_reasons.append(f"📍 Aradığınız şehirde ({listing.city})")
            else:
                score -= 30
                notes.append(f"Farklı şehir ({listing.city})")

        # 3. Anahtar Kelimeler & Açıklama Taraması (Ağırlık: %20)
        if self.keywords:
            kw_list = [k.strip().lower() for k in self.keywords.split(",") if k.strip()]
            full_text = f"{listing.title} {listing.description} {' '.join(str(v) for v in listing.specs.values())}".lower()
            
            matched_kws = [kw for kw in kw_list if kw in full_text]
            if matched_kws:
                positive_reasons.append(f"✨ Aradığınız kriterler mevcut: {', '.join(matched_kws)}")
                score += min(10, len(matched_kws) * 4)
            elif kw_list:
                score -= 10

        # 4. Öncelik Ayarlaması
        if self.priority == 'price' and positive_reasons and any("bütçe" in r.lower() or "fiyat" in r.lower() for r in positive_reasons):
            score += 5
        elif self.priority == 'location' and positive_reasons and any("konum" in r.lower() for r in positive_reasons):
            score += 5

        # Skor sınırlandırma (0 - 100 arası)
        final_score = max(5, min(100, int(score)))
        return final_score, positive_reasons, notes


class ListingInteraction(models.Model):
    ACTION_CHOICES = [
        ('favorite', 'Favoriye Eklendi'),
        ('dismiss', 'İlgilenmiyorum / Gizle'),
        ('clicked', 'İlana Göz Atıldı'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name="listing_interactions", verbose_name="Kullanıcı")
    session_key = models.CharField(max_length=100, null=True, blank=True, verbose_name="Misafir Oturumu")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="interactions", verbose_name="İlan")
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Etkileşim Türü")
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

    def __str__(self):
        owner = f"@{self.user.username}" if self.user else f"Misafir ({self.session_key[:8]}...)"
        return f"{owner} - {self.get_action_type_display()} -> {self.listing.title}"
