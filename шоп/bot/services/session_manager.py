import os
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

from bot.config import config


class SessionManager:
    """Менеджер Telegram сессий"""

    def __init__(self):
        self.clients: dict[str, TelegramClient] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_session_path(self, phone: str) -> str:
        """Путь к файлу сессии"""
        safe_phone = phone.replace("+", "").replace(" ", "")
        return os.path.join(config.SESSIONS_DIR, safe_phone)

    async def create_session(self, phone: str) -> TelegramClient:
        """Создание новой сессии (требует код подтверждения)"""
        session_path = self._get_session_path(phone)
        client = TelegramClient(session_path, config.API_ID, config.API_HASH)
        await client.connect()
        return client

    async def send_code(self, phone: str) -> tuple[TelegramClient, str]:
        """Отправка кода подтверждения"""
        client = await self.create_session(phone)
        sent = await client.send_code_request(phone)
        self.clients[phone] = client
        return client, sent.phone_code_hash

    async def sign_in(self, phone: str, code: str, phone_code_hash: str,
                      password: str = None) -> tuple[bool, str]:
        """Авторизация по коду"""
        client = self.clients.get(phone)
        if not client:
            return False, "Сессия не найдена"

        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            session_path = self._get_session_path(phone)
            return True, session_path + ".session"
        except Exception as e:
            if "Two-steps verification" in str(e) or "password" in str(e).lower():
                if password:
                    try:
                        await client.sign_in(password=password)
                        session_path = self._get_session_path(phone)
                        return True, session_path + ".session"
                    except Exception as e2:
                        return False, f"Ошибка 2FA: {e2}"
                return False, "NEED_2FA"
            return False, str(e)

    async def sign_in_2fa(self, phone: str, password: str) -> tuple[bool, str]:
        """Авторизация с 2FA"""
        client = self.clients.get(phone)
        if not client:
            return False, "Сессия не найдена"

        try:
            await client.sign_in(password=password)
            session_path = self._get_session_path(phone)
            return True, session_path + ".session"
        except Exception as e:
            return False, str(e)

    async def load_session(self, session_file: str) -> TelegramClient | None:
        """Загрузка существующей сессии"""
        session_path = session_file.replace(".session", "")
        if not os.path.exists(session_file):
            return None

        client = TelegramClient(session_path, config.API_ID, config.API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await client.disconnect()
            return None

        return client

    async def get_client(self, session_file: str) -> TelegramClient | None:
        """Получение клиента по файлу сессии (с кешированием)"""
        if session_file in self.clients:
            client = self.clients[session_file]
            if client.is_connected():
                return client

        client = await self.load_session(session_file)
        if client:
            self.clients[session_file] = client
        return client

    def get_lock(self, session_file: str) -> asyncio.Lock:
        """Получение лока для сессии (для предотвращения конфликтов)"""
        if session_file not in self._locks:
            self._locks[session_file] = asyncio.Lock()
        return self._locks[session_file]

    async def disconnect_all(self):
        """Отключение всех клиентов"""
        for client in self.clients.values():
            try:
                await client.disconnect()
            except:
                pass
        self.clients.clear()

    async def disconnect(self, session_file: str):
        """Отключение конкретного клиента"""
        if session_file in self.clients:
            try:
                await self.clients[session_file].disconnect()
            except:
                pass
            del self.clients[session_file]


session_manager = SessionManager()
