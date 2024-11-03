from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Command
from utils.watermark import WatermarkProcessor
from config import BOT, WATERMARK
import os
import logging
from typing import Union
import asyncio
import aiohttp
import math

class MediaHandler:
    def __init__(self):
        self.processor = WatermarkProcessor()
        
    async def download_file(self, file: types.File, destination: str, message: types.Message) -> bool:
        """Загрузка больших файлов с отображением прогресса"""
        try:
            # Получаем URL для загрузки файла
            file_url = await file.get_url()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    total_size = int(response.headers.get('content-length', 0))
                    
                    if total_size == 0:
                        await message.reply("Ошибка: невозможно определить размер файла")
                        return False
                    
                    # Создаем сообщение с прогрессом
                    progress_message = await message.reply("Загрузка: 0%")
                    
                    # Открываем файл для записи
                    with open(destination, 'wb') as f:
                        downloaded = 0
                        last_percentage = 0
                        
                        async for chunk in response.content.iter_chunked(BOT.CHUNK_SIZE):
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Обновляем прогресс каждые 5%
                            percentage = int((downloaded / total_size) * 100)
                            if percentage - last_percentage >= 5:
                                await progress_message.edit_text(f"Загрузка: {percentage}%")
                                last_percentage = percentage
                    
                    await progress_message.delete()
                    return True
                    
        except Exception as e:
            logging.error(f"Ошибка при загрузке файла: {str(e)}")
            await message.reply(f"Ошибка при загрузке файла: {str(e)}")
            return False

    async def process_media(self, message: types.Message, media_type: str) -> Union[tuple[str, str], tuple[None, None]]:
        """Общая логика обработки медиафайлов"""
        try:
            # Определяем file_id в зависимости от типа медиа
            if media_type == "photo":
                file_id = message.photo[-1].file_id
            elif media_type == "video":
                file_id = message.video.file_id
            elif media_type == "video_note":
                file_id = message.video_note.file_id
            else:
                raise ValueError(f"Неподдерживаемый тип медиа: {media_type}")

            # Создание временных путей
            input_path = os.path.join(BOT.DOWNLOAD_PATH, f"{file_id}")
            output_path = os.path.join(BOT.DOWNLOAD_PATH, f"watermarked_{file_id}")

            # Добавление расширения
            ext = ".jpg" if media_type == "photo" else ".mp4"
            input_path += ext
            output_path += ext

            return input_path, output_path

        except Exception as e:
            logging.error(f"Ошибка при обработке {media_type}: {str(e)}")
            await message.reply(f"Произошла ошибка при обработке файла: {str(e)}")
            return None, None

    async def handle_photo(self, message: types.Message):
        """Обработчик фото"""
        processing_msg = await message.reply("Начинаю обработку фото...")
        
        try:
            input_path, output_path = await self.process_media(message, "photo")
            if not input_path:
                return

            # Загрузка фото
            file = await message.photo[-1].get_file()
            if not await self.download_file(file, input_path, message):
                return

            # Добавление водяного знака
            self.processor.process_image(input_path, output_path)

            # Отправка обработанного фото
            await message.reply_photo(
                photo=open(output_path, 'rb'),
                caption="Фото с водяным знаком"
            )

        except Exception as e:
            await message.reply(f"Ошибка при обработке фото: {str(e)}")
        finally:
            await processing_msg.delete()
            # Очистка временных файлов
            for path in [input_path, output_path]:
                if os.path.exists(path):
                    os.remove(path)

    async def handle_video(self, message: types.Message):
        """Обработчик видео"""
        processing_msg = await message.reply("Начинаю обработку видео...")
        
        try:
            input_path, output_path = await self.process_media(message, "video")
            if not input_path:
                return

            # Загрузка видео
            file = await message.video.get_file()
            if not await self.download_file(file, input_path, message):
                return

            await message.reply("Файл загружен, добавляю водяной знак...")

            # Добавление водяного знака
            self.processor.process_video(input_path, output_path)

            await message.reply("Водяной знак добавлен, отправляю обработанное видео...")

            # Отправка обработанного видео
            await message.reply_video(
                video=open(output_path, 'rb'),
                caption="Видео с водяным знаком"
            )

        except Exception as e:
            await message.reply(f"Ошибка при обработке видео: {str(e)}")
        finally:
            await processing_msg.delete()
            # Очистка временных файлов
            for path in [input_path, output_path]:
                if os.path.exists(path):
                    os.remove(path)

    async def handle_video_note(self, message: types.Message):
        """Обработчик видео-кружков"""
        processing_msg = await message.reply("Начинаю обработку видео-кружка...")
        
        try:
            input_path, output_path = await self.process_media(message, "video_note")
            if not input_path:
                return

            # Загрузка видео
            file = await message.video_note.get_file()
            if not await self.download_file(file, input_path, message):
                return

            await message.reply("Файл загружен, добавляю водяной знак...")

            # Добавление водяного знака
            self.processor.process_video(input_path, output_path, is_video_note=True)

            await message.reply("Водяной знак добавлен, отправляю обработанное видео...")

            # Отправка обработанного видео-кружка
            with open(output_path, 'rb') as video:
                await message.reply_video_note(
                    video_note=video
                )

        except Exception as e:
            await message.reply(f"Ошибка при обработке видео-кружка: {str(e)}")
        finally:
            await processing_msg.delete()
            # Очистка временных файлов
            for path in [input_path, output_path]:
                if os.path.exists(path):
                    os.remove(path)

    async def cmd_start(self, message: types.Message):
        """Обработчик команды /start"""
        await message.reply(
            "👋 Привет! Я бот для добавления водяных знаков на медиафайлы.\n\n"
            "📝 Команды:\n"
            "/start - Показать это сообщение\n"
            "/help - Подробная инструкция\n\n"
            "✨ Возможности:\n"
            "• Добавление водяных знаков на фото\n"
            "• Обработка видео с плавающим водяным знаком\n"
            "• Поддержка видео-кружков\n"
            "• Работа с файлами любого размера\n\n"
            "🚀 Просто отправьте мне любой медиафайл!\n\n"
            "🔗 Бот создан для @freaksredana\n"
            "👨‍💻 Разработчик: @Anonimus090"
        )

    async def cmd_help(self, message: types.Message):
        """Обработчик команды /help"""
        await message.reply(
            "📖 Инструкция по использованию бота:\n\n"
            "1️⃣ Отправка фото:\n"
            "• Отправьте фото в чат\n"
            "• Бот добавит водяные знаки и вернёт обработанное изображение\n\n"
            "2️⃣ Отправка видео:\n"
            "• Отправьте видео в чат\n"
            "• Бот добавит плавающий водяной знак\n"
            "• Качество и звук сохраняются\n\n"
            "3️⃣ Видео-кружки:\n"
            "• Отправьте видео-кружок\n"
            "• Бот обработает его с сохранением формата\n\n"
            "⚙️ Дополнительные команды:\n"
            "/start - Главное меню\n\n"
            "❗️ Важно:\n"
            "• Поддерживаются форматы: JPG, PNG, MP4, MOV\n"
            "• Размер файлов не ограничен\n"
            "• Обработка может занять некоторое время\n\n"
            "🤝 По всем вопросам: @Anonimus090"
        )

    async def cmd_settings(self, message: types.Message):
        """Показывает текущие настройки водяного знака"""
        settings = (
            "⚙️ Текущие настройки бота:\n\n"
            f"📝 Текст водяного знака: {WATERMARK.TEXT}\n"
            f"📏 Размер шрифта: {WATERMARK.SIZE}\n"
            f"🔍 Прозрачность: {int(WATERMARK.OPACITY * 100)}%\n"
            f"📍 Расположение на фото: {WATERMARK.POSITION}\n\n"
            "🎥 Настройки для видео:\n"
            f"📊 Амплитуда движения: {WATERMARK.AMPLITUDE}\n"
            f"⚡️ Частота движения: {WATERMARK.FREQUENCY}\n\n"
            "🎨 Сетка водяных знаков:\n"
            f"↔️ Колонок: {WATERMARK.GRID_COLS}\n"
            f"↕️ Строк: {WATERMARK.GRID_ROWS}"
        )
        await message.reply(settings)

def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    handler = MediaHandler()
    
    # Команды
    dp.register_message_handler(handler.cmd_start, Command("start"))
    dp.register_message_handler(handler.cmd_help, Command("help"))
    
    # Медиафайлы
    dp.register_message_handler(handler.handle_photo, content_types=[types.ContentType.PHOTO])
    dp.register_message_handler(handler.handle_video, content_types=[types.ContentType.VIDEO])
    dp.register_message_handler(handler.handle_video_note, content_types=[types.ContentType.VIDEO_NOTE]) 