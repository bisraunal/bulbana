from django.db import models


class UserProfile(models.Model):
    """
    Kullanıcı Profili Modeli.
    Basit ve şifresiz giriş için kullanıcı adı ve Telegram bildirim ID'sini tutar.
    """
    username = models.CharField(max_length=50, unique=True, verbose_name="Kullanıcı Adı")
    telegram_chat_id = models.CharField(
        max_length=50, blank=True, null=True, 
        verbose_name="Telegram Chat ID",
        help_text="Telegram botundan bildirim almak için Chat ID bilgisi"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    class Meta:
        verbose_name = "Kullanıcı Profili"
        verbose_name_plural = "Kullanıcı Profilleri"
        ordering = ['-created_at']

    def __str__(self):
        return self.username


class SearchTarget(models.Model):
    """
    Arama Kriteri / Alarm Modeli.
    Sahibinden üzerindeki Vasıta, Emlak ve İkinci El filtrelerini saklar.
    """
    CATEGORY_CHOICES = [
        ('vasita', 'Vasıta (Otomobil / Araç)'),
        ('emlak', 'Emlak (Konut / Kiralık / Satılık)'),
        ('ikinci_el', 'İkinci El ve Alışveriş'),
    ]

    user = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, 
        related_name="targets", verbose_name="Kullanıcı"
    )
    title = models.CharField(
        max_length=150, 
        verbose_name="Alarm Başlığı",
        help_text="Örn: Kırmızı Hasarsız Clio 2020, Kadıköy 2+1 Balkonlu Daire"
    )
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default='vasita',
        verbose_name="Kategori"
    )

    # Lokasyon Filtreleri
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Şehir / İl")
    town = models.CharField(max_length=100, blank=True, null=True, verbose_name="İlçe")

    # Fiyat Sınırları
    min_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Min Fiyat (TL)"
    )
    max_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Max Fiyat (TL)"
    )

    # Sahibinden Arama Linki
    search_url = models.URLField(
        max_length=1000, blank=True, null=True,
        verbose_name="Sahibinden Arama URL'i",
        help_text="Doğrudan filtrelenmiş arama linki veya otomatik üretilen sorgu linki"
    )

    # Tüm özel filtreleri tutan esnek JSON alanı
    filter_criteria = models.JSONField(
        default=dict, blank=True,
        verbose_name="Gelişmiş Kriterler (JSON)"
    )

    # Özel Kelime Filtreleri
    keywords = models.TextField(
        blank=True, null=True,
        verbose_name="Aranan Kelimeler (Pozitif Filtre)",
        help_text="Virgülle ayırın (Örn: kırmızı, hatasız, boyasız)"
    )
    negative_keywords = models.TextField(
        blank=True, null=True,
        verbose_name="İstenmeyen Kelimeler (Negatif Filtre)",
        help_text="Virgülle ayırın (Örn: ağır hasar, pert, taksi çıkması, bodrum kat)"
    )

    is_active = models.BooleanField(default=True, verbose_name="Alarm Aktif mi?")
    last_checked_at = models.DateTimeField(null=True, blank=True, verbose_name="Son Tarama Zamanı")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    class Meta:
        verbose_name = "Arama Kriteri (Alarm)"
        verbose_name_plural = "Arama Kriterleri (Alarmlar)"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def get_badge_list(self):
        """Kartlarda ve bildirimlerde gösterilecek sade özet rozetler."""
        badges = []
        if self.city:
            loc = f"Konum: {self.city}"
            if self.town:
                loc += f" / {self.town}"
            badges.append(loc)

        fc = self.filter_criteria or {}
        if self.category == 'vasita':
            if fc.get('brand'):
                badges.append(f"{fc['brand']} {fc.get('model', '')}".strip())
            if fc.get('year_min') or fc.get('year_max'):
                badges.append(f"{fc.get('year_min', '')}-{fc.get('year_max', '')} Model")
            if fc.get('km_max'):
                badges.append(f"Max {fc['km_max']} KM")
            if fc.get('transmission'):
                badges.append(fc['transmission'])
            if fc.get('fuel'):
                badges.append(fc['fuel'])
            if fc.get('color'):
                badges.append(f"Renk: {fc['color']}")
            if fc.get('damage_status'):
                badges.append(fc['damage_status'])
        elif self.category == 'emlak':
            if fc.get('type'):
                badges.append(fc['type'])
            if fc.get('room_count'):
                badges.append(fc['room_count'])
            if fc.get('m2_min'):
                badges.append(f"Min {fc['m2_min']} m²")
            if fc.get('balcony'):
                badges.append("Balkonlu")
            if fc.get('furnished'):
                badges.append("Eşyalı")

        return badges


class ScrapedListing(models.Model):
    """
    Çekilen ve Eşleşen İlan Modeli.
    Kullanıcının kriterine uyan ve Sahibinden'den tespit edilen ilanları saklar.
    """
    target = models.ForeignKey(
        SearchTarget, on_delete=models.CASCADE, 
        related_name="listings", verbose_name="Arama Hedefi"
    )
    external_id = models.CharField(
        max_length=50,
        verbose_name="Sahibinden İlan No"
    )
    title = models.CharField(max_length=255, verbose_name="İlan Başlığı")
    price = models.CharField(max_length=50, verbose_name="Fiyat")
    location = models.CharField(max_length=150, blank=True, null=True, verbose_name="Konum / Şehir")
    image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Kapak Görseli Linki")
    listing_url = models.URLField(max_length=500, verbose_name="Doğrudan İlan Linki")
    published_date = models.CharField(max_length=100, blank=True, null=True, verbose_name="Yayınlanma Tarihi")
    
    # Ekstra yakalanan özellikler (Yıl, KM, Renk vb.)
    attributes = models.JSONField(default=dict, blank=True, verbose_name="İlan Özellikleri")

    is_notified = models.BooleanField(
        default=False, verbose_name="Bildirim Gönderildi mi?"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sisteme Eklenme Tarihi")

    class Meta:
        verbose_name = "Eşleşen İlan"
        verbose_name_plural = "Eşleşen İlanlar"
        ordering = ['-created_at']
        unique_together = ('target', 'external_id')

    def __str__(self):
        return f"[{self.external_id}] {self.title} - {self.price}"
