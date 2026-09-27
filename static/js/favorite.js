/**
 * BulBana - Favoriye Ekleme / Çıkarma AJAX Etkileşimi
 */

document.addEventListener('DOMContentLoaded', () => {
  const getCsrfToken = () => {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
  };

  const showToast = (message, isSuccess = true) => {
    const toastEl = document.getElementById('appToast');
    const toastMsgEl = document.getElementById('toastMessage');
    if (!toastEl || !toastMsgEl) return;

    toastMsgEl.innerHTML = `
      <i class="bi ${isSuccess ? 'bi-check-circle-fill text-success' : 'bi-info-circle-fill text-warning'}"></i>
      <span>${message}</span>
    `;

    const bsToast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 3000 });
    bsToast.show();
  };

  // Kart üzerindeki kalp butonları
  document.querySelectorAll('.btn-favorite-icon').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();

      const listingId = btn.getAttribute('data-listing-id');
      if (!listingId) return;

      try {
        const response = await fetch(`/api/listings/${listingId}/favorite/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json',
          }
        });

        if (response.ok) {
          const data = await response.json();
          const icon = btn.querySelector('i');
          
          if (data.is_favorite) {
            btn.classList.add('active');
            if (icon) {
              icon.classList.remove('bi-heart');
              icon.classList.add('bi-heart-fill', 'text-danger');
            }
          } else {
            btn.classList.remove('active');
            if (icon) {
              icon.classList.remove('bi-heart-fill', 'text-danger');
              icon.classList.add('bi-heart');
            }
          }

          showToast(data.message, true);
        } else {
          showToast('İşlem sırasında bir hata oluştu.', false);
        }
      } catch (err) {
        console.error('Favorite AJAX Error:', err);
        showToast('Bağlantı hatası oluştu.', false);
      }
    });
  });

  // Detay sayfasındaki büyük buton
  document.querySelectorAll('.btn-favorite-icon-standalone').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.preventDefault();

      const listingId = btn.getAttribute('data-listing-id');
      if (!listingId) return;

      try {
        const response = await fetch(`/api/listings/${listingId}/favorite/`, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCsrfToken(),
            'Content-Type': 'application/json',
          }
        });

        if (response.ok) {
          const data = await response.json();
          const icon = btn.querySelector('i');
          const textSpan = btn.querySelector('.fav-text');

          if (data.is_favorite) {
            btn.classList.add('active');
            if (icon) {
              icon.classList.remove('bi-heart');
              icon.classList.add('bi-heart-fill');
            }
            if (textSpan) textSpan.textContent = 'Favorilerden Çıkar';
          } else {
            btn.classList.remove('active');
            if (icon) {
              icon.classList.remove('bi-heart-fill');
              icon.classList.add('bi-heart');
            }
            if (textSpan) textSpan.textContent = 'Favorilere Kaydet';
          }

          showToast(data.message, true);
        }
      } catch (err) {
        console.error('Standalone Favorite Error:', err);
      }
    });
  });
});
