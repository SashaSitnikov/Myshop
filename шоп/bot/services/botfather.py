import asyncio
from telethon import TelegramClient
from telethon.tl.types import Message

from bot.services.session_manager import session_manager

BOTFATHER_USERNAME = "BotFather"


class BotFatherService:
    """Сервис для взаимодействия с @BotFather"""

    def __init__(self):
        self.timeout = 10

    async def _send_and_wait(self, client: TelegramClient, text: str,
                              wait_for_buttons: bool = False) -> Message | None:
        """Отправить сообщение и дождаться ответа"""
        await client.send_message(BOTFATHER_USERNAME, text)
        await asyncio.sleep(1)

        messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
        if messages:
            return messages[0]
        return None

    async def _select_bot(self, client: TelegramClient, bot_username: str) -> bool:
        """Выбрать бота из списка"""
        # BotFather присылает список ботов как кнопки
        await asyncio.sleep(0.5)
        messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)

        if messages and messages[0].buttons:
            for row in messages[0].buttons:
                for btn in row:
                    if bot_username.lower() in btn.text.lower():
                        await btn.click()
                        await asyncio.sleep(1)
                        return True

        # Или просто отправить username
        await client.send_message(BOTFATHER_USERNAME, f"@{bot_username}")
        await asyncio.sleep(1)
        return True

    async def execute_action(self, session_file: str, bot_username: str,
                             action: str, value: str = None,
                             photo_path: str = None) -> tuple[bool, str]:
        """
        Выполнить действие в BotFather

        Действия:
        - setname: Изменить имя бота
        - setdescription: Изменить описание
        - setabouttext: Изменить About текст
        - setuserpic: Изменить аватарку (нужен photo_path)
        - setdescriptionpic: Изменить картинку описания
        - setcommands: Установить команды
        - deletebot: Удалить бота
        - setinline: Включить/выключить inline режим
        - setjoingroups: Разрешить добавление в группы
        - setprivacy: Изменить privacy режим
        - setinlinefeedback: Inline feedback
        """
        lock = session_manager.get_lock(session_file)

        async with lock:
            client = await session_manager.get_client(session_file)
            if not client:
                return False, "Не удалось подключиться к сессии"

            try:
                # Отправляем команду
                command = f"/{action}"
                await self._send_and_wait(client, command)
                await asyncio.sleep(0.5)

                # Выбираем бота
                await self._select_bot(client, bot_username)
                await asyncio.sleep(1)

                # Отправляем значение или фото
                if photo_path:
                    await client.send_file(BOTFATHER_USERNAME, photo_path)
                elif value:
                    if value.upper() == "SKIP" or value == "/empty":
                        await client.send_message(BOTFATHER_USERNAME, "/empty")
                    else:
                        await client.send_message(BOTFATHER_USERNAME, value)

                await asyncio.sleep(1)

                # Получаем ответ
                messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
                if messages:
                    response = messages[0].text or "Готово"
                    response_lower = response.lower()

                    # Проверяем на ошибки
                    error_keywords = ["sorry", "invalid", "error", "failed", "can't", "cannot",
                                     "ошибка", "неверн", "не удалось", "нельзя", "must be"]
                    for keyword in error_keywords:
                        if keyword in response_lower:
                            return False, response

                    return True, response

                return True, "Команда выполнена"

            except Exception as e:
                return False, str(e)

    # ============ Конкретные действия ============

    async def set_name(self, session_file: str, bot_username: str, name: str) -> tuple[bool, str]:
        """Изменить имя бота"""
        return await self.execute_action(session_file, bot_username, "setname", name)

    async def set_description(self, session_file: str, bot_username: str, description: str) -> tuple[bool, str]:
        """Изменить Description"""
        return await self.execute_action(session_file, bot_username, "setdescription", description)

    async def set_about(self, session_file: str, bot_username: str, about: str) -> tuple[bool, str]:
        """Изменить About"""
        return await self.execute_action(session_file, bot_username, "setabouttext", about)

    async def set_userpic(self, session_file: str, bot_username: str, photo_path: str) -> tuple[bool, str]:
        """Изменить аватарку"""
        return await self.execute_action(session_file, bot_username, "setuserpic", photo_path=photo_path)

    async def set_description_pic(self, session_file: str, bot_username: str, photo_path: str) -> tuple[bool, str]:
        """Изменить картинку описания"""
        return await self.execute_action(session_file, bot_username, "setdescriptionpic", photo_path=photo_path)

    async def delete_userpic(self, session_file: str, bot_username: str) -> tuple[bool, str]:
        """Удалить аватарку"""
        return await self.execute_action(session_file, bot_username, "deleteuserpic")

    async def delete_description_pic(self, session_file: str, bot_username: str) -> tuple[bool, str]:
        """Удалить картинку описания"""
        return await self.execute_action(session_file, bot_username, "deletedescriptionpic")

    async def set_commands(self, session_file: str, bot_username: str, commands: str) -> tuple[bool, str]:
        """Установить команды (формат: command1 - description1\\ncommand2 - description2)"""
        return await self.execute_action(session_file, bot_username, "setcommands", commands)

    async def delete_commands(self, session_file: str, bot_username: str) -> tuple[bool, str]:
        """Удалить все команды"""
        lock = session_manager.get_lock(session_file)
        async with lock:
            client = await session_manager.get_client(session_file)
            if not client:
                return False, "Не удалось подключиться"

            await client.send_message(BOTFATHER_USERNAME, "/setcommands")
            await asyncio.sleep(1)
            await self._select_bot(client, bot_username)
            await asyncio.sleep(1)

            # Нажать кнопку удаления если есть
            messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
            if messages and messages[0].buttons:
                for row in messages[0].buttons:
                    for btn in row:
                        if "delete" in btn.text.lower() or "удалить" in btn.text.lower():
                            await btn.click()
                            return True, "Команды удалены"

            return True, "Готово"

    async def set_inline(self, session_file: str, bot_username: str, enabled: bool) -> tuple[bool, str]:
        """Включить/выключить inline режим"""
        lock = session_manager.get_lock(session_file)
        async with lock:
            client = await session_manager.get_client(session_file)
            if not client:
                return False, "Не удалось подключиться"

            await client.send_message(BOTFATHER_USERNAME, "/setinline")
            await asyncio.sleep(1)
            await self._select_bot(client, bot_username)
            await asyncio.sleep(1)

            messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
            if messages and messages[0].buttons:
                for row in messages[0].buttons:
                    for btn in row:
                        text = btn.text.lower()
                        if enabled and ("enable" in text or "включить" in text or "turn on" in text):
                            await btn.click()
                            return True, "Inline режим включен"
                        elif not enabled and ("disable" in text or "выключить" in text or "turn off" in text):
                            await btn.click()
                            return True, "Inline режим выключен"

            return True, "Статус не изменен"

    async def set_join_groups(self, session_file: str, bot_username: str, enabled: bool) -> tuple[bool, str]:
        """Разрешить/запретить добавление в группы"""
        lock = session_manager.get_lock(session_file)
        async with lock:
            client = await session_manager.get_client(session_file)
            if not client:
                return False, "Не удалось подключиться"

            await client.send_message(BOTFATHER_USERNAME, "/setjoingroups")
            await asyncio.sleep(1)
            await self._select_bot(client, bot_username)
            await asyncio.sleep(1)

            messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
            if messages and messages[0].buttons:
                for row in messages[0].buttons:
                    for btn in row:
                        text = btn.text.lower()
                        if enabled and ("enable" in text or "включить" in text):
                            await btn.click()
                            return True, "Добавление в группы разрешено"
                        elif not enabled and ("disable" in text or "выключить" in text):
                            await btn.click()
                            return True, "Добавление в группы запрещено"

            return True, "Статус не изменен"

    async def set_privacy(self, session_file: str, bot_username: str, enabled: bool) -> tuple[bool, str]:
        """Включить/выключить privacy mode"""
        lock = session_manager.get_lock(session_file)
        async with lock:
            client = await session_manager.get_client(session_file)
            if not client:
                return False, "Не удалось подключиться"

            await client.send_message(BOTFATHER_USERNAME, "/setprivacy")
            await asyncio.sleep(1)
            await self._select_bot(client, bot_username)
            await asyncio.sleep(1)

            messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
            if messages and messages[0].buttons:
                for row in messages[0].buttons:
                    for btn in row:
                        text = btn.text.lower()
                        if enabled and ("enable" in text or "включить" in text):
                            await btn.click()
                            return True, "Privacy mode включен"
                        elif not enabled and ("disable" in text or "выключить" in text):
                            await btn.click()
                            return True, "Privacy mode выключен"

            return True, "Статус не изменен"

    async def set_menu_button(self, session_file: str, bot_username: str, url: str = None) -> tuple[bool, str]:
        """Установить Menu Button"""
        return await self.execute_action(session_file, bot_username, "setmenubutton", url or "/empty")

    async def set_domain(self, session_file: str, bot_username: str, domain: str) -> tuple[bool, str]:
        """Установить домен"""
        return await self.execute_action(session_file, bot_username, "setdomain", domain)

    async def set_privacy_policy(self, session_file: str, bot_username: str, url: str) -> tuple[bool, str]:
        """Установить Privacy Policy"""
        return await self.execute_action(session_file, bot_username, "setprivacypolicy", url)

    async def revoke_token(self, session_file: str, bot_username: str) -> tuple[bool, str]:
        """Получить новый токен"""
        lock = session_manager.get_lock(session_file)
        async with lock:
            client = await session_manager.get_client(session_file)
            if not client:
                return False, "Не удалось подключиться"

            await client.send_message(BOTFATHER_USERNAME, "/revoke")
            await asyncio.sleep(1)
            await self._select_bot(client, bot_username)
            await asyncio.sleep(2)

            messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
            if messages:
                text = messages[0].text
                # Ищем токен в ответе
                import re
                token_match = re.search(r'\d+:[A-Za-z0-9_-]+', text)
                if token_match:
                    return True, token_match.group()
                return True, text

            return False, "Не удалось получить новый токен"

    async def get_token(self, session_file: str, bot_username: str) -> tuple[bool, str]:
        """Получить текущий токен"""
        lock = session_manager.get_lock(session_file)
        async with lock:
            client = await session_manager.get_client(session_file)
            if not client:
                return False, "Не удалось подключиться"

            await client.send_message(BOTFATHER_USERNAME, "/mybots")
            await asyncio.sleep(1)
            await self._select_bot(client, bot_username)
            await asyncio.sleep(1)

            # Нажимаем API Token
            messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
            if messages and messages[0].buttons:
                for row in messages[0].buttons:
                    for btn in row:
                        if "api token" in btn.text.lower() or "токен" in btn.text.lower():
                            await btn.click()
                            await asyncio.sleep(1)
                            break

            messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
            if messages:
                import re
                token_match = re.search(r'\d+:[A-Za-z0-9_-]+', messages[0].text)
                if token_match:
                    return True, token_match.group()

            return False, "Токен не найден"

    async def transfer_ownership(self, session_file: str, bot_username: str, new_owner_id: int) -> tuple[bool, str]:
        """Передать владение ботом"""
        lock = session_manager.get_lock(session_file)
        async with lock:
            client = await session_manager.get_client(session_file)
            if not client:
                return False, "Не удалось подключиться"

            await client.send_message(BOTFATHER_USERNAME, "/mybots")
            await asyncio.sleep(1)
            await self._select_bot(client, bot_username)
            await asyncio.sleep(1)

            # Ищем кнопку Transfer Ownership
            messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
            if messages and messages[0].buttons:
                for row in messages[0].buttons:
                    for btn in row:
                        if "transfer" in btn.text.lower():
                            await btn.click()
                            await asyncio.sleep(1)
                            # Отправляем ID нового владельца
                            await client.send_message(BOTFATHER_USERNAME, str(new_owner_id))
                            await asyncio.sleep(2)
                            messages = await client.get_messages(BOTFATHER_USERNAME, limit=1)
                            return True, messages[0].text if messages else "Запрос отправлен"

            return False, "Кнопка передачи не найдена"


botfather_service = BotFatherService()
