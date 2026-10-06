from django.db import models


class UserProfile(models.Model):
    """
    Kullanici Profili Modeli.
    Basit ve sifresiz giris icin kullanici adi ve Telegram bildirim ID'sini tutar.
    """
    username = models.CharField(max_length=50, unique=True, verbose_name="Kullanici Adi")
    telegram_chat_id = models.CharField(
        max_length=50, blank=True, null=True, 
        verbose_name="Telegram Chat ID",
        help_text="Telegram botundan bildirim almak icin Chat ID bilgisi"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Olusturulma Tarihi")

    class Meta:
        verbose_name = "Kullanici Profili"
        verbose_name_plural = "Kullanici Profilleri"
        ordering = ['-created_at']

    def __str__(self):
        return self.username


class SearchTarget(models.Model):
    """
    Arama Kriteri / Alarm Modeli.
    Sahibinden uzerindeki Vasita, Emlak ve Ikinci El filtrelerini saklar.
    """
    CATEGORY_CHOICES = [
        ('vasita', 'Vasita (Otomobil / Arac)'),
        ('emlak', 'Emlak (Konut / Kiralik / Satilik)'),
        ('ikinci_el', 'Ikinci El ve Alisveris'),
    ]

    user = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, 
        related_name="targets", verbose_name="Kullanici"
    )
    title = models.CharField(
        max_length=150, 
        verbose_name="Alarm Basligi",
        help_text="Orn: Kirmizi Hasarsiz Clio 2020, Kadikoy 2+1 Balkonlu Daire"
    )
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default='vasita',
        verbose_name="Kategori"
    )

    # Lokasyon Filtreleri
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sehir / Il")
    town = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ilce")

    # Fiyat Sinirlari
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
        help_text="Dogrudan filtrelenmis arama linki veya otomatik uretilen sorgu linki"
    )

    # Tum ozel filtreleri tutan esnek JSON alani
    filter_criteria = models.JSONField(
        default=dict, blank=True,
        verbose_name="Gelismis Kriterler (JSON)"
    )

    # Ozel Kelime Filtreleri
    keywords = models.TextField(
        blank=True, null=True,
        verbose_name="Aranan Kelimeler (Pozitif Filtre)",
        help_text="Virgulle ayirin (Orn: kirmizi, hatasiz, boyasiz)"
    )
    negative_keywords = models.TextField(
        blank=True, null=True,
        verbose_name="Istenmeyen Kelimeler (Negatif Filtre)",
        help_text="Virgulle ayirin (Orn: agir hasar, pert, taksi cikmasi, bodrum kat)"
    )

    is_active = models.BooleanField(default=True, verbose_name="Alarm Aktif mi?")
    last_checked_at = models.DateTimeField(null=True, blank=True, verbose_name="Son Tarama Zamani")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Olusturulma Tarihi")

    class Meta:
        verbose_name = "Arama Kriteri (Alarm)"
        verbose_name_plural = "Arama Kriterleri (Alarmlar)"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def get_badge_list(self):
        """Kartlarda ve bildirimlerde gosterilecek sade ozet rozetler."""
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
                badges.append(f"Min {fc['m2_min']} m2")
            if fc.get('balcony'):
                badges.append("Balkonlu")
            if fc.get('furnished'):
                badges.append("Esyali")

        return badges


class ScrapedListing(models.Model):
    """
    Cekilen ve Eslesen Ilan Modeli.
    Kullanicinin kriterine uyan ve Sahibinden'den tespit edilen ilanlari saklar.
    """
    target = models.ForeignKey(
        SearchTarget, on_delete=models.CASCADE, 
        related_name="listings", verbose_name="Arama Hedefi"
    )
    external_id = models.CharField(
        max_length=50,
        verbose_name="Sahibinden Ilan No"
    )
    title = models.CharField(max_length=255, verbose_name="Ilan Basligi")
    price = models.CharField(max_length=50, verbose_name="Fiyat")
    location = models.CharField(max_length=150, blank=True, null=True, verbose_name="Konum / Sehir")
    image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Kapak Gorseli Linki")
    listing_url = models.URLField(max_length=500, verbose_name="Dogrudan Ilan Linki")
    published_date = models.CharField(max_length=100, blank=True, null=True, verbose_name="Yayinlanma Tarihi")
    
    # Ekstra yakalanan ozellikler (Yil, KM, Renk vb.)
    attributes = models.JSONField(default=dict, blank=True, verbose_name="Ilan Ozellikleri")

    is_notified = models.BooleanField(
        default=False, verbose_name="Bildirim Gonderildi mi?"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sisteme Eklenme Tarihi")

    class Meta:
        verbose_name = "Eslesen Ilan"
        verbose_name_plural = "Eslesen Ilanlar"
        ordering = ['-created_at']
        unique_together = ('target', 'external_id')

    def __str__(self):
        return f"[{self.external_id}] {self.title} - {self.price}"
