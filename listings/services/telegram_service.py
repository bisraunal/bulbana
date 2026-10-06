import os
import requests
import logging

logger = logging.getLogger(__name__)


def send_telegram_notification(chat_id: str, listing) -> bool:
    """
    Kullanıcının Telegram hesabına bulunan yeni ilan için fotoğraflı ve linkli bildirim gönderir.
    %100 ücretsiz Telegram Bot API kullanılır.
    """
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token or not chat_id:
        logger.warning("Telegram bildirimi atılamadı: TELEGRAM_BOT_TOKEN veya chat_id eksik.")
        return False

    # Bildirim Metni (Markdown Formatı)
    caption = (
        f"🎯 *Yeni Eşleşen İlan Bulundu!*\n\n"
        f"📌 *Başlık:* {listing.title}\n"
        f"💰 *Fiyat:* {listing.price}\n"
        f"📍 *Konum:* {listing.location or 'Belirtilmemiş'}\n"
        f"📅 *Tarih:* {listing.published_date or 'Yeni'}\n"
        f"🔍 *Arama Hedefi:* {listing.target.title}\n\n"
        f"🔗 [İlana Gitmek İçin Tıklayın]({listing.listing_url})"
    )

    # Eğer görsel linki varsa fotoğraflı mesaj gönder
    if listing.image_url and listing.image_url.startswith('http'):
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        payload = {
            'chat_id': chat_id,
            'photo': listing.image_url,
            'caption': caption,
            'parse_mode': 'Markdown'
        }
    else:
        # Görsel yoksa normal metin mesajı gönder
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': caption,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': False
        }

    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        if res_data.get('ok'):
            logger.info(f"Telegram bildirimi gönderildi: {chat_id}")
            return True
        else:
            logger.error(f"Telegram API Hatası: {res_data}")
            return False
    except Exception as e:
        logger.error(f"Telegram istek hatası: {str(e)}")
        return False
