from django.db import models


class UserProfile(models.Model):
    """
    Kullanıcı Profili Modeli.
    Basit ve şifresiz/hızlı giriş için kullanıcı adı ve Telegram bildirim ID'sini tutar.
    """
    username = models.CharField(max_length=50, unique=True, verbose_name="Kullanıcı Adı")
    telegram_chat_id = models.CharField(
        max_length=50, blank=True, null=True, 
        verbose_name="Telegram Chat ID",
        help_text="Telegram botundan bildirim almak için Chat ID'niz"
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
    Kullanıcının Sahibinden'de taranmasını istediği araç, emlak veya ürün kriterlerini tutar.
    """
    CATEGORY_CHOICES = [
        ('vasita', '🚗 Vasıta (Otomobil / Araç)'),
        ('emlak', '🏠 Emlak (Konut / Kiralık / Satılık)'),
        ('ikinci_el', '📱 İkinci El & Alışveriş'),
    ]

    user = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, 
        related_name="targets", verbose_name="Kullanıcı"
    )
    title = models.CharField(
        max_length=150, 
        verbose_name="Alarm Başlığı",
        help_text="Örn: Kırmızı Hasarsız Clio, Kadıköy 2+1 Daire"
    )
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default='vasita',
        verbose_name="Kategori"
    )
    search_url = models.URLField(
        max_length=500,
        verbose_name="Sahibinden Arama URL'i",
        help_text="Sahibinden'de arama yapıp kopyaladığınız filtrelenmiş arama linki"
    )
    min_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Min Fiyat (TL)"
    )
    max_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name="Max Fiyat (TL)"
    )
    keywords = models.TextField(
        blank=True, null=True,
        verbose_name="Aranan Kelimeler (Pozitif Filtre)",
        help_text="Virgülle ayırın (Örn: kırmızı, otomatik, boyasız, balkonlu)"
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


class ScrapedListing(models.Model):
    """
    Çekilen & Eşleşen İlan Modeli.
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
    is_notified = models.BooleanField(
        default=False, verbose_name="Bildirim Gönderildi mi?"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sisteme Eklenme Tarihi")

    class Meta:
        verbose_name = "Eşleşen İlan"
        verbose_name_plural = "Eşleşen İlanlar"
        ordering = ['-created_at']
        # Aynı hedef için aynı ilan numarasının mükerrer eklenmesini önler
        unique_together = ('target', 'external_id')

    def __str__(self):
        return f"[{self.external_id}] {self.title} - {self.price}"
