from flask import Flask, Response, jsonify
import base64
from urllib.parse import urlparse, parse_qs, unquote
import re

app = Flask(__name__)

def b64(text):
    return "base64:" + base64.b64encode(text.encode()).decode()


VLESS_KEYS = """
ss://1488SOSIHUY1488==@1:443#─── Универсальные 🔥
vless://9cb2d5c5-c5e0-409b-ad3b-7c057b7971b1@37.139.42.234:4443?security=reality&encryption=none&pbk=-kDgSQgouE56cqDIDwgCco1LNQ-8q61WllL5egDI0yI&headerType=none&fp=chrome&allowinsecure=0&type=tcp&sni=yandex.ru&sid=6670#🇷🇺 🍌 Ютуб без рекламы
vless://519f23e6-cc05-462e-8bdf-2da3c9178d19@cloudav.noped.online:443?mode=multi&security=reality&encryption=none&authority=&pbk=sIBL9uK_8LpZIng7IltNLUAEDYqxEr8kA7IKINxxdwI&fp=random&spx=%2Fpath&allowinsecure=0&type=grpc&serviceName=example-grpc&sni=cloudav.noped.online&sid=9999#🇦🇹 Австрия
vless://eee5cbcd-9dbe-434f-b669-8eaed97d9660@gb01-vlr01.tcp-reset-club.net:22443?security=reality&encryption=none&pbk=mLmBhbVFfNuo2eUgBh6r9-5Koz9mUCn3aSzlR6IejUg&headerType=none&fp=chrome&spx=%2F&allowinsecure=0&type=tcp&flow=xtls-rprx-vision&sni=hls-svod.itunes.apple.com&sid=8453e5fd9af927#🇬🇧 Великобритания
vless://9e8b0d0b-0f30-43cc-8c0e-8acfe1001717@de1.vpnreal.ru:443?security=reality&encryption=none&pbk=xUBjC2vNXBrDnJ3rVvQl2CYPvugp3VeVC5NN9ukRojU&headerType=none&fp=chrome&allowinsecure=0&type=tcp&flow=xtls-rprx-vision&sni=eh.vk.com&sid=e3ebde1f3c9c2b7c#🇩🇪+Германия
vless://f79ef1b4-5486-42e0-8cbc-280739f61f91@kz.cloudevpn.cfd:443?security=reality&encryption=none&pbk=llaiqC-oIhL_bjc236FPq26LSn7IVhIa4cIC6OVytws&headerType=none&fp=chrome&spx=%2F&allowinsecure=0&type=tcp&flow=xtls-rprx-vision&sni=hls-svod.itunes.apple.com&sid=31#🇰🇿 Казахстан
vless://b82d7a2a-e02b-4980-b368-d7bbcf857775@nl.cloudevpn.cfd:443?security=reality&encryption=none&pbk=mLmBhbVFfNuo2eUgBh6r9-5Koz9mUCn3aSzlR6IejUg&headerType=none&fp=chrome&spx=%2F&allowinsecure=0&type=tcp&flow=xtls-rprx-vision&sni=hls-svod.itunes.apple.com&sid=175d#🇳🇱 Нидерланды
vless://b82d7a2a-e02b-4980-b368-d7bbcf857775@pol.cloudevpn.cfd:443?security=reality&encryption=none&pbk=mLmBhbVFfNuo2eUgBh6r9-5Koz9mUCn3aSzlR6IejUg&headerType=none&fp=chrome&spx=%2F&allowinsecure=0&type=tcp&flow=xtls-rprx-vision&sni=hls-svod.itunes.apple.com&sid=f79448a30d#🇵🇱 Польша
vless://b67212ce-0210-4179-8092-bcea1325c3dc@tur.cloudevpn.cfd:8080?mode=gun&security=none&encryption=none&type=grpc&serviceName=vless#🇹🇷 Турция
vless://b0aa22ee-b085-45aa-a448-831aa4ef1573@us-api.sbrf-cdn342.ru:4241?security=reality&encryption=none&pbk=-8Dc8Dm5YzxVvllu8W5Uc7N9rq27_A3McxYXArNyJQs&headerType=none&type=tcp&flow=xtls-rprx-vision&sni=dropbox.com&sid=0a381e1fa219#🇺🇸 США
vless://b0aa22ee-b085-45aa-a448-831aa4ef1573@fi.cloudevpn.cfd:8443?security=reality&encryption=none&pbk=ATRoFPpyxH23kPCa9dKyLTT_gQ_eAkNtVVRlvPaxBjQ&headerType=none&type=tcp&flow=xtls-rprx-vision&sni=holodos.vk.com&sid=111111#🇫🇮 Финляндия
vless://b0aa22ee-b085-45aa-a448-831aa4ef1573@fr.cloudevpn.cfd:4241?security=reality&encryption=none&pbk=-8Dc8Dm5YzxVvllu8W5Uc7N9rq27_A3McxYXArNyJQs&headerType=none&type=tcp&flow=xtls-rprx-vision&sni=dropbox.com&sid=0a381e1fa219#🇫🇷 Франция
vless://b82d7a2a-e02b-4980-b368-d7bbcf857775@swi.cloudevpn.cfd:443?security=reality&encryption=none&pbk=mLmBhbVFfNuo2eUgBh6r9-5Koz9mUCn3aSzlR6IejUg&headerType=none&fp=chrome&spx=%2F&allowinsecure=0&type=tcp&flow=xtls-rprx-vision&sni=hls-svod.itunes.apple.com&sid=31#🇨🇭 Швейцария
vless://b67212ce-0210-4179-8092-bcea1325c3dc@swe.cloudevpn.cfd:8080?mode=gun&security=none&encryption=none&type=grpc&serviceName=vless#🇸🇪 Швеция
vless://b82d7a2a-e02b-4980-b368-d7bbcf857775@es.cloudevpn.cfd:443?security=reality&encryption=none&pbk=mLmBhbVFfNuo2eUgBh6r9-5Koz9mUCn3aSzlR6IejUg&headerType=none&fp=chrome&spx=%2F&allowinsecure=0&type=tcp&flow=xtls-rprx-vision&sni=hls-svod.itunes.apple.com&sid=31#🇪🇪 Эстония
vless://b0aa22ee-b085-45aa-a448-831aa4ef1573@es2.cloudevpn.cfd:7443?security=reality&encryption=none&pbk=XguLRlc-hWqFhf8-KTxtCE434F6e4Hiqoc5cTBpLxnE&headerType=none&type=tcp&flow=xtls-rprx-vision&sni=stackoverflow.com&sid=111111#🇪🇪 Эстония | 🕹️ Игровой
ss://1488SOSIHUY11488==@1:443#─── Обходы 🔥
vless://56322908-df4d-4285-be22-b8370b3b36b4@cdn.meowworld.ru:443?mode=auto&path=%2F&security=tls&encryption=none&allowinsecure=0&type=xhttp#🇷🇺 LTE | Обход #1 💥
vless://6d39596c-b569-4a61-86c3-28cfb83a4c95@79.137.175.56:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=m.vk.ru&fp=chrome&security=reality&pbk=Qddpg8luihgzgx4g4uMJklXzlrMCd8L1igJSWrRUvSc&sid=8f222b3475800821#🇷🇺 LTE | Обход #2
vless://56322908-df4d-4285-be22-b8370b3b36b4@cdn.meowworld.ru:443?mode=auto&path=%2F&security=tls&encryption=none&allowinsecure=0&type=xhttp#🇷🇺 LTE | Обход #3
vless://ab942643-a3be-4773-9a60-0de1111f9e28@ob.trustsub.ru:443?security=reality&encryption=none&pbk=SxOInP7OQXH1aCyT36KS7AQf0ITe8pCJbQWcVAtpQ08&headerType=none&fp=chrome&spx=%2FUvPxhgggZShSIDu&allowinsecure=0&type=tcp&sni=tesla.com&sid=09fdc14e554e9c#🇷🇺 LTE | Обход #4
vless://ab942643-a3be-4773-9a60-0de1111f9e28@ob3.trustsub.ru:443?security=reality&encryption=none&pbk=sb1UxS7Y60smrewjKvGYo9psOF_Foh29UNWcwyIn3Fc&headerType=none&fp=chrome&spx=%2FATofU2vqlXJdiwa&allowinsecure=0&type=tcp&sni=www.nvidia.com&sid=c3dd419a#🇷🇺 LTE | Обход #5
vless://9e8b0d0b-0f30-43cc-8c0e-8acfe1001717@meg1.vpnreal.ru:8443?security=reality&encryption=none&pbk=xUBjC2vNXBrDnJ3rVvQl2CYPvugp3VeVC5NN9ukRojU&headerType=none&fp=chrome&allowinsecure=0&type=tcp&flow=xtls-rprx-vision&sni=eh.vk.com&sid=e3ebde1f3c9c2b7c#🇳🇱 LTE | Обход #6
vless://b0aa22ee-b085-45aa-a448-831aa4ef1573@essencion.sbrf-cdn342.ru:443?security=reality&encryption=none&pbk=OCRYYq4e92sQ-wWFRX6WX9pdvuFBWOqybLhpSiv3nFA&headerType=none&type=tcp&flow=xtls-rprx-vision&sni=ads.x5.ru&sid=111111#🇳🇱 LTE | Обход #7
vless://72fb3bd4-75dd-488a-9af7-c391321ecfcc@79.137.175.44:8443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=m.vk.ru&fp=random&security=reality&pbk=zr8_rtHm86s_G1gfRwNtunStGngYZSdYkA3PyBFXpDg&sid=04bf0403f96e5b4b#🇪🇸 LTE | Обход #8
vless://b67212ce-0210-4179-8092-bcea1325c3dc@balance-fi.elix.rip:42198?security=reality&encryption=none&pbk=DvKMFkm82Jkp6Jk_7pXYb0fMXq1MsLMNxDeQfcCSbEA&headerType=none&fp=chrome&type=tcp&flow=xtls-rprx-vision&sni=download.max.ru&sid=ab12cd34#🇫🇮 LTE | Обход #9
vless://b67212ce-0210-4179-8092-bcea1325c3dc@ru-msk.elix.rip:8080?mode=gun&security=none&encryption=none&type=grpc&serviceName=vless#🇷🇺 LTE | Обход #10
vless://ad5d8d51-18f4-451b-9c01-7baff1d9b244@51.250.73.139:12001/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=api-maps.yandex.ru&fp=chrome&security=reality&pbk=0a3d38cwnQfUM7EqjEinf1XUZyKdzgiuRMayO3LcYl0&sid=#🇩🇪 LTE | Обход #11
vless://c0c3dc30-4ed9-e13d-50e8-0a84a84815e3@146.185.210.127:7443/?type=grpc&encryption=none&flow=&sni=eh.vk.com&fp=chrome&security=reality&pbk=90gAm3EU2v0llWwt9XH0e70DL_UlL4Ud5nEXeLBEEw8&sid=2eb27292#🇬🇧 LTE | Обход #12
vless://f625ba3b-93dc-4a87-9e69-f39a2f16ff98@81.200.151.79:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=m.vk.com&fp=chrome&security=reality&pbk=FkmYFobwxLMLEktYXywmjthuEYCZggITsxwPNasTKUg&sid=a76ea384b29a4f79#🇷🇺 LTE | Обход #13
vless://f60a9d13-1d10-4ce5-ae8a-79e0daeaa064@79.137.175.56:51102/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=m.vk.ru&fp=chrome&security=reality&pbk=Qddpg8luihgzgx4g4uMJklXzlrMCd8L1igJSWrRUvSc&sid=1929ef620e9b34f5#🇵🇱 LTE | Обход #14
vless://30eb83b9-1782-4848-a37c-dec8bbf4c62f@95.163.250.22:6443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=ads.x5.ru&fp=chrome&security=reality&pbk=NQHJZ88t5mdW_YiTrgzsCwoJO0tgK2CP8Cd1HP-_6Gw&sid=bad5722c72a038#🇫🇮 LTE | Обход #15
vless://467aa349-5a10-4f23-98d7-dd5d836dcbe5@37.139.33.57:8443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=m.vk.ru&fp=chrome&security=reality&pbk=_CjW0Khlrr5z5oc9Oy6-w2ZEanz-zMBktVn5EOX9oTM&sid=4ffc99daad0f261f#🇮🇹 LTE | Обход #16
vless://3c5c4ccc-b502-42cb-8c42-cfa714db4767@84.23.52.70:443/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=m.vk.ru&fp=chrome&security=reality&pbk=7zd9mJilgjOrg_ohtw23Vmio-pdnYqeP_r-kiWt87Cg&sid=2715592069f36fe7#🇭🇺 LTE | Обход #17
vless://ad5d8d51-18f4-451b-9c01-7baff1d9b244@51.250.73.139:12001/?type=tcp&encryption=none&flow=xtls-rprx-vision&sni=api-maps.yandex.ru&security=reality&pbk=0a3d38cwnQfUM7EqjEinf1XUZyKdzgiuRMayO3LcYl0&sid=#🇩🇪 LTE | Обход #18
vless://12cb9911-a48d-4147-85cc-68dd678e94c6@64.188.64.59:443/?type=tcp&encryption=none&flow=&sni=yandex.ru&fp=chrome&security=reality&pbk=iv8v94q9qxkMw5WSUc0obloyLVFNTsfyy9Y3FaGlj1k&sid=efd29b2d25#🇩🇪 LTE | Обход #19
vless://b67212ce-0210-4179-8092-bcea1325c3dc@balance.elix.rip:7443?security=reality&encryption=none&pbk=DvKMFkm82Jkp6Jk_7pXYb0fMXq1MsLMNxDeQfcCSbEA&headerType=none&fp=qq&type=tcp&flow=xtls-rprx-vision&sni=5post-gate.x5.ru&sid=fcba98#🇪🇪 LTE | Обход #20
""".strip()

@app.route("/subscription")
def subscription():
    headers = {
        "profile-title": b64("🌥 Cloud VPN"),
        "announce": b64(
            "🌥 Облако свободного интернета без ограничений\n"
            "⚠️ LTE обходы в конце списка ⚠️"
        ),
        "support-url": "https://t.me/avestb",
        "profile-web-page-url": "https://cloudevpn.cfd",
        "subscription-userinfo": "upload=0; download=0; total=0; expire=4102444800",
        "profile-update-interval": "1",
        "hide-settings": "1"
    }
    
    return Response(VLESS_KEYS, headers=headers, mimetype="text/plain")


if __name__ == "__main__":
    app.run(port=8080)
