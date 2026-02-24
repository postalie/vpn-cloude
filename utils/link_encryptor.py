"""
Собственный сервис шифрования ссылок
Работает на основе crypto.happ.su API
"""
import requests
from bs4 import BeautifulSoup
import base64
import hashlib
import urllib.parse


def get_dl_link(url: str) -> str:
    """
    Получает ссылку для скачивания/перенаправления через crypto.happ.su
    """
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'ru-RU,ru;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://crypto.happ.su',
        'referer': 'https://crypto.happ.su/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
    }
    
    data = {
        'url': url,
    }
    
    try:
        response = requests.post('https://crypto.happ.su/', headers=headers, data=data, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        link = soup.find('a', id='dl')
        
        if link and 'href' in link.attrs:
            return link['href']
    except Exception as e:
        print(f"Ошибка получения dl ссылки: {e}")
    print(f"ссылка от крипто хапп {link}")
    return None


def encrypt_link(url: str) -> str:
    """
    Шифрует ссылку через crypto.happ.su
    Возвращает зашифрованную ссылку (без happ://crypt5/)
    """
    dl_link = get_dl_link(url)

    if dl_link:
        # Формат: happ://crypt5/<encrypted_data> (URL-encoded)
        if dl_link.startswith('happ://crypt5/'):
            encrypted = dl_link.replace('happ://crypt5/', '')
            return encrypted
        # Формат: happ://crypt3/<encrypted_data> (URL-encoded)
        elif dl_link.startswith('happ://crypt3/'):
            encrypted = dl_link.replace('happ://crypt3/', '')
            return encrypted
        # Формат: https://crypto.happ.su/dl#<encrypted_data>
        elif '#' in dl_link:
            encrypted = dl_link.split('#', 1)[1]
            return encrypted

    return None


def create_encrypted_happ_link(user_id: int, sub_uuid: str, domain: str) -> str:
    from config import GITHUB_PAGE_URL

    subscription_url = f"https://{domain}/add/{user_id}/{sub_uuid}"
    encrypted = encrypt_link(subscription_url)

    if encrypted:
        encrypted_with_prefix = f"crypt5/{encrypted}"
        
        # БЕЗ unquote! Просто кодируем строку как есть
        safe_encrypted = base64.urlsafe_b64encode(
            encrypted_with_prefix.encode('utf-8')
        ).decode().rstrip('=')
        
        return f"{GITHUB_PAGE_URL}/{safe_encrypted}"

    safe_encrypted = base64.urlsafe_b64encode(
        subscription_url.encode('utf-8')
    ).decode().rstrip('=')
    return f"{GITHUB_PAGE_URL}/{safe_encrypted}"


def generate_short_hash(url: str, length: int = 8) -> str:
    """
    Генерирует короткий хеш для ссылки
    """
    hash_object = hashlib.md5(url.encode())
    return hash_object.hexdigest()[:length]

# subscription_url = f"https://cloudevpn.cfd/add/1699548539/68b678ad-52ed-4c48-a49c-b430235c6d2c"
# dl_link = get_dl_link(subscription_url)
# print(dl_link)