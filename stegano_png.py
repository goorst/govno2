from PIL import Image
import io
import hashlib
import random

# Уникальный маркер конца текста (5 байт)
END_MARKER = b'\x00\xFF\x00\xFF\x00'

def generate_seed_from_key(key: str = "default_seed") -> int:
    hash_object = hashlib.sha256(key.encode())
    return int.from_bytes(hash_object.digest()[:8], 'big')

def generate_pseudo_random_positions(total_pixels: int, total_bits: int, seed_key: str = "stegano_key") -> list:
    seed = generate_seed_from_key(seed_key)
    random.seed(seed)
    all_positions = [(p, c) for p in range(total_pixels) for c in range(3)]
    selected_positions = random.sample(all_positions, min(total_bits, len(all_positions)))
    return selected_positions

def hide_text_png(image_file, text: str, seed_key: str = "stegano_key") -> io.BytesIO:
    """
    Скрывает текст в PNG-изображении с помощью LSB-стеганографии 
    с псевдослучайным распределением битов.
    """
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Кодируем текст в UTF-8 байты
    text_bytes = text.encode('utf-8')
    
    # Добавляем уникальный маркер конца
    text_bytes += END_MARKER
    
    # Преобразуем байты в биты
    bits = []
    for byte in text_bytes:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    
    # Проверяем размер
    total_pixels = img.width * img.height
    total_bits_available = total_pixels * 3
    
    if len(bits) > total_bits_available:
        raise ValueError(f"Текст слишком длинный. Максимум: {total_bits_available//8} байт")
    
    # Генерируем псевдослучайные позиции
    positions = generate_pseudo_random_positions(total_pixels, len(bits), seed_key)
    
    # Создаём копию для модификации
    encoded_img = img.copy()
    pixels = encoded_img.load()
    
    # Создаем массив пикселей для быстрого доступа
    pixel_array = []
    for y in range(img.height):
        for x in range(img.width):
            pixel_array.append((x, y))
    
    # Встраиваем биты в псевдослучайные позиции
    for bit_idx, (pixel_idx, channel) in enumerate(positions):
        if bit_idx >= len(bits):
            break
            
        x, y = pixel_array[pixel_idx]
        r, g, b = encoded_img.getpixel((x, y))
        
        bit_val = bits[bit_idx]
        
        # Изменяем соответствующий канал
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
    Извлекает скрытый текст из PNG-изображения с помощью LSB-стеганографии
    с псевдослучайным распределением битов.
    """
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    total_pixels = img.width * img.height
    
    # Создаем массив пикселей для быстрого доступа по индексу
    pixel_array = []
    for y in range(img.height):
        for x in range(img.width):
            pixel_array.append((x, y))
    
    # Максимальное количество бит
    max_bits = total_pixels * 3
    bits = []
    bytes_list = []
    
    # Генерируем псевдослучайные позиции
    positions = generate_pseudo_random_positions(total_pixels, max_bits, seed_key)
    
    # Извлекаем биты в порядке, определенном псевдослучайной последовательностью
    for bit_idx, (pixel_idx, channel) in enumerate(positions):
        x, y = pixel_array[pixel_idx]
        r, g, b = img.getpixel((x, y))
        
        # Извлекаем бит из соответствующего канала
        if channel == 0:
            bits.append(r & 1)
        elif channel == 1:
            bits.append(g & 1)
        else:
            bits.append(b & 1)
        
        # Каждые 8 бит преобразуем в байт
        if len(bits) >= 8:
            byte_val = 0
            for i in range(8):
                byte_val = (byte_val << 1) | bits[i]
            bits = bits[8:]
            
            bytes_list.append(byte_val)
            
            # Проверяем на маркер конца (последние 5 байт)
            if len(bytes_list) >= len(END_MARKER):
                last_bytes = bytes(bytes_list[-len(END_MARKER):])
                if last_bytes == END_MARKER:
                    # Убираем маркер и декодируем
                    text_bytes = bytes(bytes_list[:-len(END_MARKER)])
                    try:
                        return text_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            return text_bytes.decode('cp1251')
                        except:
                            return text_bytes.decode('latin-1')
    
    # Если не нашли маркер
    try:
        return bytes(bytes_list).decode('utf-8')
    except UnicodeDecodeError:
        return bytes(bytes_list).decode('latin-1')