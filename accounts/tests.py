from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse

class AccountsAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="test_kullanici",
            email="test@example.com",
            password="guvenliparola123"
        )

    def test_user_login_success(self):
        """Kullanıcı girişinin başarılı olduğunu doğrular."""
        response = self.client.post(reverse('login'), {
            'username': 'test_kullanici',
            'password': 'guvenliparola123'
        })
        self.assertEqual(response.status_code, 302)

    def test_user_login_wrong_password(self):
        """Hatalı parolada giriş yapılmadığını ve form hatası döndüğünü doğrular."""
        response = self.client.post(reverse('login'), {
            'username': 'test_kullanici',
            'password': 'yanlisparola'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)

    def test_user_registration(self):
        """Yeni kullanıcı kaydını test eder."""
        response = self.client.post(reverse('register'), {
            'username': 'yeni_kullanici',
            'email': 'yeni@example.com',
            'password': 'guvenliparola456',
            'password_confirm': 'guvenliparola456'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='yeni_kullanici').exists())
