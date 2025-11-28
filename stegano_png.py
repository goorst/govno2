from PIL import Image
import io

def hide_text_png(image_path: str, text: str) -> io.BytesIO:
    """
    Скрывает текст в PNG-изображении с помощью LSB-стеганографии.
    Возвращает BytesIO с новым изображением.
    
    Поддерживает только RGB PNG-изображения.
    Текст завершается нулевым байтом (\x00) как маркер конца.
    """
    # Открываем изображение
    img = Image.open(image_path)
    
    # Конвертируем в RGB, если нужно
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Добавляем терминатор конца текста
    text += '\x00'
    
    # Преобразуем текст в последовательность битов
    bits = ''.join(format(ord(char), '08b') for char in text)
    
    # Проверяем, хватает ли пикселей
    total_bits = img.width * img.height * 3  # 3 канала (R, G, B)
    if len(bits) > total_bits:
        raise ValueError("Текст слишком длинный для данного изображения.")
    
    # Создаём копию изображения для модификации
    encoded_img = img.copy()
    pixels = encoded_img.load()
    bit_index = 0
    
    # Проходим по всем пикселям
    for y in range(img.height):
        for x in range(img.width):
            if bit_index >= len(bits):
                break
                
            r, g, b = img.getpixel((x, y))
            
            # Меняем младший бит каждого канала
            new_r = (r & 0xFE) | int(bits[bit_index])
            bit_index += 1
            new_g = (g & 0xFE) | (int(bits[bit_index]) if bit_index < len(bits) else 0)
            bit_index += 1
            new_b = (b & 0xFE) | (int(bits[bit_index]) if bit_index < len(bits) else 0)
            bit_index += 1
            
            pixels[x, y] = (new_r, new_g, new_b)
        if bit_index >= len(bits):
            break
    
    # Сохраняем результат в BytesIO
    output = io.BytesIO()
    encoded_img.save(output, format='PNG')
    output.seek(0)  # Важно: сбросить указатель в начало
    return output