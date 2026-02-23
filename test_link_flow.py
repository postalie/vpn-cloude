"""
Тест цепочки шифрования ссылки для Happ
"""
import base64
import requests
from bs4 import BeautifulSoup

# Тестовые данные
USER_ID = 273761139
SUB_UUID = "16f86b13-5b18-44bf-a1a2-6d330d5c1783"
DOMAIN = "cloudevpn.cfd"
GITHUB_PAGE_URL = "https://h1tezz.github.io/cloud"

print("=" * 60)
print("ТЕСТ ЦЕПОЧКИ ШИФРОВАНИЯ ССЫЛКИ ДЛЯ HAPP")
print("=" * 60)

# 1. Создаём исходную ссылку
subscription_url = f"https://{DOMAIN}/add/{USER_ID}/{SUB_UUID}"
print(f"\n[1] ИСХОДНАЯ ССЫЛКА:")
print(f"    {subscription_url}")

# 2. Шифруем через crypto.happ.su
print(f"\n[2] ШИФРОВАНИЕ ЧЕРЕЗ crypto.happ.su...")
headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'accept-language': 'ru-RU,ru;q=0.9',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://crypto.happ.su',
    'referer': 'https://crypto.happ.su/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
}

data = {'url': subscription_url}

try:
    response = requests.post('https://crypto.happ.su/', headers=headers, data=data, timeout=15)
    print(f"    Статус ответа: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    link = soup.find('a', id='dl')
    
    if link and 'href' in link.attrs:
        dl_link = link['href']
        print(f"    DL ssylka (do decode): {dl_link[:100]}...")

        # Dekodiruem URL
        import urllib.parse
        dl_link = urllib.parse.unquote(dl_link)
        print(f"    DL ssylka (posle decode): {dl_link[:100]}...")

        # Izvlekaem zashifrovannuyu chast
        encrypted = None
        if dl_link.startswith('happ://crypt5/'):
            encrypted = dl_link.replace('happ://crypt5/', '')
            print(f"    Format: happ://crypt5/...")
        elif dl_link.startswith('happ://crypt3/'):
            encrypted = dl_link.replace('happ://crypt3/', '')
            print(f"    Format: happ://crypt3/...")
        elif '#' in dl_link:
            encrypted = dl_link.split('#', 1)[1]
            print(f"    Format: #...")

        if encrypted:
            print(f"    [3] ZASHIFROVANNYE DANNYE (bez prefiksa):")
            print(f"        {encrypted[:100]}...")
            
            # 4. Добавляем префикс crypt5/
            encrypted_with_prefix = f"crypt5/{encrypted}"
            print(f"\n[3.5] ДОБАВЛЯЕМ ПРЕФИКС crypt5/:")
            print(f"        {encrypted_with_prefix[:100]}...")
            
            # 5. Кодируем в base64 для GitHub
            safe_encrypted = base64.urlsafe_b64encode(encrypted_with_prefix.encode()).decode().rstrip('=')
            print(f"\n[4] BASE64 ДЛЯ GITHUB:")
            print(f"    {safe_encrypted[:100]}...")
            
            # 6. Создаём ссылку GitHub Pages
            github_link = f"{GITHUB_PAGE_URL}/{safe_encrypted}"
            print(f"\n[5] ССЫЛКА GITHUB PAGES:")
            print(f"    {github_link}")
            
            # 7. Сокращаем через clck.ru
            print(f"\n[6] СОКРАЩЕНИЕ ЧЕРЕЗ clck.ru...")
            clean_url = github_link.replace("https://", "")
            api_url = f"https://clck.ru/--?url={clean_url}"
            
            clck_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            clck_response = requests.get(api_url, headers=clck_headers, timeout=15)
            if clck_response.status_code == 200:
                short_link = clck_response.text.strip()
                print(f"    СОКРАЩЁННАЯ ССЫЛКА: {short_link}")
            else:
                print(f"    Ошибка clck.ru: {clck_response.status_code}")
                short_link = github_link
            
            # 8. Финальный результат
            print(f"\n[7] ИТОГ:")
            print(f"    Пользователь получает: {short_link}")
            print(f"\n[8] ЧТО ПРОИСХОДИТ ПРИ КЛИКЕ:")
            print(f"    1. clck.ru redirect na GitHub")
            print(f"    2. GitHub (404.html) decodes base64 -> 'crypt5/{encrypted[:50]}...'")
            print(f"    3. GitHub sozdaet happ://crypt5/{encrypted[:50]}...")
            print(f"    4. Happ rasshifrovyvaet i podklyuchaetsya")
            
            # 9. Проверка 404.html логики
            print(f"\n[9] PROVERKA 404.html LOGIKI:")
            print(f"    VHODNOY path: /{safe_encrypted[:80]}...")
            
            # Декодируем обратно
            padded = safe_encrypted
            while len(padded) % 4 != 0:
                padded += '='
            
            decoded = base64.urlsafe_b64decode(padded).decode()
            print(f"    Posle dekodirovaniya: {decoded[:80]}...")
            
            if decoded.startswith('crypt5/'):   
                print(f"    OK - Eto crypt5 dannye")
                print(f"    404.html sozdast: happ://{decoded[:50]}...")
            elif decoded.startswith("happ://crypt"):
                print(f"    OK - Eto happ://crypt ssylka")
                print(f"    404.html sozdast: happ://{decoded.replace('happ://', '')[:50]}...")
            elif "add/" in decoded:
                print(f"    OK - Eto pryamoy add/ URL")
                print(f"    404.html sozdast: happ://{decoded[:50]}...")
            else:
                print(f"    WARNING - Neizvestnyy format")
            
        else:
            print(f"    ERROR: V ssylke net # s zashifrovannymi dannymi")
    else:
        print(f"    ERROR: Ne naydeno ssylki s id='dl'")
        print(f"    HTML otvet: {response.text[:500]}")
        
except Exception as e:
    print(f"    ERROR: {e}")

print("\n" + "=" * 60)
