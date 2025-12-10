from PIL import Image
import io

def hide_text_bmp(image_file, text: str) -> io.BytesIO:
    """
    Скрывает текст в BMP-изображении с помощью LSB-стеганографии.
    Поддерживает кириллицу через UTF-8.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Кодируем текст в UTF-8 байты
    text_bytes = text.encode('utf-8')
    
    # Добавляем терминатор (нулевой байт)
    text_bytes += b'\x00'
    
    # Преобразуем байты в биты
    bits = []
    for byte in text_bytes:
        bits.extend(format(byte, '08b'))
    bits_str = ''.join(bits)
    
    # Проверяем размер
    total_bits = img.width * img.height * 3
    if len(bits_str) > total_bits:
        raise ValueError(f"Текст слишком длинный. Максимум: {total_bits//8} байт")
    
    # Создаём копию для модификации
    encoded_img = img.copy()
    pixels = encoded_img.load()
    bit_index = 0
    
    # Проходим по всем пикселям
    for y in range(img.height):
        for x in range(img.width):
            if bit_index >= len(bits_str):
                break
                
            r, g, b = img.getpixel((x, y))
            new_r, new_g, new_b = r, g, b
            
            # Меняем младший бит
            if bit_index < len(bits_str):
                new_r = (r & 0xFE) | int(bits_str[bit_index])
                bit_index += 1
                
            if bit_index < len(bits_str):
                new_g = (g & 0xFE) | int(bits_str[bit_index])
                bit_index += 1
                
            if bit_index < len(bits_str):
                new_b = (b & 0xFE) | int(bits_str[bit_index])
                bit_index += 1
            
            pixels[x, y] = (new_r, new_g, new_b)
            
        if bit_index >= len(bits_str):
            break
    
    # Сохраняем результат
    output = io.BytesIO()
    encoded_img.save(output, format='BMP', optimize=True)
    output.seek(0)
    return output

def extract_text_bmp(image_file) -> str:
    """
    Извлекает скрытый текст из BMP-изображения с помощью LSB-стеганографии.
    Поддерживает кириллицу через UTF-8.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    bits = []
    bytes_list = []
    
    # Проходим по всем пикселям и извлекаем младшие биты
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = img.getpixel((x, y))
            
            # Извлекаем младшие биты каждого канала
            bits.append(str(r & 1))
            bits.append(str(g & 1))
            bits.append(str(b & 1))
            
            # Каждые 8 бит преобразуем в байт
            while len(bits) >= 8:
                byte_bits = bits[:8]
                bits = bits[8:]
                
                byte_value = int(''.join(byte_bits), 2)
                
                # Если встретили нулевой байт - конец текста
                if byte_value == 0:
                    try:
                        # Декодируем все байты как UTF-8
                        return bytes(bytes_list).decode('utf-8')
                    except UnicodeDecodeError:
                        # Если не получается декодировать как UTF-8, пробуем другие кодировки
                        try:
                            return bytes(bytes_list).decode('cp1251')
                        except:
                            return bytes(bytes_list).decode('latin-1')
                
                bytes_list.append(byte_value)
    
    # Если не нашли терминатор, пытаемся декодировать то, что есть
    try:
        return bytes(bytes_list).decode('utf-8')
    except UnicodeDecodeError:
        return bytes(bytes_list).decode('latin-1')