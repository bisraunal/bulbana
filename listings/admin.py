from django.contrib import admin
from .models import UserProfile, SearchTarget, ScrapedListing


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('username', 'telegram_chat_id', 'created_at')
    search_fields = ('username', 'telegram_chat_id')


@admin.register(SearchTarget)
class SearchTargetAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'is_active', 'last_checked_at', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('title', 'user__username', 'keywords', 'negative_keywords')


@admin.register(ScrapedListing)
class ScrapedListingAdmin(admin.ModelAdmin):
    list_display = ('external_id', 'title', 'price', 'target', 'is_notified', 'created_at')
    list_filter = ('is_notified', 'created_at')
    search_fields = ('external_id', 'title', 'location')
