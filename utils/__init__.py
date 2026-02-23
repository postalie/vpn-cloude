import requests
import urllib.parse
import base64
from config import GITHUB_PAGE_URL
from .link_encryptor import encrypt_link, create_encrypted_happ_link


def shorten_url(long_url):
    """
    Сокращает ссылку через clck.ru API
    """
    try:
        # Формат который работает у пользователя: без https:// и без кодирования спецсимволов
        clean_url = long_url.replace("https://", "").replace("http://", "")
        api_url = f"https://clck.ru/--?url={clean_url}"

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(api_url, headers=headers, timeout=15)

        if response.status_code == 200:
            result = response.text.strip()
            if result.startswith("http"):
                return result

        # Fallback: стандартный метод с кодированием всего URL
        encoded_url = urllib.parse.quote(long_url)
        api_url_fallback = f"https://clck.ru/--?url={encoded_url}"
        response = requests.get(api_url_fallback, headers=headers, timeout=15)

        if response.status_code == 200:
            result = response.text.strip()
            if result.startswith("http"):
                return result

    except Exception as e:
        print(f"Ошибка сокращения ссылки: {e}")

    return long_url


def encrypt_subscription_happ(subscription_url):
    """
    Шифрует подписку через crypto.happ.su (наш собственный сервис)
    Возвращает зашифрованную строку для deep link (в формате crypt5/...)
    """
    try:
        # Используем наш собственный сервис на основе crypto.happ.su
        encrypted = encrypt_link(subscription_url)
        if encrypted:
            return encrypted
        
        # Fallback: кодируем саму ссылку в base64
        return base64.urlsafe_b64encode(subscription_url.encode()).decode().rstrip('=')
    except Exception as e:
        print(f"Ошибка шифрования через crypto.happ.su: {e}")
        return None


def get_happ_github_link(user_id, sub_uuid, domain_clean):
    """
    Создает ссылку на GitHub Pages с зашифрованной подпиской
    Использует crypto.happ.su для шифрования
    """
    # Используем новую функцию шифрования
    return create_encrypted_happ_link(user_id, sub_uuid, domain_clean)