from PIL import Image
import io
import hashlib
import random

def generate_seed_from_key(key: str = "default_seed") -> int:
    """Генерирует seed из ключа для воспроизводимости"""
    hash_object = hashlib.sha256(key.encode())
    return int.from_bytes(hash_object.digest()[:8], 'big')

def generate_pseudo_random_positions(total_pixels: int, total_bits: int, seed_key: str = "stegano_key") -> list:
    """
    Генерирует псевдослучайные позиции для встраивания битов
    """
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
        
    text_bytes = text.encode('utf-8')
    text_bytes += b'\x00'
    
    bits = []
    for byte in text_bytes:
        bits.extend(format(byte, '08b'))
    bits_str = ''.join(bits)
    
    total_pixels = img.width * img.height
    total_bits_available = total_pixels * 3
    
    if len(bits_str) > total_bits_available:
        raise ValueError(f"Текст слишком длинный. Максимум: {total_bits_available//8} байт")
    
    positions = generate_pseudo_random_positions(total_pixels, len(bits_str), seed_key)
    
    encoded_img = img.copy()
    pixels = encoded_img.load()
    
    pixel_array = []
    for y in range(img.height):
        for x in range(img.width):
            pixel_array.append((x, y))
    
    for bit_idx, (pixel_idx, channel) in enumerate(positions):
        if bit_idx >= len(bits_str):
            break
            
        x, y = pixel_array[pixel_idx]
        r, g, b = encoded_img.getpixel((x, y))
        
        if channel == 0:
            r = (r & 0xFE) | int(bits_str[bit_idx])
        elif channel == 1:
            g = (g & 0xFE) | int(bits_str[bit_idx])
        else:
            b = (b & 0xFE) | int(bits_str[bit_idx])
            
        pixels[x, y] = (r, g, b)
    
    output = io.BytesIO()
    encoded_img.save(output, format='PNG', optimize=True)
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
    
    pixel_array = []
    for y in range(img.height):
        for x in range(img.width):
            pixel_array.append((x, y))
    
    # Начинаем с извлечения достаточного количества битов
    max_bits = total_pixels * 3
    bits = []
    bytes_list = []
    
    positions = generate_pseudo_random_positions(total_pixels, max_bits, seed_key)
    
    
    for bit_idx, (pixel_idx, channel) in enumerate(positions):
        x, y = pixel_array[pixel_idx]
        r, g, b = img.getpixel((x, y))
        
        # Извлекаем бит из соответствующего канала
        if channel == 0:
            bit = str(r & 1)
        elif channel == 1:
            bit = str(g & 1)
        else:
            bit = str(b & 1)
            
        bits.append(bit)
        
        # Каждые 8 бит преобразуем в байт
        if len(bits) >= 8:
            byte_bits = bits[:8]
            bits = bits[8:]
            
            byte_value = int(''.join(byte_bits), 2)
            
            # Проверяем на терминатор
            if byte_value == 0:
                try:
                    return bytes(bytes_list).decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        return bytes(bytes_list).decode('cp1251')
                    except:
                        return bytes(bytes_list).decode('latin-1')
            
            bytes_list.append(byte_value)
    
    # Если не нашли терминатор
    try:
        return bytes(bytes_list).decode('utf-8')
    except UnicodeDecodeError:
        return bytes(bytes_list).decode('latin-1')