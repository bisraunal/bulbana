from django import forms
from .models import UserPreference, Category

class UserPreferenceForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="-- Kategori Seçiniz --",
        widget=forms.Select(attrs={
            'class': 'form-select form-select-lg',
            'id': 'pref-category'
        }),
        label="Ne Arıyorsunuz?"
    )

    class Meta:
        model = UserPreference
        fields = [
            'title', 'category', 'min_price', 'max_price',
            'target_city', 'target_district', 'keywords', 'priority'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Örn: Kadıköy 2+1 Ev, Şehir İçi Otomatik Araba'
            }),
            'min_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Örn: 15000'
            }),
            'max_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Örn: 30000'
            }),
            'target_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Örn: İstanbul, Ankara, İzmir'
            }),
            'target_district': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Örn: Kadıköy, Çankaya, Karşıyaka'
            }),
            'keywords': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Örn: balkon, metro, kedi dostu, otomatik, 16gb ram'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
        labels = {
            'title': 'Arayışınıza Bir Başlık Verin',
            'min_price': 'Minimum Bütçe (TL)',
            'max_price': 'Maksimum Bütçe (TL)',
            'target_city': 'Hedef Şehir',
            'target_district': 'Hedef İlçe / Bölge',
            'keywords': 'Olmazsa Olmaz Özellikler (Virgülle)',
            'priority': 'Eşleştirme Önceliğiniz',
        }
        help_texts = {
            'keywords': 'Aramanızda öne çıkmasını istediğiniz kelimeleri virgülle ayırarak yazabilirsiniz.',
        }

    def clean(self):
        cleaned_data = super().clean()
        min_p = cleaned_data.get('min_price')
        max_p = cleaned_data.get('max_price')

        if min_p and min_p < 0:
            self.add_error('min_price', 'Minimum bütçe negatif olamaz.')

        if max_p and max_p < 0:
            self.add_error('max_price', 'Maksimum bütçe negatif olamaz.')

        if min_p and max_p and min_p > max_p:
            self.add_error('max_price', 'Maksimum bütçe minimum bütçeden küçük olamaz.')

        return cleaned_data


class QuickSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'İlan başlığı, açıklama veya anahtar kelime arayın...'
        })
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Tüm Kategoriler",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Şehir (Örn: İstanbul)'
        })
    )
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Maksimum Fiyat'
        })
    )
