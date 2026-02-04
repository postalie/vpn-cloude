export default {
    async fetch(request, env) {
        try {
            const url = new URL(request.url);
            const pathParts = url.pathname.split('/').filter(Boolean);

            // 1. ПРОКСИРОВАНИЕ API ЗАПРОСОВ (для TMA)
            if (pathParts[0] === 'api') {
                const apiPath = url.pathname;
                const railwayApiUrl = `https://vpn-cloude-production.up.railway.app${apiPath}${url.search}`;

                const newHeaders = new Headers(request.headers);
                newHeaders.set("X-API-Key", "CloudeVpnVOIDAPI_1488");

                const apiResponse = await fetch(railwayApiUrl, {
                    method: request.method,
                    headers: newHeaders,
                    body: request.method !== 'GET' && request.method !== 'HEAD' ? await request.arrayBuffer() : null
                });

                // Возвращаем ответ от бэкенда с сохранением CORS
                const responseHeaders = new Headers(apiResponse.headers);
                responseHeaders.set("Access-Control-Allow-Origin", "*");

                return new Response(apiResponse.body, {
                    status: apiResponse.status,
                    headers: responseHeaders
                });
            }

            let uuid = null;

            // 2. ОПРЕДЕЛЯЕМ UUID ДЛЯ ПОДПИСОК
            if (pathParts.length >= 2 && pathParts[0] === 'sub') {
                uuid = pathParts[1];
            } else if (pathParts.length >= 2 && pathParts[0] === 'add') {
                uuid = pathParts[2];
            } else if (pathParts.length >= 2 && /^\d+$/.test(pathParts[0])) {
                uuid = pathParts[1];
            }

            // Если это не API и не подписка — отдаем файлы сайта (TMA)
            if (!uuid) {
                return env.ASSETS.fetch(request);
            }

            // ФУНКЦИЯ ДЛЯ ОТВЕТА С ОШИБКОЙ
            const sendErrorConfig = (message) => {
                const fakeConfig = `vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none#${message}`;
                const base64Config = btoa(String.fromCharCode(...new TextEncoder().encode(fakeConfig)));

                return new Response(base64Config, {
                    headers: {
                        "Content-Type": "text/plain; charset=utf-8",
                        "Profile-Update-Interval": "3",
                        "Cache-Control": "no-cache"
                    }
                });
            };

            // ЗАПРОС К БЭКЕНДУ
            const railwayUrl = `https://vpn-cloude-production.up.railway.app/api/sub/${uuid}`;
            let response;

            try {
                // Пакетная передача ВСЕХ заголовков (для передачи модели устройства)
                const newHeaders = new Headers(request.headers);
                newHeaders.set("X-API-Key", "CloudeVpnVOIDAPI_1488");

                response = await fetch(railwayUrl, { headers: newHeaders });
            } catch (e) {
                return sendErrorConfig("🚨 Ошибка сервера. Попробуйте позже");
            }

            // Если UUID не найден на бэкенде
            if (response.status === 404 || !response.ok) {
                return sendErrorConfig("🚨 Подписка недоступна");
            }

            const subInfo = response.headers.get("Subscription-Userinfo") || "";

            // ПРОВЕРКА СРОКА ГОДНОСТИ
            if (subInfo.includes("expire=")) {
                const expireMatch = subInfo.match(/expire=(\d+)/);
                if (expireMatch) {
                    const expireTimestamp = parseInt(expireMatch[1]) * 1000;
                    if (Date.now() > expireTimestamp) {
                        return sendErrorConfig("❌ Подписка истекла");
                    }
                }
            }

            // УСПЕШНЫЙ ОТВЕТ
            const data = await response.text();

            return new Response(data, {
                headers: {
                    "Content-Type": "text/plain; charset=utf-8",
                    "Subscription-Userinfo": subInfo,
                    "Profile-Title": "☁️ CloudVPN",
                    "Profile-Update-Interval": "1",
                    "Support-Url": "https://t.me/CloudeVPNbot",
                    "Profile-Web-Page-Url": "https://t.me/soldenchain",
                    "announce": "ㅤㅤㅤㅤㅤНе работает VPN? нажми на 🔄 для обновленияㅤㅤㅤㅤㅤ📲 LTE обходы в конце списка",
                    "Cache-Control": "no-cache"
                }
            });

        } catch (globalE) {
            return new Response(`Global Error: ${globalE.message}`, { status: 500 });
        }
    }
};