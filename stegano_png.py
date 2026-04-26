from PIL import Image
import io
import hashlib
import random

# Уникальный маркер конца текста
END_MARKER = b'\x00\xFF\x00\xFF\x00'

def generate_seed_from_key(key: str = "default_seed") -> int:
    """Генерирует числовой seed из строкового ключа через SHA-256"""
    hash_object = hashlib.sha256(key.encode())
    return int.from_bytes(hash_object.digest()[:8], 'big')

def generate_pseudo_random_positions(total_pixels: int, total_bits: int, seed_key: str = "stegano_key") -> list:
    """
    Генерирует псевдослучайные позиции для встраивания битов.
    
    Использует эффективный алгоритм без создания полного списка всех позиций:
    1. Из ключа через SHA-256 получаем seed
    2. Для каждого бита генерируем случайный индекс пикселя и канал
    3. Отклоняем повторы через множество used_positions
    
    Сложность: O(n) по памяти, где n = total_bits
    """
    seed = generate_seed_from_key(seed_key)
    rng = random.Random(seed)
    
    positions = []
    used_positions = set()
    total_channels = 3
    
    # Генерируем ровно total_bits уникальных позиций
    while len(positions) < total_bits:
        pixel_idx = rng.randint(0, total_pixels - 1)
        channel = rng.randint(0, total_channels - 1)
        
        position = (pixel_idx, channel)
        if position not in used_positions:
            used_positions.add(position)
            positions.append(position)
    
    return positions

def hide_text_png(image_file, text: str, seed_key: str = "stegano_key") -> io.BytesIO:
    """
    Скрывает текст в PNG-изображении с помощью LSB-стеганографии 
    с псевдослучайным распределением битов.
    """
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Кодируем текст в UTF-8 байты + маркер конца
    text_bytes = text.encode('utf-8')
    text_bytes += END_MARKER
    
    # Преобразуем байты в биты (от старшего к младшему)
    bits = []
    for byte in text_bytes:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    
    # Проверяем размер
    total_pixels = img.width * img.height
    
    if len(bits) > total_pixels * 3:
        raise ValueError(f"Текст слишком длинный")
    
    # Генерируем псевдослучайные позиции
    positions = generate_pseudo_random_positions(total_pixels, len(bits), seed_key)
    
    # Создаём копию для модификации
    encoded_img = img.copy()
    pixels = encoded_img.load()
    
    # Создаем массив пикселей для доступа по индексу
    pixel_array = []
    for y in range(img.height):
        for x in range(img.width):
            pixel_array.append((x, y))
    
    # Встраиваем биты
    for bit_idx, (pixel_idx, channel) in enumerate(positions):
        x, y = pixel_array[pixel_idx]
        r, g, b = encoded_img.getpixel((x, y))
        
        bit_val = bits[bit_idx]
        
        if channel == 0:
            r = (r & 0xFE) | bit_val
        elif channel == 1:
            g = (g & 0xFE) | bit_val
        else:
            b = (b & 0xFE) | bit_val
            
        pixels[x, y] = (r, g, b)
    
    # Сохраняем результат
    output = io.BytesIO()
    encoded_img.save(output, format='PNG', optimize=False)
    output.seek(0)
    return output

def extract_text_png(image_file, seed_key: str = "stegano_key") -> str:
    """
    Извлекает скрытый текст из PNG-изображения.
    """
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    total_pixels = img.width * img.height
    total_bits = total_pixels * 3
    
    # Создаем массив пикселей
    pixel_array = []
    for y in range(img.height):
        for x in range(img.width):
            pixel_array.append((x, y))
    
    # Генерируем те же позиции (используем тот же ключ)
    # Берем с запасом, но не все возможные
    max_bits_to_extract = min(total_bits, 50000)  # Ограничиваем для скорости
    positions = generate_pseudo_random_positions(total_pixels, max_bits_to_extract, seed_key)
    
    bits = []
    bytes_list = []
    
    # Извлекаем биты
    for bit_idx, (pixel_idx, channel) in enumerate(positions):
        x, y = pixel_array[pixel_idx]
        r, g, b = img.getpixel((x, y))
        
        if channel == 0:
            bits.append(r & 1)
        elif channel == 1:
            bits.append(g & 1)
        else:
            bits.append(b & 1)
        
        # Формируем байты
        if len(bits) >= 8:
            byte_val = 0
            for i in range(8):
                byte_val = (byte_val << 1) | bits[i]
            bits = bits[8:]
            
            bytes_list.append(byte_val)
            
            # Проверяем маркер конца
            if len(bytes_list) >= len(END_MARKER):
                last_bytes = bytes(bytes_list[-len(END_MARKER):])
                if last_bytes == END_MARKER:
                    text_bytes = bytes(bytes_list[:-len(END_MARKER)])
                    try:
                        return text_bytes.decode('utf-8')
                    except:
                        try:
                            return text_bytes.decode('cp1251')
                        except:
                            return text_bytes.decode('latin-1')
    
    # Если не нашли маркер
    try:
        return bytes(bytes_list).decode('utf-8')
    except:
        return bytes(bytes_list).decode('latin-1')