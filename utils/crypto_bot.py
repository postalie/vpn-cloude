import aiohttp
from config import CRYPTO_BOT_TOKEN

class CryptoBotClient:
    def __init__(self):
        self.base_url = "https://pay.crypt.bot/api"
        self.token = CRYPTO_BOT_TOKEN
        self.headers = {"Crypto-Pay-API-Token": self.token}

    async def _request(self, method: str, endpoint: str, data: dict = None):
        url = f"{self.base_url}/{endpoint}"
        async with aiohttp.ClientSession() as session:
            try:
                if method == "GET":
                    async with session.get(url, headers=self.headers, params=data) as resp:
                        return await resp.json()
                elif method == "POST":
                    async with session.post(url, headers=self.headers, json=data) as resp:
                        return await resp.json()
            except Exception as e:
                print(f"CryptoBot API Error: {e}")
                return None

    async def create_invoice(self, amount: float, asset: str, description: str = "Top up balance", payload: str = ""):
        """
        Create a new invoice.
        asset: TON, USDT, BTC, TRX
        """
        data = {
            "asset": asset,
            "amount": str(amount),
            "description": description,
            "payload": payload,
            # "allow_comments": False,
            # "allow_anonymous": False
        }
        response = await self._request("POST", "createInvoice", data)
        if response and response.get('ok'):
            return response['result']
        return None

    async def get_invoice(self, invoice_id: int):
        """
        Get invoice details by ID.
        """
        # getInvoices accepts invoice_ids as comma-separated string
        data = {"invoice_ids": str(invoice_id)}
        response = await self._request("GET", "getInvoices", data)
        if response and response.get('ok'):
            items = response['result']['items']
            if items:
                return items[0]
        return None

crypto_bot = CryptoBotClient()
