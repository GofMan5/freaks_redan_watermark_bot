from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT
from handlers.media_handlers import register_handlers
import logging
import sys

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

async def on_startup(dp: Dispatcher):
    """Действия при запуске бота"""
    logging.info('Бот запущен')
    
async def on_shutdown(dp: Dispatcher):
    """Действия при остановке бота"""
    logging.info('Бот остановлен')
    await dp.storage.close()
    await dp.storage.wait_closed()

def main():
    """Основная функция запуска бота"""
    setup_logging()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT.TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    
    # Регистрация обработчиков
    register_handlers(dp)
    
    # Запуск бота
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )

if __name__ == '__main__':
    main()