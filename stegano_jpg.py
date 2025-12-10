import numpy as np
from PIL import Image
import io
import math
from scipy.fftpack import dct, idct

def hide_text_jpg(image_file, text: str) -> io.BytesIO:
    """
    DCT алгоритм для скрытия текста в JPG.
    Поддерживает кириллицу через UTF-8.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Преобразуем в numpy array
    img_array = np.array(img, dtype=np.float32)
    height, width, channels = img_array.shape
    
    # Кодируем текст в UTF-8 байты
    text_bytes = text.encode('utf-8')
    
    # Добавляем терминатор (два нулевых байта для надежности)
    text_bytes += b'\x00\x00'
    
    # Преобразуем байты в биты
    bits = []
    for byte in text_bytes:
        bits.extend(format(byte, '08b'))
    bits_str = ''.join(bits)
    
    # Размеры в блоках
    blocks_h = height // 8
    blocks_w = width // 8
    
    # Проверяем вместимость (используем все 3 канала)
    max_bits = blocks_h * blocks_w * 3
    if len(bits_str) > max_bits:
        raise ValueError(f"Текст слишком длинный. Максимум: {max_bits//8} байт")
    
    # Скрываем биты
    bit_index = 0
    
    for c in range(channels):  # Для каждого канала
        channel = img_array[:, :, c]
        
        for y_block in range(blocks_h):
            for x_block in range(blocks_w):
                if bit_index >= len(bits_str):
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
                quant_step = 5.0  # Увеличиваем шаг для лучшей устойчивости
                
                # Скрываем бит
                if bits_str[bit_index] == '1':
                    # Устанавливаем ближайшее нечетное кратное quant_step/2
                    quantized = math.floor(original_value / quant_step)
                    dct_block[coef_pos] = quantized * quant_step + quant_step / 2.0
                else:
                    # Устанавливаем ближайшее четное кратное quant_step
                    dct_block[coef_pos] = math.floor(original_value / quant_step) * quant_step
                
                bit_index += 1
                
                # Обратное DCT
                idct_block = idct(idct(dct_block.T, norm='ortho').T, norm='ortho')
                
                # Возвращаем блок
                channel[y_start:y_start+8, x_start:x_start+8] = idct_block
            
            if bit_index >= len(bits_str):
                break
        
        if bit_index >= len(bits_str):
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
    Поддерживает кириллицу через UTF-8.
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
    bytes_list = []
    bits_str = ""
    
    # Восстанавливаем точную последовательность прохода
    bit_index = 0
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
                if bit_index % 3 == 0:
                    coef_pos = (3, 4)
                elif bit_index % 3 == 1:
                    coef_pos = (4, 3)
                else:
                    coef_pos = (5, 2)
                
                value = dct_block[coef_pos]
                quant_step = 5.0
                
                # Определяем, к какому значению ближе
                floor_val = math.floor(value / quant_step) * quant_step
                mid_val = floor_val + quant_step / 2.0
                
                # Вычисляем расстояния
                dist_to_floor = abs(value - floor_val)
                dist_to_mid = abs(value - mid_val)
                
                # Определяем бит (0 если ближе к floor, 1 если ближе к mid)
                if dist_to_mid < dist_to_floor:
                    bits_str += '1'
                else:
                    bits_str += '0'
                
                bit_index += 1
                
                # Каждые 8 бит проверяем
                if len(bits_str) >= 8:
                    byte_bits = bits_str[:8]
                    bits_str = bits_str[8:]
                    
                    byte_value = int(byte_bits, 2)
                    
                    # Проверяем на терминатор (два нулевых байта подряд)
                    if byte_value == 0:
                        if len(bytes_list) > 0 and bytes_list[-1] == 0:
                            # Нашли два нулевых байта подряд - конец текста
                            bytes_list.pop()  # Удаляем первый нулевой байт
                            try:
                                # Декодируем все байты как UTF-8
                                return bytes(bytes_list).decode('utf-8')
                            except UnicodeDecodeError:
                                # Если не получается декодировать как UTF-8
                                try:
                                    return bytes(bytes_list).decode('cp1251')
                                except:
                                    return bytes(bytes_list).decode('latin-1')
                    
                    bytes_list.append(byte_value)
        
        # Проверяем, не собрали ли мы уже весь текст
        if len(bits_str) < 8 and len(bytes_list) > 0:
            # Пытаемся декодировать то, что есть
            try:
                return bytes(bytes_list).decode('utf-8')
            except UnicodeDecodeError:
                try:
                    return bytes(bytes_list).decode('cp1251')
                except:
                    return bytes(bytes_list).decode('latin-1')
    
    # Если дошли до конца, пытаемся декодировать все, что собрали
    try:
        return bytes(bytes_list).decode('utf-8')
    except UnicodeDecodeError:
        try:
            return bytes(bytes_list).decode('cp1251')
        except:
            return bytes(bytes_list).decode('latin-1')