from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import math
from moviepy.editor import VideoFileClip, AudioFileClip
from config import WATERMARK
import os
import logging
from typing import Tuple, Optional
import random

class WatermarkProcessor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _get_text_size(self, draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
        """Получает размеры текста с учетом новых версий Pillow"""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        return (text_width, text_height)

    def _get_random_positions(self, image_size: Tuple[int, int], text_size: Tuple[int, int], count: int = 10) -> list:
        """Генерирует случайные позиции для водяных знаков"""
        width, height = image_size
        text_width, text_height = text_size
        positions = []
        
        # Создаем сетку для равномерного распределения
        grid_cols = WATERMARK.GRID_COLS
        grid_rows = WATERMARK.GRID_ROWS
        
        # Вычисляем размеры ячейки
        cell_width = width // grid_cols
        cell_height = height // grid_rows
        
        # Проверяем, что текст не больше ячейки
        if text_width >= cell_width:
            # Уменьшаем количество колонок, если текст слишком большой
            grid_cols = max(1, width // (text_width + 20))
            cell_width = width // grid_cols
        
        if text_height >= cell_height:
            # Уменьшаем количество строк, если текст слишком большой
            grid_rows = max(1, height // (text_height + 20))
            cell_height = height // grid_rows
        
        for row in range(grid_rows):
            for col in range(grid_cols):
                # Вычисляем границы для размещения текста в ячейке
                x_min = col * cell_width
                y_min = row * cell_height
                x_max = x_min + cell_width - text_width
                y_max = y_min + cell_height - text_height
                
                # Если места д��я текста недостаточно, используем минимальные координаты
                x = x_min if x_max <= x_min else random.randint(x_min, x_max)
                y = y_min if y_max <= y_min else random.randint(y_min, y_max)
                
                # Добавляем небольшой случайный поворот
                angle = random.uniform(-30, 30)
                positions.append((x, y, angle))
        
        return positions

    def _get_available_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Находит доступный шрифт в системе"""
        for font_path in WATERMARK.FONTS:
            try:
                return ImageFont.truetype(font_path, size)
            except OSError:
                continue
        
        self.logger.warning("Не найдены системные шрифты, использую шрифт по умолчанию")
        return ImageFont.load_default()

    def process_image(self, input_path: str, output_path: str) -> Optional[str]:
        """Обработка изображения с множественными водяными знаками"""
        try:
            # Открываем изображение
            image = Image.open(input_path)
            
            # Получаем размеры изображения
            width, height = image.size
            
            # Масштабируем размер шрифта относительно размера изображения
            font_size = int(min(width, height) * 0.05)  # 5% от меньшей стороны
            
            # Конвертируем в RGBA для работы с прозрачностью
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # Создаем новый прозрачный слой для водяных знаков
            watermark_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(watermark_layer)
            
            # Получаем доступный шрифт
            font = self._get_available_font(font_size)
            
            # Получаем размер текста
            text_size = self._get_text_size(draw, WATERMARK.TEXT, font)
            
            # Получаем случайные позиции для водяных знаков
            positions = self._get_random_positions(image.size, text_size)
            
            # Создаем цвет с нужной прозрачностью дл�� текста
            watermark_color = (*WATERMARK.COLOR[:3], int(255 * 0.3))
            
            # Наносим водяные знаки на прозрачный слой с улучшенным качеством
            for x, y, angle in positions:
                # Создаем временное изображение для текста с увеличенным размером
                scale = 2  # Увеличиваем размер в 2 раза для лучшего качества
                txt = Image.new('RGBA', 
                              (text_size[0] * scale, text_size[1] * scale), 
                              (0, 0, 0, 0))
                d = ImageDraw.Draw(txt)
                
                # Рисуем текст с увеличенным размером
                scaled_font = self._get_available_font(font_size * scale)
                d.text((0, 0), WATERMARK.TEXT, font=scaled_font, fill=watermark_color)
                
                # Поворачиваем текст с высоким качеством
                rotated_txt = txt.rotate(angle, expand=True, resample=Image.BICUBIC)
                
                # Уменьшаем обратно до нужного размера с высоким качеством
                rotated_txt = rotated_txt.resize(
                    (int(rotated_txt.size[0] / scale), 
                     int(rotated_txt.size[1] / scale)),
                    Image.LANCZOS
                )
                
                # Накладываем на прозрачный слой
                watermark_layer.paste(rotated_txt, (x, y), rotated_txt)
            
            # Комбинируем изображение и слой с водяными знаками
            result = Image.alpha_composite(image, watermark_layer)
            
            # Конвертируем результат в RGB перед сохранением в JPEG
            result_rgb = Image.new('RGB', image.size, (255, 255, 255))
            result_rgb.paste(result, mask=result.split()[3])
            
            # Сохраняем результат с высоким качеством
            result_rgb.save(output_path, 'JPEG', quality=95, subsampling=0)
            
            return output_path
        except Exception as e:
            self.logger.error(f"Ошибка при обработке изображения: {str(e)}")
            raise

    def process_video(self, input_path: str, output_path: str, is_video_note: bool = False) -> Optional[str]:
        """Обработка видео"""
        temp_output = output_path.replace('.mp4', '_temp.mp4')
        
        cap = None
        out = None
        video = None
        processed_video = None
        final_video = None
        
        try:
            cap = cv2.VideoCapture(input_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Для видео-кружков нужен квадратный размер
            if is_video_note:
                size = min(width, height)
                width = size
                height = size
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(WATERMARK.TEXT, font, WATERMARK.FONT_SCALE, WATERMARK.THICKNESS)[0]
            
            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                if is_video_note:
                    # Обрезаем кадр до квадрата
                    h, w = frame.shape[:2]
                    size = min(w, h)
                    x = (w - size) // 2
                    y = (h - size) // 2
                    frame = frame[y:y+size, x:x+size]
                    frame = cv2.resize(frame, (width, height))
                
                overlay = frame.copy()
                position = self._get_floating_position((width, height), text_size, frame_count, total_frames)
                
                cv2.putText(overlay, WATERMARK.TEXT, position, font, WATERMARK.FONT_SCALE,
                           WATERMARK.COLOR[:3], WATERMARK.THICKNESS, cv2.LINE_AA)
                
                frame = cv2.addWeighted(overlay, WATERMARK.OPACITY, frame, 1 - WATERMARK.OPACITY, 0)
                out.write(frame)
                frame_count += 1
            
            # Закрываем видео объекты
            if cap is not None:
                cap.release()
            if out is not None:
                out.release()
            
            # Обработка звука
            try:
                video = VideoFileClip(input_path)
                if video.audio is not None:
                    processed_video = VideoFileClip(temp_output)
                    final_video = processed_video.set_audio(video.audio)
                    
                    # Используем временный путь для финального видео
                    final_temp = output_path.replace('.mp4', '_final_temp.mp4')
                    final_video.write_videofile(final_temp, codec='libx264', audio_codec='aac')
                    
                    # Закрываем все объекты перед операциями с файлами
                    video.close()
                    processed_video.close()
                    final_video.close()
                    
                    # Удаляем временные файлы и перемещаем финальное видео
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    os.rename(final_temp, output_path)
                else:
                    # Если нет звука, просто перемещаем временный файл
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    os.rename(temp_output, output_path)
            except Exception as e:
                self.logger.error(f"Ошибка при обработке звука: {str(e)}")
                # В случае ошибки со звуком используем видео без звука
                if os.path.exists(output_path):
                    os.remove(output_path)
                os.rename(temp_output, output_path)
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке видео: {str(e)}")
            raise
        finally:
            # Закрываем все объекты в блоке finally
            if cap is not None:
                cap.release()
            if out is not None:
                out.release()
            if video is not None:
                video.close()
            if processed_video is not None:
                processed_video.close()
            if final_video is not None:
                final_video.close()
            
            # Удаляем временные файлы
            temp_files = [
                temp_output,
                output_path.replace('.mp4', '_final_temp.mp4')
            ]
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    self.logger.error(f"Ошибка при удалении временного файла {temp_file}: {str(e)}")

    def _get_floating_position(self, frame_size: Tuple[int, int], text_size: Tuple[int, int], 
                         frame_count: int, total_frames: int) -> Tuple[int, int]:
        """Вычисляет позицию плавающего водяного знака для видео"""
        width, height = frame_size
        text_width, text_height = text_size
        
        # Вычисляем центр экрана
        center_x = (width - text_width) // 2
        center_y = (height - text_height) // 2
        
        # Создаем эффект плавающего движения
        time = frame_count / total_frames * 2 * math.pi  # Преобразуем номер кадра во время
        
        # Движение по кругу с изменяющимся радиусом
        radius = WATERMARK.AMPLITUDE * (1 + math.sin(time * 0.5)) / 2  # Радиус меняется от 0 до AMPLITUDE
        
        # Вычисляем смещение от центра
        offset_x = radius * math.cos(time * WATERMARK.FREQUENCY)
        offset_y = radius * math.sin(time * WATERMARK.FREQUENCY)
        
        # Добавляем небольшое вертикальное колебание
        vertical_offset = WATERMARK.AMPLITUDE * 0.3 * math.sin(time * 2)
        
        # Вычисляем финальные координаты
        x = int(center_x + offset_x)
        y = int(center_y + offset_y + vertical_offset)
        
        # Убеждаемся, что текст не выходит за границы кадра
        x = max(0, min(x, width - text_width))
        y = max(0, min(y, height - text_height))
        
        return (x, y)