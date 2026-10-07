/**
 * BulBana - Akıllı Arayış Chatbot Asistanı (Voice Search & Multi-turn & Chips)
 */

document.addEventListener('DOMContentLoaded', () => {
  const chatbotBtn = document.getElementById('chatbotToggleBtn');
  const chatbotBox = document.getElementById('chatbotBox');
  const chatbotClose = document.getElementById('chatbotClose');
  const chatForm = document.getElementById('chatbotForm');
  const chatInput = document.getElementById('chatbotInput');
  const chatBody = document.getElementById('chatbotBody');
  const voiceBtn = document.getElementById('voiceSearchBtn');
  const chips = document.querySelectorAll('.chat-chip');

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

  // Hızlı Öneri Hapları (Chips)
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chatInput.value = chip.textContent.trim();
      chatForm.dispatchEvent(new Event('submit'));
    });
  });

  // 🎙️ Sesli Arama (Web Speech API)
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'tr-TR';
    recognition.continuous = false;
    recognition.interimResults = false;

    voiceBtn.addEventListener('click', () => {
      voiceBtn.classList.add('btn-danger', 'text-white');
      voiceBtn.classList.remove('btn-outline-secondary');
      chatInput.placeholder = 'Dinliyorum, konuşun...';
      recognition.start();
    });

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      chatInput.value = transcript;
      voiceBtn.classList.remove('btn-danger', 'text-white');
      voiceBtn.classList.add('btn-outline-secondary');
      chatInput.placeholder = 'İstediğin evi, arabayı yaz...';
      chatForm.dispatchEvent(new Event('submit'));
    };

    recognition.onerror = () => {
      voiceBtn.classList.remove('btn-danger', 'text-white');
      voiceBtn.classList.add('btn-outline-secondary');
      chatInput.placeholder = 'İstediğin evi, arabayı yaz...';
    };

    recognition.onend = () => {
      voiceBtn.classList.remove('btn-danger', 'text-white');
      voiceBtn.classList.add('btn-outline-secondary');
      chatInput.placeholder = 'İstediğin evi, arabayı yaz...';
    };
  } else {
    if (voiceBtn) voiceBtn.style.display = 'none';
  }

  let lastUserQuery = '';

  // Mesaj Ekleme
  const appendMessage = (text, isUser = false, listings = []) => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${isUser ? 'chat-msg-user' : 'chat-msg-bot'}`;
    
    let formattedText = text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');

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
            ${item.market_price_diff ? `<div class="text-success small fw-semibold" style="font-size:0.68rem;"><i class="bi bi-tag-fill me-1"></i>${item.market_price_diff}</div>` : ''}
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

    // Bot mesajları için 👍 / 👎 Geri Bildirim Butonları
    if (!isUser) {
      const feedbackWrap = document.createElement('div');
      feedbackWrap.className = 'chat-feedback-wrap';
      feedbackWrap.innerHTML = `
        <span class="text-muted" style="font-size:0.68rem;">Faydalı oldu mu?</span>
        <button type="button" class="btn-feedback btn-fb-up" title="Faydalı buldum">
          👍 Evet
        </button>
        <button type="button" class="btn-feedback btn-fb-down" title="Yetersiz veya hatalı">
          👎 Hayır
        </button>
      `;

      const btnUp = feedbackWrap.querySelector('.btn-fb-up');
      const btnDown = feedbackWrap.querySelector('.btn-fb-down');

      const sendFeedback = async (type, btnActive, btnInactive) => {
        btnActive.classList.add(type === 'positive' ? 'active-positive' : 'active-negative');
        btnInactive.disabled = true;
        btnActive.disabled = true;
        btnActive.innerHTML = type === 'positive' ? '👍 Teşekkürler!' : '👎 Kaydedildi';

        try {
          await fetch('/api/chatbot/feedback/', {
            method: 'POST',
            headers: {
              'X-CSRFToken': getCsrfToken(),
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              feedback: type,
              user_query: lastUserQuery,
              bot_reply: text
            })
          });
        } catch (e) {
          console.error('Feedback send error:', e);
        }
      };

      btnUp.addEventListener('click', () => sendFeedback('positive', btnUp, btnDown));
      btnDown.addEventListener('click', () => sendFeedback('negative', btnDown, btnUp));

      msgDiv.appendChild(feedbackWrap);
    }

    chatBody.appendChild(msgDiv);
    chatBody.scrollTop = chatBody.scrollHeight;
  };

  // Form Gönderimi
  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const userText = chatInput.value.trim();
    if (!userText) return;

    lastUserQuery = userText;
    appendMessage(userText, true);
    chatInput.value = '';

    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'chat-msg chat-msg-bot text-muted small fst-italic';
    loadingDiv.id = 'chatLoading';
    loadingDiv.innerHTML = '<i class="bi bi-hourglass-split me-1"></i> Sahibinden verileri & tesciller taranıyor...';
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

