from django import forms
from .models import SearchTarget, UserProfile


class SearchTargetForm(forms.ModelForm):
    class Meta:
        model = SearchTarget
        fields = [
            'title', 'category', 'city', 'town', 'min_price', 'max_price',
            'search_url', 'keywords', 'negative_keywords', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Örn: Kırmızı Clio 2020+'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'İstanbul'}),
            'town': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Kadıköy'}),
            'min_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '500000'}),
            'max_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '750000'}),
            'search_url': forms.URLInput(attrs={'class': 'form-control'}),
            'keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'kırmızı, hatasız'}),
            'negative_keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ağır hasar, pert'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        min_p = cleaned_data.get('min_price')
        max_p = cleaned_data.get('max_price')

        if min_p and min_p < 0:
            self.add_error('min_price', 'Minimum fiyat negatif olamaz.')

        if max_p and max_p < 0:
            self.add_error('max_price', 'Maksimum fiyat negatif olamaz.')

        if min_p and max_p and min_p > max_p:
            self.add_error('max_price', 'Maksimum fiyat minimum fiyattan küçük olamaz.')

        return cleaned_data


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['username', 'telegram_chat_id']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'telegram_chat_id': forms.TextInput(attrs={'class': 'form-control'}),
        }
