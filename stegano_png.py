# from PIL import Image
# import io

# def hide_text_png(image_file, text: str) -> io.BytesIO:
#     """
#     Скрывает текст в PNG-изображении с помощью LSB-стеганографии.
#     """
#     # Сбрасываем позицию файла
#     image_file.seek(0)
#     img = Image.open(image_file)
    
#     if img.mode != 'RGB':
#         img = img.convert('RGB')
    
#     # Добавляем терминатор
#     text += '\x00'
    
#     # Преобразуем текст в биты
#     bits = ''.join(format(ord(char), '08b') for char in text)
    
#     # Проверяем размер
#     total_bits = img.width * img.height * 3
#     if len(bits) > total_bits:
#         raise ValueError("Текст слишком длинный для данного изображения.")
    
#     # Создаём копию для модификации
#     encoded_img = img.copy()
#     pixels = encoded_img.load()
#     bit_index = 0
    
#     # Проходим по всем пикселям
#     for y in range(img.height):
#         for x in range(img.width):
#             if bit_index >= len(bits):
#                 break
                
#             r, g, b = img.getpixel((x, y))
            
#             # Меняем младший бит
#             if bit_index < len(bits):
#                 new_r = (r & 0xFE) | int(bits[bit_index])
#                 bit_index += 1
#             else:
#                 new_r = r
                
#             if bit_index < len(bits):
#                 new_g = (g & 0xFE) | int(bits[bit_index])
#                 bit_index += 1
#             else:
#                 new_g = g
                
#             if bit_index < len(bits):
#                 new_b = (b & 0xFE) | int(bits[bit_index])
#                 bit_index += 1
#             else:
#                 new_b = b
            
#             pixels[x, y] = (new_r, new_g, new_b)
            
#         if bit_index >= len(bits):
#             break
    
#     # Сохраняем результат
#     output = io.BytesIO()
#     encoded_img.save(output, format='PNG')
#     output.seek(0)
#     return output

# def extract_text_png(image_file) -> str:
#     """
#     Извлекает скрытый текст из PNG-изображения с помощью LSB-стеганографии.
#     """
#     # Сбрасываем позицию файла
#     image_file.seek(0)
#     img = Image.open(image_file)
    
#     if img.mode != 'RGB':
#         img = img.convert('RGB')
    
#     bits = []
#     text = ""
    
#     # Проходим по всем пикселям и извлекаем младшие биты
#     for y in range(img.height):
#         for x in range(img.width):
#             r, g, b = img.getpixel((x, y))
            
#             # Извлекаем младшие биты каждого канала
#             bits.append(str(r & 1))
#             bits.append(str(g & 1))
#             bits.append(str(b & 1))
            
#             # Каждые 8 бит пытаемся преобразовать в символ
#             if len(bits) >= 8:
#                 byte_bits = bits[:8]
#                 bits = bits[8:]
                
#                 char_code = int(''.join(byte_bits), 2)
                
#                 # Если встретили нулевой байт - конец текста
#                 if char_code == 0:
#                     return text
                
#                 text += chr(char_code)
    
#     return text


from PIL import Image
import io

def hide_text_png(image_file, text: str) -> io.BytesIO:
    """
    Скрывает текст в PNG-изображении с помощью LSB-стеганографии.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Добавляем терминатор
    text += '\x00'
    
    # Преобразуем текст в биты
    bits = ''.join(format(ord(char), '08b') for char in text)
    
    # Проверяем размер
    total_bits = img.width * img.height * 3
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
                
            r, g, b = img.getpixel((x, y))
            
            # Меняем младший бит
            if bit_index < len(bits):
                new_r = (r & 0xFE) | int(bits[bit_index])
                bit_index += 1
            else:
                new_r = r
                
            if bit_index < len(bits):
                new_g = (g & 0xFE) | int(bits[bit_index])
                bit_index += 1
            else:
                new_g = g
                
            if bit_index < len(bits):
                new_b = (b & 0xFE) | int(bits[bit_index])
                bit_index += 1
            else:
                new_b = b
            
            pixels[x, y] = (new_r, new_g, new_b)
            
        if bit_index >= len(bits):
            break
    
    # Сохраняем результат
    output = io.BytesIO()
    encoded_img.save(output, format='PNG', optimize=True)
    output.seek(0)
    return output

def extract_text_png(image_file) -> str:
    """
    Извлекает скрытый текст из PNG-изображения с помощью LSB-стеганографии.
    """
    # Сбрасываем позицию файла
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    bits = []
    text = ""
    
    # Проходим по всем пикселям и извлекаем младшие биты
    for y in range(img.height):
        for x in range(img.width):
            r, g, b = img.getpixel((x, y))
            
            # Извлекаем младшие биты каждого канала
            bits.append(str(r & 1))
            bits.append(str(g & 1))
            bits.append(str(b & 1))
            
            # Каждые 8 бит пытаемся преобразовать в символ
            if len(bits) >= 8:
                byte_bits = bits[:8]
                bits = bits[8:]
                
                char_code = int(''.join(byte_bits), 2)
                
                # Если встретили нулевой байт - конец текста
                if char_code == 0:
                    return text
                
                text += chr(char_code)
    
    return text