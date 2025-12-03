from PIL import Image
import io

def hide_text_bmp(image_file, text: str) -> io.BytesIO:
    """
    Скрывает текст в BMP-изображении с помощью LSB-стеганографии.
    BMP поддерживает LSB так как это несжатый формат.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    # BMP обычно в режиме RGB или RGBA
    if img.mode not in ['RGB', 'RGBA']:
        img = img.convert('RGB')
    
    # Добавляем терминатор
    text += '\x00'
    
    # Преобразуем текст в биты
    bits = ''.join(format(ord(char), '08b') for char in text)
    
    # Проверяем размер
    channels = len(img.getbands())  # Получаем количество каналов (3 для RGB, 4 для RGBA)
    total_bits = img.width * img.height * 3  # Используем только RGB каналы для LSB
    
    if len(bits) > total_bits:
        raise ValueError(f"Текст слишком длинный для данного изображения. Макс: {total_bits//8} символов")
    
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
            new_pixel = list(pixel)
            
            # Обрабатываем первые 3 канала (RGB)
            for i in range(min(3, len(pixel))):  # Берем максимум 3 цветовых канала
                if bit_index < len(bits):
                    # Меняем младший бит
                    new_pixel[i] = (pixel[i] & 0xFE) | int(bits[bit_index])
                    bit_index += 1
            
            pixels[x, y] = tuple(new_pixel)
            
        if bit_index >= len(bits):
            break
    
    # Сохраняем результат как BMP
    output = io.BytesIO()
    
    # Сохраняем в том же режиме, что и исходное изображение
    encoded_img.save(output, format='BMP')
    output.seek(0)
    return output

def extract_text_bmp(image_file) -> str:
    """
    Извлекает скрытый текст из BMP-изображения с помощью LSB-стеганографии.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    # Конвертируем в RGB/RGBA для совместимости
    if img.mode not in ['RGB', 'RGBA']:
        img = img.convert('RGB')
    
    bits = []
    text = ""
    
    # Проходим по всем пикселям и извлекаем младшие биты
    for y in range(img.height):
        for x in range(img.width):
            pixel = img.getpixel((x, y))
            
            # Извлекаем младшие биты первых 3 каналов (RGB)
            for i in range(min(3, len(pixel))):
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