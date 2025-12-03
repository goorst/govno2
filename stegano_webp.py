from PIL import Image
import io

def hide_text_webp(image_file, text: str) -> io.BytesIO:
    """
    Скрывает текст в WebP-изображении с помощью LSB-стеганографии.
    WebP поддерживает сжатие, но в режиме без потерь можно использовать LSB.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    # Конвертируем в RGB/RGBA для совместимости
    if img.mode not in ['RGB', 'RGBA']:
        img = img.convert('RGB')
    
    # Добавляем терминатор
    text += '\x00'
    
    # Преобразуем текст в биты
    bits = ''.join(format(ord(char), '08b') for char in text)
    
    # Проверяем размер
    channels = 3 if img.mode == 'RGB' else 4  # RGBA
    total_bits = img.width * img.height * channels
    if len(bits) > total_bits:
        raise ValueError("Текст слишком длинный для данного изображения.")
    
    # Создаём копию для модификации
    encoded_img = img.copy()
    pixels = encoded_img.load()
    bit_index = 0
    
    # Проходим по всем пикселям
    for y in range(img.height):
        for x in range(img.width):
            if bit_index >= len(bits):
                break
                
            pixel = img.getpixel((x, y))
            new_pixel = []
            
            # Обрабатываем каждый канал
            for i, channel_value in enumerate(pixel[:channels]):  # Берем только цветовые каналы
                if bit_index < len(bits):
                    # Меняем младший бит
                    new_channel = (channel_value & 0xFE) | int(bits[bit_index])
                    bit_index += 1
                else:
                    new_channel = channel_value
                new_pixel.append(new_channel)
            
            # Если RGBA, сохраняем альфа-канал без изменений
            if img.mode == 'RGBA' and len(pixel) == 4 and i < 3:
                new_pixel.append(pixel[3])
            
            pixels[x, y] = tuple(new_pixel)
            
        if bit_index >= len(bits):
            break
    
    # Сохраняем результат как WebP с минимальным сжатием для сохранения LSB
    output = io.BytesIO()
    encoded_img.save(output, format='WEBP', lossless=True, quality=100)
    output.seek(0)
    return output

def extract_text_webp(image_file) -> str:
    """
    Извлекает скрытый текст из WebP-изображения с помощью LSB-стеганографии.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    # Конвертируем в RGB/RGBA для совместимости
    if img.mode not in ['RGB', 'RGBA']:
        img = img.convert('RGB')
    
    channels = 3 if img.mode == 'RGB' else 3  # Для извлечения используем только цветовые каналы
    
    bits = []
    text = ""
    
    # Проходим по всем пикселям и извлекаем младшие биты
    for y in range(img.height):
        for x in range(img.width):
            pixel = img.getpixel((x, y))
            
            # Извлекаем младшие биты каждого цветового канала
            for i in range(channels):
                bits.append(str(pixel[i] & 1))
            
            # Каждые 8 бит пытаемся преобразовать в символ
            while len(bits) >= 8:
                byte_bits = bits[:8]
                bits = bits[8:]
                
                char_code = int(''.join(byte_bits), 2)
                
                # Если встретили нулевой байт - конец текста
                if char_code == 0:
                    return text
                
                text += chr(char_code)
    
    return text