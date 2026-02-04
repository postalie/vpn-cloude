import requests
import urllib.parse
import base64
from config import GITHUB_PAGE_URL

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
    Шифрует подписку через API Happ
    Возвращает зашифрованную строку для deep link
    """
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'ru-RU,ru;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'https://happ.shandy.dev',
        'Referer': 'https://happ.shandy.dev/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    }
    
    json_data = {
        'version': 'crypt3',
        'data': subscription_url,
    }
    
    try:
        response = requests.post(
            'https://happ.shandy.dev/api/encode', 
            headers=headers, 
            json=json_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('encryptedData')
        else:
            print(f"Ошибка API Happ: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Ошибка шифрования: {e}")
        return None

def get_happ_github_link(user_id, sub_uuid, domain_clean):
    """
    Создает ссылку на GitHub Pages с зашифрованной подпиской
    """
    subscription_url = f"https://{domain_clean}/add/{user_id}/{sub_uuid}"
    
    encrypted_data = encrypt_subscription_happ(subscription_url)
    
    if not encrypted_data:
        return subscription_url
    
    safe_encrypted = base64.urlsafe_b64encode(encrypted_data.encode()).decode().rstrip("=")
    
    gh_link = f"{GITHUB_PAGE_URL}/{safe_encrypted}"
    
    return gh_link
