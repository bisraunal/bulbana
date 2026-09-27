from django.contrib import admin
from .models import Category, Listing, UserPreference, ListingInteraction

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'price', 'city', 'district', 'is_active', 'created_at')
    list_filter = ('category', 'city', 'is_active', 'created_at')
    search_fields = ('title', 'description', 'city', 'district')
    list_editable = ('price', 'is_active')


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'category', 'min_price', 'max_price', 'target_city', 'priority', 'created_at')
    list_filter = ('category', 'priority', 'target_city', 'created_at')
    search_fields = ('title', 'keywords', 'target_city', 'target_district')


@admin.register(ListingInteraction)
class ListingInteractionAdmin(admin.ModelAdmin):
    list_display = ('listing', 'user', 'session_key', 'action_type', 'created_at')
    list_filter = ('action_type', 'created_at')
