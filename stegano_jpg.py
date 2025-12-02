import numpy as np
from PIL import Image
import io
import math
from scipy.fftpack import dct, idct

def hide_text_jpg(image_file, text: str) -> io.BytesIO:
    """
    DCT алгоритм для скрытия текста в JPG.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Преобразуем в numpy array
    img_array = np.array(img, dtype=np.float32)
    height, width, channels = img_array.shape
    
    # Добавляем терминатор
    text += '\x00'
    
    # Преобразуем текст в биты
    bits = ''.join(format(ord(char), '08b') for char in text)
    
    # Размеры в блоках
    blocks_h = height // 8
    blocks_w = width // 8
    
    # Проверяем вместимость (используем все 3 канала)
    max_bits = blocks_h * blocks_w * 3
    if len(bits) > max_bits:
        raise ValueError(f"Текст слишком длинный. Максимум: {max_bits//8} символов")
    
    # Скрываем биты
    bit_index = 0
    
    for c in range(channels):  # Для каждого канала
        channel = img_array[:, :, c]
        
        for y_block in range(blocks_h):
            for x_block in range(blocks_w):
                if bit_index >= len(bits):
                    break
                
                # Извлекаем блок
                y_start = y_block * 8
                x_start = x_block * 8
                block = channel[y_start:y_start+8, x_start:x_start+8]
                
                # Применяем DCT
                dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
                
                # Выбираем разные коэффициенты для разных битов
                if bit_index % 3 == 0:
                    coef_pos = (3, 4)  # Низкая частота
                elif bit_index % 3 == 1:
                    coef_pos = (4, 3)  # Средняя частота
                else:
                    coef_pos = (5, 2)  # Средняя частота
                
                original_value = dct_block[coef_pos]
                quant_step = 4.0  # Больший шаг для устойчивости
                
                # Скрываем бит
                if bits[bit_index] == '1':
                    # Устанавливаем ближайшее нечетное кратное quant_step/2
                    dct_block[coef_pos] = math.floor(original_value / quant_step) * quant_step + quant_step / 2.0
                else:
                    # Устанавливаем ближайшее четное кратное quant_step
                    dct_block[coef_pos] = math.floor(original_value / quant_step) * quant_step
                
                bit_index += 1
                
                # Обратное DCT
                idct_block = idct(idct(dct_block.T, norm='ortho').T, norm='ortho')
                
                # Возвращаем блок
                channel[y_start:y_start+8, x_start:x_start+8] = idct_block
            
            if bit_index >= len(bits):
                break
        
        if bit_index >= len(bits):
            break
    
    # Конвертируем обратно
    img_array = np.clip(img_array, 0, 255).astype(np.uint8)
    encoded_img = Image.fromarray(img_array, 'RGB')
    
    # Сохраняем с максимальным качеством
    output = io.BytesIO()
    encoded_img.save(output, format='JPEG', quality=100, optimize=False, subsampling=0)
    output.seek(0)
    
    return output

def extract_text_jpg(image_file) -> str:
    """
    Извлекает текст из JPG с DCT алгоритмом.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    img_array = np.array(img, dtype=np.float32)
    height, width, channels = img_array.shape
    
    blocks_h = height // 8
    blocks_w = width // 8
    
    bits = []
    text = ""
    
    # Восстанавливаем точную последовательность прохода
    for c in range(channels):
        channel = img_array[:, :, c]
        
        for y_block in range(blocks_h):
            for x_block in range(blocks_w):
                # Извлекаем блок
                y_start = y_block * 8
                x_start = x_block * 8
                block = channel[y_start:y_start+8, x_start:x_start+8]
                
                # Применяем DCT
                dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
                
                # Определяем позицию коэффициента на основе общего индекса
                total_index = (c * blocks_h * blocks_w) + (y_block * blocks_w) + x_block
                
                if total_index % 3 == 0:
                    coef_pos = (3, 4)
                elif total_index % 3 == 1:
                    coef_pos = (4, 3)
                else:
                    coef_pos = (5, 2)
                
                value = dct_block[coef_pos]
                quant_step = 4.0
                
                # Определяем, к какому значению ближе
                floor_val = math.floor(value / quant_step) * quant_step
                mid_val = floor_val + quant_step / 2.0
                
                # Вычисляем расстояния
                dist_to_floor = abs(value - floor_val)
                dist_to_mid = abs(value - mid_val)
                
                # Определяем бит (0 если ближе к floor, 1 если ближе к mid)
                if dist_to_mid < dist_to_floor:
                    bits.append('1')
                else:
                    bits.append('0')
                
                # Каждые 8 бит проверяем
                if len(bits) >= 8:
                    byte_bits = bits[:8]
                    bits = bits[8:]
                    
                    char_code = int(''.join(byte_bits), 2)
                    
                    # Терминатор
                    if char_code == 0:
                        return text
                    
                    text += chr(char_code)
    
    return text