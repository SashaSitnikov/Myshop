import aiohttp
from typing import Optional

from bot.config import config


class CryptoBotService:
    """Сервис для работы с CryptoBot API"""

    def __init__(self):
        self.token = config.CRYPTOBOT_TOKEN
        if config.CRYPTOBOT_IS_TESTNET:
            self.base_url = "https://testnet-pay.crypt.bot/api"
        else:
            self.base_url = "https://pay.crypt.bot/api"

    @property
    def headers(self):
        return {"Crypto-Pay-API-Token": self.token}

    async def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Выполнить запрос к API"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/{endpoint}"
            async with session.request(method, url, headers=self.headers, **kwargs) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    raise Exception(data.get("error", {}).get("name", "Unknown error"))
                return data.get("result", {})

    async def get_me(self) -> dict:
        """Получить информацию о приложении"""
        return await self._request("GET", "getMe")

    async def get_balance(self) -> list:
        """Получить баланс"""
        return await self._request("GET", "getBalance")

    async def create_invoice(
        self,
        amount: float,
        currency: str = "USDT",
        description: str = None,
        payload: str = None,
        paid_btn_name: str = "callback",
        paid_btn_url: str = None,
        expires_in: int = 3600
    ) -> dict:
        """
        Создать счёт на оплату

        Args:
            amount: Сумма
            currency: Валюта (USDT, TON, BTC и т.д.)
            description: Описание платежа
            payload: Данные для идентификации (до 4096 символов)
            paid_btn_name: Тип кнопки после оплаты (callback, viewItem, openChannel, openBot)
            paid_btn_url: URL для кнопки
            expires_in: Время жизни счёта в секундах

        Returns:
            dict с информацией о счёте
        """
        params = {
            "asset": currency,
            "amount": str(amount),
        }

        if description:
            params["description"] = description
        if payload:
            params["payload"] = payload
        if paid_btn_name and paid_btn_url:
            params["paid_btn_name"] = paid_btn_name
            params["paid_btn_url"] = paid_btn_url
        if expires_in:
            params["expires_in"] = expires_in

        return await self._request("POST", "createInvoice", json=params)

    async def get_invoices(
        self,
        asset: str = None,
        invoice_ids: list[int] = None,
        status: str = None,
        offset: int = 0,
        count: int = 100
    ) -> dict:
        """Получить список счетов"""
        params = {"offset": offset, "count": count}
        if asset:
            params["asset"] = asset
        if invoice_ids:
            params["invoice_ids"] = ",".join(map(str, invoice_ids))
        if status:
            params["status"] = status

        return await self._request("GET", "getInvoices", params=params)

    async def get_invoice(self, invoice_id: int) -> Optional[dict]:
        """Получить информацию о конкретном счёте"""
        result = await self.get_invoices(invoice_ids=[invoice_id])
        items = result.get("items", [])
        return items[0] if items else None

    async def check_invoice_paid(self, invoice_id: int) -> bool:
        """Проверить, оплачен ли счёт"""
        invoice = await self.get_invoice(invoice_id)
        return invoice and invoice.get("status") == "paid"

    async def delete_invoice(self, invoice_id: int) -> bool:
        """Удалить счёт"""
        try:
            await self._request("POST", "deleteInvoice", json={"invoice_id": invoice_id})
            return True
        except:
            return False

    def get_invoice_url(self, invoice: dict) -> str:
        """Получить URL для оплаты"""
        if config.CRYPTOBOT_IS_TESTNET:
            return invoice.get("bot_invoice_url") or invoice.get("pay_url", "")
        return invoice.get("bot_invoice_url") or invoice.get("pay_url", "")


cryptobot_service = CryptoBotService()
