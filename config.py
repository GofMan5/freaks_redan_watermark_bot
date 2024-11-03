import os
from dataclasses import dataclass
from typing import Tuple

@dataclass
class WatermarkConfig:
    TEXT: str = "https://t.me/freaksredana"
    # Список возможных шрифтов в порядке приоритета
    FONTS: tuple = (
        'arial.ttf',
        'Arial.ttf',
        'DejaVuSans.ttf',
        'FreeSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/System/Library/Fonts/Arial.ttf',  # для MacOS
        'C:/Windows/Fonts/arial.ttf',  # для Windows
        '/usr/share/fonts/TTF/arial.ttf'  # для Linux
    )
    SIZE: int = 72
    COLOR: Tuple[int, int, int, int] = (255, 255, 255, 128)
    POSITION: str = "bottom-right"
    # Настройки для видео
    AMPLITUDE: int = 50
    FREQUENCY: float = 2.0
    OPACITY: float = 0.5
    # Дополнительные настройки
    FONT_SCALE: float = 1.0
    THICKNESS: int = 2
    PADDING: int = 20
    # Новые настройки для улучшения качества
    GRID_COLS: int = 3
    GRID_ROWS: int = 2

@dataclass
class BotConfig:
    TOKEN: str = "7592489033:AAEFSE7yvThvM1uR8uT03RCyUn-qQJ2AZsQ"
    DOWNLOAD_PATH: str = "downloads"
    TEMP_PATH: str = "temp"
    CHUNK_SIZE: int = 20 * 1024 * 1024  # Размер чанка для загрузки больших файлов
    ALLOWED_FORMATS: tuple = ('.jpg', '.jpeg', '.png', '.mp4', '.mov')

# Инициализация конфигураций
WATERMARK = WatermarkConfig()
BOT = BotConfig()

# Создание необходимых директорий
for path in [BOT.DOWNLOAD_PATH, BOT.TEMP_PATH]:
    if not os.path.exists(path):
        os.makedirs(path)