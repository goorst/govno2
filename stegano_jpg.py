import numpy as np
from PIL import Image
import io
from scipy.fftpack import dct, idct

def rgb_to_ycbcr(rgb):
    """
    Конвертирует RGB в YCbCr по стандарту ITU-R BT.601 (используется в JPEG).
    
    Y (яркость) - воспринимаемая яркость пикселя:
    Коэффициенты отражают чувствительность человеческого глаза к цветам:
    - 0.299 (R): глаз менее чувствителен к красному (~30%)
    - 0.587 (G): глаз наиболее чувствителен к зеленому (~59%) 
    - 0.114 (B): глаз наименее чувствителен к синему (~11%)
    
    Cb (цветоразностный синий) = 0.564 * (B - Y) + 128:
    Представляет разницу между синим каналом и яркостью.
    Смещение +128 центрирует значения для 8-битного представления (0-255).
    Коэффициенты получены подстановкой Y в формулу:
    - -0.1687 = -0.299 * 0.564
    - -0.3313 = -0.587 * 0.564  
    -  0.5    = (1 - 0.114) * 0.564 = 0.886 * 0.564 ≈ 0.5
    
    Cr (цветоразностный красный) = 0.713 * (R - Y) + 128:
    Представляет разницу между красным каналом и яркостью.
    Смещение +128 центрирует значения для 8-битного представления.
    Коэффициенты получены подстановкой Y в формулу:
    -  0.5    = (1 - 0.299) * 0.713 = 0.701 * 0.713 ≈ 0.5
    - -0.4187 = -0.587 * 0.713
    - -0.0813 = -0.114 * 0.713
    """
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    
    # Y  =  0.299*R + 0.587*G + 0.114*B
    y = 0.299 * r + 0.587 * g + 0.114 * b
    
    # Cb = -0.1687*R - 0.3313*G + 0.5*B + 128
    cb = -0.1687 * r - 0.3313 * g + 0.5 * b + 128
    
    # Cr =  0.5*R - 0.4187*G - 0.0813*B + 128
    cr = 0.5 * r - 0.4187 * g - 0.0813 * b + 128
    
    return np.stack([y, cb, cr], axis=2)


def ycbcr_to_rgb(ycbcr):
    """
    Конвертирует YCbCr обратно в RGB по стандарту ITU-R BT.601.
    
    Обратное преобразование получено решением системы уравнений
    относительно R, G, B из прямого преобразования:
    
    Из прямого преобразования имеем:
    Y  =  0.299*R + 0.587*G + 0.114*B
    Cb = -0.1687*R - 0.3313*G + 0.5*B + 128  =>  Cb' = Cb - 128
    Cr =  0.5*R - 0.4187*G - 0.0813*B + 128  =>  Cr' = Cr - 128
    
    Решая систему, получаем:
    
    R = Y + 1.402 * Cr'
    где 1.402 = 1 / 0.713 (коэффициент при Cr в прямом преобразовании)
    Физический смысл: красный канал = яркость + усиленная красно-цветовая разница
    
    B = Y + 1.772 * Cb'
    где 1.772 = 1 / 0.564 (коэффициент при Cb в прямом преобразовании)
    Физический смысл: синий канал = яркость + усиленная сине-цветовая разница
    
    G = Y - 0.34414 * Cb' - 0.71414 * Cr'
    где коэффициенты получены подстановкой R и B в уравнение для Y:
    0.34414 = (0.114 * 1.772) / 0.587 (компенсация синего в зеленом)
    0.71414 = (0.299 * 1.402) / 0.587 (компенсация красного в зеленом)
    Физический смысл: зеленый = яркость - вклад синего - вклад красного
    """
    # Извлекаем каналы и убираем смещение 128 для цветоразностных компонент
    y = ycbcr[:, :, 0]           # Яркость (0-255)
    cb = ycbcr[:, :, 1] - 128    # Cb' (синяя цветоразность, центрированная вокруг 0)
    cr = ycbcr[:, :, 2] - 128    # Cr' (красная цветоразность, центрированная вокруг 0)
    
    # R = Y + 1.402 * Cr'
    r = y + 1.402 * cr
    
    # G = Y - 0.34414 * Cb' - 0.71414 * Cr'
    g = y - 0.34414 * cb - 0.71414 * cr
    
    # B = Y + 1.772 * Cb'
    b = y + 1.772 * cb
    
    return np.stack([r, g, b], axis=2)

def hide_text_jpg(image_file, text: str) -> io.BytesIO:
    """
    DCT алгоритм для скрытия текста в JPG.
    Модифицирует только Y канал, сохраняя цветность.
    """
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Преобразуем в numpy array
    img_array = np.array(img, dtype=np.float32)
    height, width, _ = img_array.shape
    
    # Конвертируем в YCbCr
    ycbcr = rgb_to_ycbcr(img_array)
    y_channel = ycbcr[:, :, 0].copy()
    
    # Кодируем текст
    text_bytes = text.encode('utf-8')
    text_bytes += b'\x00'
    
    bits = []
    for byte in text_bytes:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    
    # Размеры в блоках
    blocks_h = height // 8
    blocks_w = width // 8
    
    max_bits = blocks_h * blocks_w
    if len(bits) > max_bits:
        raise ValueError(f"Текст слишком длинный. Максимум: {max_bits//8} байт")
    
    bit_index = 0
    quant_step = 30.0  # Большой шаг для устойчивости
    
    for y_block in range(blocks_h):
        for x_block in range(blocks_w):
            if bit_index >= len(bits):
                break
            
            y_start = y_block * 8
            x_start = x_block * 8
            block = y_channel[y_start:y_start+8, x_start:x_start+8].copy()
            
            # DCT
            dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
            
            # Используем коэффициент (4,4) - средняя частота
            coef_pos = (4, 4)
            
            if bits[bit_index] == 1:
                # Устанавливаем положительное значение
                dct_block[coef_pos] = quant_step * 2
            else:
                # Устанавливаем отрицательное значение
                dct_block[coef_pos] = -quant_step * 2
            
            bit_index += 1
            
            # Обратное DCT
            idct_block = idct(idct(dct_block.T, norm='ortho').T, norm='ortho')
            y_channel[y_start:y_start+8, x_start:x_start+8] = idct_block
        
        if bit_index >= len(bits):
            break
    
    # Восстанавливаем Y канал
    ycbcr[:, :, 0] = y_channel
    
    # Конвертируем обратно в RGB
    rgb_array = ycbcr_to_rgb(ycbcr)
    rgb_array = np.clip(rgb_array, 0, 255).astype(np.uint8)
    
    encoded_img = Image.fromarray(rgb_array, 'RGB')
    
    # Сохраняем
    output = io.BytesIO()
    encoded_img.save(output, format='JPEG', quality=100, subsampling='4:4:4')
    output.seek(0)
    
    return output

def extract_text_jpg(image_file) -> str:
    """
    Извлекает текст из JPG с DCT алгоритмом.
    """
    image_file.seek(0)
    img = Image.open(image_file)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    img_array = np.array(img, dtype=np.float32)
    height, width, _ = img_array.shape
    
    # Конвертируем в YCbCr и берем Y канал
    ycbcr = rgb_to_ycbcr(img_array)
    y_channel = ycbcr[:, :, 0]
    
    blocks_h = height // 8
    blocks_w = width // 8
    
    bits = []
    bytes_list = []
    
    for y_block in range(blocks_h):
        for x_block in range(blocks_w):
            y_start = y_block * 8
            x_start = x_block * 8
            block = y_channel[y_start:y_start+8, x_start:x_start+8]
            
            # DCT
            dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
            
            coef_pos = (4, 4)
            value = dct_block[coef_pos]
            
            # Определяем бит
            bit = 1 if value > 0 else 0
            bits.append(bit)
            
            if len(bits) >= 8:
                byte_val = 0
                for i in range(8):
                    byte_val = (byte_val << 1) | bits[i]
                bits = bits[8:]
                
                if byte_val == 0:
                    try:
                        return bytes(bytes_list).decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            return bytes(bytes_list).decode('cp1251')
                        except:
                            return bytes(bytes_list).decode('latin-1')
                
                bytes_list.append(byte_val)
    
    try:
        return bytes(bytes_list).decode('utf-8')
    except UnicodeDecodeError:
        return bytes(bytes_list).decode('latin-1')