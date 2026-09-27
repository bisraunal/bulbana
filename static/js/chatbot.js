/**
 * BulBana - Akıllı Arayış Chatbot Asistanı (Client JS)
 */

document.addEventListener('DOMContentLoaded', () => {
  const chatbotBtn = document.getElementById('chatbotToggleBtn');
  const chatbotBox = document.getElementById('chatbotBox');
  const chatbotClose = document.getElementById('chatbotClose');
  const chatForm = document.getElementById('chatbotForm');
  const chatInput = document.getElementById('chatbotInput');
  const chatBody = document.getElementById('chatbotBody');

  if (!chatbotBtn || !chatbotBox || !chatForm) return;

  const getCsrfToken = () => {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
  };

  // Aç / Kapa
  chatbotBtn.addEventListener('click', () => {
    chatbotBox.classList.toggle('active');
    if (chatbotBox.classList.contains('active')) {
      chatInput.focus();
    }
  });

  chatbotClose.addEventListener('click', () => {
    chatbotBox.classList.remove('active');
  });

  // Mesaj Ekleme Yardımcısı
  const appendMessage = (text, isUser = false, listings = []) => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${isUser ? 'chat-msg-user' : 'chat-msg-bot'}`;
    
    // Markdown bold formatı (**bold** -> <strong>bold</strong>)
    const formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    msgDiv.innerHTML = `<div>${formattedText}</div>`;

    if (listings && listings.length > 0) {
      const cardsWrap = document.createElement('div');
      cardsWrap.className = 'mt-2 d-flex flex-column gap-2';

      listings.forEach(item => {
        const card = document.createElement('div');
        card.className = 'chatbot-card-mini shadow-sm';
        card.innerHTML = `
          <img src="${item.image_url || 'https://via.placeholder.com/60x50'}" alt="${item.title}">
          <div style="flex-grow:1; min-width:0;">
            <div class="fw-bold text-truncate small">${item.title}</div>
            <div class="d-flex justify-content-between align-items-center mt-1">
              <span class="text-primary fw-bold small">${item.price}</span>
              <span class="badge bg-success small" style="font-size:0.7rem;">%${item.match_score} Uyum</span>
            </div>
            <div class="mt-1 d-flex justify-content-between align-items-center">
              <span class="text-muted" style="font-size:0.7rem;">${item.location}</span>
              <a href="${item.detail_url}" class="btn btn-sm btn-dark py-0 px-2 fw-bold" style="font-size:0.7rem;">İncele &rarr;</a>
            </div>
          </div>
        `;
        cardsWrap.appendChild(card);
      });

      msgDiv.appendChild(cardsWrap);
    }

    chatBody.appendChild(msgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
  };

  // Form Gönderme
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const userText = chatInput.value.trim();
    if (!userText) return;

    // Kullanıcı mesajını göster
    appendMessage(userText, true);
    chatInput.value = '';

    // Yükleniyor baloncuğu
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-msg chat-msg-bot text-muted small fst-italic';
    loadingDiv.id = 'chatLoading';
    loadingDiv.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Sahibinden verileri taranıyor...';
    chatBody.appendChild(loadingDiv);
    chatBody.scrollTop = chatBody.scrollHeight;

    try {
      const response = await fetch('/api/chatbot/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCsrfToken(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: userText })
      });

      const loadingEl = document.getElementById('chatLoading');
      if (loadingEl) loadingEl.remove();

      if (response.ok) {
        const data = await response.json();
        appendMessage(data.reply, false, data.listings);
      } else {
        const errorData = await response.json().catch(() => ({}));
        appendMessage(errorData.error || 'Bir hata oluştu, lütfen tekrar deneyin.', false);
      }
    } catch (err) {
      const loadingEl = document.getElementById('chatLoading');
      if (loadingEl) loadingEl.remove();
      appendMessage('Sunucuyla bağlantı kurulamadı.', false);
    }
  });
});
