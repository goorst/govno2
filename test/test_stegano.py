import sys
import os
import io
import csv
import time
import random
import string
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib

# Для работы без GUI
matplotlib.use('Agg')

from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr

from stegano_png import hide_text_png, extract_text_png
from stegano_jpg import hide_text_jpg, extract_text_jpg
from stegano_bmp import hide_text_bmp, extract_text_bmp
from stegano_webp import hide_text_webp, extract_text_webp

class SteganoAnalyzer:
    """Класс для анализа и тестирования стеганографических алгоритмов"""
    
    # Конфигурация алгоритмов
    ALGORITHMS = {
        'png': {
            'hide': hide_text_png,
            'extract': extract_text_png,
            'format_dir': 'png',
            'extension': '.png',
            'lossless': True,
            'color': '#2ecc71'
        },
        'bmp': {
            'hide': hide_text_bmp,
            'extract': extract_text_bmp,
            'format_dir': 'bmp',
            'extension': '.bmp',
            'lossless': True,
            'color': '#3498db'
        },
        'webp': {
            'hide': hide_text_webp,
            'extract': extract_text_webp,
            'format_dir': 'webp',
            'extension': '.webp',
            'lossless': True,
            'color': '#9b59b6'
        },
        'jpg': {
            'hide': hide_text_jpg,
            'extract': extract_text_jpg,
            'format_dir': 'jpg',
            'extension': '.jpg',
            'lossless': False,
            'color': '#e74c3c'
        }
    }
    
    # Ключ для псевдослучайной последовательности
    STEGANO_KEY = "my_secret_stegano_key_2024"
    
    def __init__(self, test_images_dir: str = 'test/test_images', output_dir: str = 'test/test_results'):
        """
        Инициализация анализатора
        
        Args:
            test/test_images_dir: директория с тестовыми изображениями
            test/output_dir: директория для результатов
        """
        self.test_images_dir = Path(test_images_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем поддиректории
        (self.output_dir / 'charts').mkdir(exist_ok=True)
        (self.output_dir / 'charts' / 'quality_metrics').mkdir(exist_ok=True)
        (self.output_dir / 'charts' / 'time_analysis').mkdir(exist_ok=True)
        (self.output_dir / 'charts' / 'per_image_analysis').mkdir(exist_ok=True)
        (self.output_dir / 'stego_images').mkdir(exist_ok=True)
        (self.output_dir / 'reports').mkdir(exist_ok=True)
        
        self.results = []
        self.test_images = {}
        self.image_metrics_cache = {}
        
    def find_test_images(self) -> Dict[str, List[Path]]:
        """Находит все тестовые изображения в соответствующих поддиректориях"""
        self.test_images = {}
        
        for algo_name, algo_info in self.ALGORITHMS.items():
            format_dir = self.test_images_dir / algo_info['format_dir']
            
            if format_dir.exists():
                # Ищем все изображения соответствующего формата
                images = []
                for ext in [algo_info['extension'], algo_info['extension'].upper()]:
                    images.extend(format_dir.glob(f'*{ext}'))
                
                self.test_images[algo_name] = images
                print(f"Найдено {len(images)} изображений для {algo_name.upper()} в {format_dir}")
            else:
                print(f"Директория {format_dir} не найдена для {algo_name.upper()}")
                self.test_images[algo_name] = []
                
        total_images = sum(len(imgs) for imgs in self.test_images.values())
        print(f"Всего найдено {total_images} тестовых изображений")
        
        return self.test_images
    
    def generate_test_texts(self) -> List[Tuple[str, str, int]]:
        """
        Генерирует тестовые тексты разной длины и содержания
        
        Returns:
            List of (name, text, length)
        """
        texts = []
        
        # Короткий текст (только латиница)
        texts.append(('short_eng', 'Hello World!', 12))
        
        # Короткий текст с кириллицей
        texts.append(('short_rus', 'Привет, мир!', 12))
        
        # Средний текст
        medium_text = """Это тестовый текст среднего размера. 
        Он содержит несколько предложений на русском языке.
        Предназначен для проверки стеганографических алгоритмов."""
        texts.append(('medium_rus', medium_text, len(medium_text.encode('utf-8'))))
        
        # Длинный текст
        long_text = ("""Lorem ipsum dolor sit amet, consectetur adipiscing elit. """ * 5 +
                    """Русский текст для проверки кириллицы. """ * 5)
        texts.append(('long_mixed', long_text, len(long_text.encode('utf-8'))))
        
        # Случайный текст разной длины
        for size in [100, 500, 1000, 2000]:
            random_text = ''.join(random.choices(
                string.ascii_letters + string.digits + ' АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя',
                k=size
            ))
            texts.append((f'random_{size}', random_text, size))
        
        return texts
    
    def calculate_detailed_metrics(self, original: Image.Image, stego: Image.Image) -> Dict[str, float]:
        """
        Вычисляет детальные метрики качества между оригиналом и стего-изображением
        """
        # Конвертируем в numpy массивы
        orig_array = np.array(original.convert('RGB'))
        stego_array = np.array(stego.convert('RGB'))
        
        metrics = {}
        
        # Базовые метрики
        metrics['psnr'] = psnr(orig_array, stego_array, data_range=255)
        
        # SSIM
        try:
            metrics['ssim'] = ssim(orig_array, stego_array, channel_axis=2, data_range=255)
        except Exception:
            metrics['ssim'] = 1.0
        
        # MSE (Mean Squared Error)
        mse_value = np.mean((orig_array.astype(float) - stego_array.astype(float)) ** 2)
        metrics['mse'] = mse_value
        
        # RMSE (Root Mean Squared Error)
        metrics['rmse'] = np.sqrt(mse_value)
        
        # MAE (Mean Absolute Error)
        metrics['mae'] = np.mean(np.abs(orig_array.astype(float) - stego_array.astype(float)))
        
        # Максимальная разница
        metrics['max_diff'] = np.max(np.abs(orig_array.astype(float) - stego_array.astype(float)))
        
        # Процент измененных пикселей
        changed_pixels = np.sum(np.any(orig_array != stego_array, axis=2))
        total_pixels = orig_array.shape[0] * orig_array.shape[1]
        metrics['changed_pixels_percent'] = (changed_pixels / total_pixels) * 100
        
        # Среднее изменение интенсивности
        metrics['avg_intensity_change'] = np.mean(np.abs(orig_array.astype(float) - stego_array.astype(float)))
        
        # Медианное изменение
        metrics['median_intensity_change'] = np.median(np.abs(orig_array.astype(float) - stego_array.astype(float)))
        
        # Стандартное отклонение разницы
        metrics['std_intensity_change'] = np.std(np.abs(orig_array.astype(float) - stego_array.astype(float)))
        
        # Нормализованная кросс-корреляция (NCC)
        orig_norm = orig_array - np.mean(orig_array)
        stego_norm = stego_array - np.mean(stego_array)
        ncc = np.sum(orig_norm * stego_norm) / (np.sqrt(np.sum(orig_norm**2) * np.sum(stego_norm**2)) + 1e-10)
        metrics['ncc'] = ncc
        
        # Структурное содержание (SC)
        sc = np.sum(orig_array**2) / (np.sum(stego_array**2) + 1e-10)
        metrics['structural_content'] = sc
        
        # Средняя разница (AD)
        metrics['average_difference'] = np.mean(orig_array.astype(float) - stego_array.astype(float))
        
        # SNR (Signal-to-Noise Ratio)
        signal_power = np.mean(orig_array.astype(float) ** 2)
        noise_power = mse_value
        if noise_power > 0:
            metrics['snr'] = 10 * np.log10(signal_power / noise_power)
        else:
            metrics['snr'] = float('inf')
        
        # Анализ по каналам RGB
        for i, channel in enumerate(['R', 'G', 'B']):
            channel_orig = orig_array[:, :, i]
            channel_stego = stego_array[:, :, i]
            
            metrics[f'{channel}_mse'] = np.mean((channel_orig.astype(float) - channel_stego.astype(float)) ** 2)
            metrics[f'{channel}_psnr'] = psnr(channel_orig, channel_stego, data_range=255)
            metrics[f'{channel}_mae'] = np.mean(np.abs(channel_orig.astype(float) - channel_stego.astype(float)))
            metrics[f'{channel}_changed_pixels'] = np.sum(channel_orig != channel_stego) / (channel_orig.shape[0] * channel_orig.shape[1]) * 100
        
        return metrics
    
    def calculate_capacity(self, image: Image.Image, algorithm: str) -> Dict[str, int]:
        """
        Рассчитывает емкость изображения для разных алгоритмов
        """
        width, height = image.size
        pixels = width * height
        channels = 3 if image.mode == 'RGB' else 1
        
        capacity = {}
        
        if algorithm in ['png', 'bmp', 'webp']:
            # LSB метод: 1 бит на канал
            capacity['bits'] = pixels * channels
            capacity['bytes'] = capacity['bits'] // 8
            capacity['chars'] = capacity['bytes']
        elif algorithm == 'jpg':
            # DCT метод: 1 бит на блок 8x8 на канал
            blocks_h = height // 8
            blocks_w = width // 8
            capacity['bits'] = blocks_h * blocks_w * channels
            capacity['bytes'] = capacity['bits'] // 8
            capacity['chars'] = capacity['bytes']
        
        return capacity
    
    def run_single_test(self, image_path: Path, algorithm: str, 
                        text_name: str, text: str) -> Optional[Dict]:
        """
        Запускает одиночный тест
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'image': str(image_path.name),
            'image_path': str(image_path),
            'image_size': str(Image.open(image_path).size),
            'image_width': Image.open(image_path).width,
            'image_height': Image.open(image_path).height,
            'image_pixels': Image.open(image_path).width * Image.open(image_path).height,
            'algorithm': algorithm,
            'text_name': text_name,
            'text_length_chars': len(text),
            'text_length_bytes': len(text.encode('utf-8')),
            'success': False,
            'extraction_success': False,
            'hide_time': 0,
            'extract_time': 0,
            'total_time': 0,
            'hide_speed_bps': 0,
            'extract_speed_bps': 0,
            'psnr': None,
            'ssim': None,
            'mse': None,
            'rmse': None,
            'mae': None,
            'max_diff': None,
            'snr': None,
            'ncc': None,
            'structural_content': None,
            'average_difference': None,
            'changed_pixels_percent': None,
            'avg_intensity_change': None,
            'median_intensity_change': None,
            'std_intensity_change': None,
            'R_mse': None, 'R_psnr': None, 'R_mae': None, 'R_changed_pixels': None,
            'G_mse': None, 'G_psnr': None, 'G_mae': None, 'G_changed_pixels': None,
            'B_mse': None, 'B_psnr': None, 'B_mae': None, 'B_changed_pixels': None,
            'capacity_bits': None,
            'capacity_bytes': None,
            'capacity_usage_percent': None,
            'file_size_original': 0,
            'file_size_stego': 0,
            'size_increase_percent': 0,
            'error': None
        }
        
        try:
            # Открываем оригинальное изображение
            original_img = Image.open(image_path)
            
            # Вычисляем емкость
            capacity = self.calculate_capacity(original_img, algorithm)
            result['capacity_bits'] = capacity['bits']
            result['capacity_bytes'] = capacity['bytes']
            
            # Процент использования емкости
            if capacity['bytes'] > 0:
                result['capacity_usage_percent'] = (result['text_length_bytes'] / capacity['bytes']) * 100
            
            # Размер файла оригинала
            result['file_size_original'] = image_path.stat().st_size
            
            # Проверяем, поместится ли текст
            if result['text_length_bytes'] > capacity['bytes']:
                result['error'] = f"Text too large: {result['text_length_bytes']} > {capacity['bytes']}"
                return result
            
            # Скрываем текст
            with open(image_path, 'rb') as f:
                image_data = io.BytesIO(f.read())
            
            start_time = time.perf_counter()
            try:
                hide_func = self.ALGORITHMS[algorithm]['hide']
                # Для LSB алгоритмов передаем ключ
                if algorithm in ['png', 'bmp', 'webp']:
                    stego_data = hide_func(image_data, text, self.STEGANO_KEY)
                else:
                    stego_data = hide_func(image_data, text)
                    
                result['hide_time'] = time.perf_counter() - start_time
                result['success'] = True
                
                # Вычисляем скорость скрытия (бит/сек)
                bits_hidden = result['text_length_bytes'] * 8
                if result['hide_time'] > 0:
                    result['hide_speed_bps'] = bits_hidden / result['hide_time']
                    
            except Exception as e:
                result['error'] = f"Hide error: {str(e)}"
                return result
            
            # Размер стего-файла
            result['file_size_stego'] = len(stego_data.getvalue())
            result['size_increase_percent'] = ((result['file_size_stego'] - result['file_size_original']) / 
                                               result['file_size_original']) * 100
            
            # Сохраняем стего-изображение
            stego_filename = f"{image_path.stem}_{algorithm}_{text_name}{self.ALGORITHMS[algorithm]['extension']}"
            stego_path = self.output_dir / 'stego_images' / stego_filename
            with open(stego_path, 'wb') as f:
                f.write(stego_data.getvalue())
            
            # Открываем стего-изображение для метрик
            stego_img = Image.open(stego_path)
            
            # Вычисляем детальные метрики качества
            metrics = self.calculate_detailed_metrics(original_img, stego_img)
            result.update(metrics)
            
            # Сохраняем метрики в кэш для анализа по изображениям
            img_key = f"{image_path.name}_{algorithm}"
            if img_key not in self.image_metrics_cache:
                self.image_metrics_cache[img_key] = {
                    'image_name': image_path.name,
                    'algorithm': algorithm,
                    'metrics': []
                }
            self.image_metrics_cache[img_key]['metrics'].append({
                'text_name': text_name,
                'text_size': result['text_length_bytes'],
                'psnr': metrics['psnr'],
                'ssim': metrics['ssim'],
                'mse': metrics['mse'],
                'snr': metrics['snr'],
                'ncc': metrics['ncc'],
                'changed_pixels': metrics['changed_pixels_percent']
            })
            
            # Извлекаем текст
            with open(stego_path, 'rb') as f:
                stego_data_for_extract = io.BytesIO(f.read())
            
            start_time = time.perf_counter()
            try:
                extract_func = self.ALGORITHMS[algorithm]['extract']
                # Для LSB алгоритмов передаем ключ
                if algorithm in ['png', 'bmp', 'webp']:
                    extracted_text = extract_func(stego_data_for_extract, self.STEGANO_KEY)
                else:
                    extracted_text = extract_func(stego_data_for_extract)
                    
                result['extract_time'] = time.perf_counter() - start_time
                result['total_time'] = result['hide_time'] + result['extract_time']
                
                # Вычисляем скорость извлечения (бит/сек)
                if result['extract_time'] > 0:
                    result['extract_speed_bps'] = bits_hidden / result['extract_time']
                
                # Проверяем корректность извлечения
                if extracted_text.strip() == text.strip():
                    result['extraction_success'] = True
                else:
                    result['error'] = f"Extraction mismatch"
                    
            except Exception as e:
                result['error'] = f"Extract error: {str(e)}"
                
        except Exception as e:
            result['error'] = f"General error: {str(e)}"
            
        return result
    
    def run_all_tests(self) -> List[Dict]:
        """
        Запускает все тесты на всех изображениях со всеми текстами
        """
        # Находим изображения
        if not self.test_images:
            self.find_test_images()
            
        if not any(self.test_images.values()):
            print("Нет тестовых изображений!")
            return []
            
        # Генерируем тестовые тексты
        test_texts = self.generate_test_texts()
        
        self.results = []
        
        # Подсчитываем общее количество тестов
        total_tests = sum(len(images) * len(test_texts) 
                         for algo, images in self.test_images.items())
        
        current_test = 0
        
        print(f"\nЗапуск тестов. Всего тестов: {total_tests}")
        print("=" * 80)
        
        for algo_name, images in self.test_images.items():
            if not images:
                continue
                
            print(f"\n{'='*40}")
            print(f"Тестирование алгоритма: {algo_name.upper()}")
            print(f"Количество изображений: {len(images)}")
            print(f"{'='*40}")
            
            for image_path in images:
                print(f"\n  Изображение: {image_path.name}")
                
                for text_name, text, length in test_texts:
                    current_test += 1
                    print(f"    [{current_test}/{total_tests}] Текст: {text_name} ({length} символов)", end='')
                    
                    result = self.run_single_test(image_path, algo_name, text_name, text)
                    
                    if result:
                        self.results.append(result)
                        if result['success'] and result['extraction_success']:
                            psnr_val = result['psnr'] if result['psnr'] != float('inf') else '∞'
                            print(f" ✓ PSNR: {psnr_val:.2f} dB, SSIM: {result['ssim']:.4f}, MSE: {result['mse']:.2f}")
                        else:
                            error_msg = result['error'][:50] if result['error'] else "Unknown error"
                            print(f" ✗ {error_msg}")
                    else:
                        print(" ✗ Ошибка выполнения")
        
        print("\n" + "=" * 80)
        successful = sum(1 for r in self.results if r['success'] and r['extraction_success'])
        print(f"Тестирование завершено. Успешных тестов: {successful}/{len(self.results)} ({successful/len(self.results)*100:.1f}%)")
        
        return self.results
    
    def save_results_to_csv(self, filename: str = 'test_results.csv'):
        """Сохраняет результаты в CSV файл"""
        if not self.results:
            print("Нет результатов для сохранения")
            return
            
        csv_path = self.output_dir / 'reports' / filename
        
        fieldnames = [
            'timestamp', 'image', 'image_size', 'image_width', 'image_height', 'image_pixels',
            'algorithm', 'text_name', 'text_length_chars', 'text_length_bytes', 
            'success', 'extraction_success', 'hide_time', 'extract_time', 'total_time',
            'hide_speed_bps', 'extract_speed_bps', 
            'psnr', 'ssim', 'mse', 'rmse', 'mae', 'max_diff', 'snr', 'ncc',
            'structural_content', 'average_difference', 'changed_pixels_percent',
            'avg_intensity_change', 'median_intensity_change', 'std_intensity_change',
            'R_mse', 'R_psnr', 'R_mae', 'R_changed_pixels',
            'G_mse', 'G_psnr', 'G_mae', 'G_changed_pixels',
            'B_mse', 'B_psnr', 'B_mae', 'B_changed_pixels',
            'capacity_bits', 'capacity_bytes', 'capacity_usage_percent',
            'file_size_original', 'file_size_stego', 'size_increase_percent', 'error'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.results)
            
        print(f"Результаты сохранены в {csv_path}")
    
    def analyze_quality_metrics(self):
        """Анализ метрик качества"""
        successful_tests = [r for r in self.results if r['success'] and r['extraction_success']]
        
        if not successful_tests:
            print("Нет успешных тестов для анализа качества")
            return
            
        quality_stats = {
            'overall': {},
            'by_algorithm': {},
            'by_text_size': {},
            'by_image': {}
        }
        
        # Общая статистика
        quality_stats['overall'] = {
            'avg_psnr': np.mean([r['psnr'] for r in successful_tests if r['psnr'] != float('inf')]),
            'std_psnr': np.std([r['psnr'] for r in successful_tests if r['psnr'] != float('inf')]),
            'avg_ssim': np.mean([r['ssim'] for r in successful_tests]),
            'std_ssim': np.std([r['ssim'] for r in successful_tests]),
            'avg_mse': np.mean([r['mse'] for r in successful_tests]),
            'std_mse': np.std([r['mse'] for r in successful_tests]),
            'avg_mae': np.mean([r['mae'] for r in successful_tests]),
            'avg_snr': np.mean([r['snr'] for r in successful_tests if r['snr'] != float('inf')]),
            'avg_ncc': np.mean([r['ncc'] for r in successful_tests]),
            'avg_changed_pixels': np.mean([r['changed_pixels_percent'] for r in successful_tests]),
        }
        
        # По алгоритмам
        for algo in self.ALGORITHMS.keys():
            algo_tests = [r for r in successful_tests if r['algorithm'] == algo]
            if algo_tests:
                quality_stats['by_algorithm'][algo] = {
                    'count': len(algo_tests),
                    'avg_psnr': np.mean([r['psnr'] for r in algo_tests if r['psnr'] != float('inf')]),
                    'std_psnr': np.std([r['psnr'] for r in algo_tests if r['psnr'] != float('inf')]),
                    'avg_ssim': np.mean([r['ssim'] for r in algo_tests]),
                    'std_ssim': np.std([r['ssim'] for r in algo_tests]),
                    'avg_mse': np.mean([r['mse'] for r in algo_tests]),
                    'std_mse': np.std([r['mse'] for r in algo_tests]),
                    'avg_rmse': np.mean([r['rmse'] for r in algo_tests]),
                    'avg_mae': np.mean([r['mae'] for r in algo_tests]),
                    'avg_snr': np.mean([r['snr'] for r in algo_tests if r['snr'] != float('inf')]),
                    'avg_ncc': np.mean([r['ncc'] for r in algo_tests]),
                    'avg_changed_pixels': np.mean([r['changed_pixels_percent'] for r in algo_tests]),
                    'min_psnr': np.min([r['psnr'] for r in algo_tests if r['psnr'] != float('inf')]),
                    'max_psnr': np.max([r['psnr'] for r in algo_tests if r['psnr'] != float('inf')]),
                }
                
                # Анализ по каналам
                for channel in ['R', 'G', 'B']:
                    quality_stats['by_algorithm'][algo][f'{channel}_avg_psnr'] = np.mean([r[f'{channel}_psnr'] for r in algo_tests])
                    quality_stats['by_algorithm'][algo][f'{channel}_avg_mse'] = np.mean([r[f'{channel}_mse'] for r in algo_tests])
        
        # Сохраняем статистику качества
        quality_stats_path = self.output_dir / 'reports' / 'quality_statistics.json'
        
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.float32, np.float64)):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            return obj
        
        with open(quality_stats_path, 'w', encoding='utf-8') as f:
            json.dump(convert_to_serializable(quality_stats), f, indent=2, ensure_ascii=False)
        
        return quality_stats
    
    def generate_quality_charts(self):
        """Генерирует графики метрик качества"""
        successful_tests = [r for r in self.results if r['success'] and r['extraction_success']]
        
        if not successful_tests:
            print("Нет успешных тестов для визуализации качества")
            return
            
        quality_charts_dir = self.output_dir / 'charts' / 'quality_metrics'
        algorithms = list(self.ALGORITHMS.keys())
        
        # 1. Сравнение основных метрик качества
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # PSNR
        ax = axes[0, 0]
        algo_psnr = {}
        for algo in algorithms:
            psnr_vals = [r['psnr'] for r in successful_tests 
                        if r['algorithm'] == algo and r['psnr'] != float('inf')]
            if psnr_vals:
                algo_psnr[algo] = psnr_vals
        
        if algo_psnr:
            bp = ax.boxplot([algo_psnr.get(algo, []) for algo in algorithms if algo in algo_psnr], 
                          labels=[a.upper() for a in algorithms if a in algo_psnr], 
                          patch_artist=True)
            for patch, algo in zip(bp['boxes'], [a for a in algorithms if a in algo_psnr]):
                patch.set_facecolor(self.ALGORITHMS[algo]['color'])
        
        ax.set_title('PSNR (чем больше, тем лучше)', fontsize=12, fontweight='bold')
        ax.set_ylabel('PSNR (dB)')
        ax.grid(True, alpha=0.3)
        
        # SSIM
        ax = axes[0, 1]
        algo_ssim = {}
        for algo in algorithms:
            ssim_vals = [r['ssim'] for r in successful_tests if r['algorithm'] == algo]
            if ssim_vals:
                algo_ssim[algo] = ssim_vals
        
        if algo_ssim:
            bp = ax.boxplot([algo_ssim.get(algo, []) for algo in algorithms if algo in algo_ssim],
                          labels=[a.upper() for a in algorithms if a in algo_ssim],
                          patch_artist=True)
            for patch, algo in zip(bp['boxes'], [a for a in algorithms if a in algo_ssim]):
                patch.set_facecolor(self.ALGORITHMS[algo]['color'])
        
        ax.set_title('SSIM (чем ближе к 1, тем лучше)', fontsize=12, fontweight='bold')
        ax.set_ylabel('SSIM')
        ax.grid(True, alpha=0.3)
        
        # MSE
        ax = axes[0, 2]
        algo_mse = {}
        for algo in algorithms:
            mse_vals = [r['mse'] for r in successful_tests if r['algorithm'] == algo]
            if mse_vals:
                algo_mse[algo] = mse_vals
        
        if algo_mse:
            bp = ax.boxplot([algo_mse.get(algo, []) for algo in algorithms if algo in algo_mse],
                          labels=[a.upper() for a in algorithms if a in algo_mse],
                          patch_artist=True)
            for patch, algo in zip(bp['boxes'], [a for a in algorithms if a in algo_mse]):
                patch.set_facecolor(self.ALGORITHMS[algo]['color'])
        
        ax.set_title('MSE (чем меньше, тем лучше)', fontsize=12, fontweight='bold')
        ax.set_ylabel('MSE')
        ax.set_yscale('log')
        ax.grid(True, alpha=0.3)
        
        # SNR
        ax = axes[1, 0]
        algo_snr = {}
        for algo in algorithms:
            snr_vals = [r['snr'] for r in successful_tests 
                       if r['algorithm'] == algo and r['snr'] != float('inf')]
            if snr_vals:
                algo_snr[algo] = snr_vals
        
        if algo_snr:
            bp = ax.boxplot([algo_snr.get(algo, []) for algo in algorithms if algo in algo_snr],
                          labels=[a.upper() for a in algorithms if a in algo_snr],
                          patch_artist=True)
            for patch, algo in zip(bp['boxes'], [a for a in algorithms if a in algo_snr]):
                patch.set_facecolor(self.ALGORITHMS[algo]['color'])
        
        ax.set_title('SNR (Signal-to-Noise Ratio)', fontsize=12, fontweight='bold')
        ax.set_ylabel('SNR (dB)')
        ax.grid(True, alpha=0.3)
        
        # NCC (Normalized Cross-Correlation)
        ax = axes[1, 1]
        algo_ncc = {}
        for algo in algorithms:
            ncc_vals = [r['ncc'] for r in successful_tests if r['algorithm'] == algo]
            if ncc_vals:
                algo_ncc[algo] = ncc_vals
        
        if algo_ncc:
            bp = ax.boxplot([algo_ncc.get(algo, []) for algo in algorithms if algo in algo_ncc],
                          labels=[a.upper() for a in algorithms if a in algo_ncc],
                          patch_artist=True)
            for patch, algo in zip(bp['boxes'], [a for a in algorithms if a in algo_ncc]):
                patch.set_facecolor(self.ALGORITHMS[algo]['color'])
        
        ax.set_title('NCC (чем ближе к 1, тем лучше)', fontsize=12, fontweight='bold')
        ax.set_ylabel('NCC')
        ax.grid(True, alpha=0.3)
        
        # Процент измененных пикселей
        ax = axes[1, 2]
        algo_changed = {}
        for algo in algorithms:
            changed_vals = [r['changed_pixels_percent'] for r in successful_tests if r['algorithm'] == algo]
            if changed_vals:
                algo_changed[algo] = changed_vals
        
        if algo_changed:
            bp = ax.boxplot([algo_changed.get(algo, []) for algo in algorithms if algo in algo_changed],
                          labels=[a.upper() for a in algorithms if a in algo_changed],
                          patch_artist=True)
            for patch, algo in zip(bp['boxes'], [a for a in algorithms if a in algo_changed]):
                patch.set_facecolor(self.ALGORITHMS[algo]['color'])
        
        ax.set_title('Процент измененных пикселей', fontsize=12, fontweight='bold')
        ax.set_ylabel('Изменено пикселей (%)')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(quality_charts_dir / 'main_quality_metrics.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 2. Сравнение метрик по каналам RGB
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        for idx, channel in enumerate(['R', 'G', 'B']):
            ax = axes[idx]
            
            channel_psnr = {}
            for algo in algorithms:
                psnr_vals = [r[f'{channel}_psnr'] for r in successful_tests 
                            if r['algorithm'] == algo and r[f'{channel}_psnr'] != float('inf')]
                if psnr_vals:
                    channel_psnr[algo] = psnr_vals
            
            if channel_psnr:
                x = np.arange(len(channel_psnr))
                means = [np.mean(vals) for vals in channel_psnr.values()]
                stds = [np.std(vals) for vals in channel_psnr.values()]
                
                bars = ax.bar([a.upper() for a in channel_psnr.keys()], means, 
                             yerr=stds, capsize=5,
                             color=[self.ALGORITHMS[a]['color'] for a in channel_psnr.keys()])
                
                ax.set_title(f'Канал {channel} - PSNR', fontsize=12, fontweight='bold')
                ax.set_ylabel('PSNR (dB)')
                ax.grid(True, alpha=0.3, axis='y')
                
                for bar, val in zip(bars, means):
                    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                           f'{val:.1f}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(quality_charts_dir / 'rgb_channel_psnr.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 3. Радарная диаграмма качества
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        quality_metrics = ['PSNR', 'SSIM', 'SNR', 'NCC', '1/MSE', 'Неизменность']
        num_vars = len(quality_metrics)
        
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        angles += angles[:1]
        
        for algo in algorithms:
            algo_tests = [r for r in successful_tests if r['algorithm'] == algo]
            if not algo_tests:
                continue
            
            # Нормализуем значения
            all_psnr = [np.mean([r['psnr'] for r in successful_tests if r['algorithm'] == a and r['psnr'] != float('inf')]) 
                       for a in algorithms]
            all_ssim = [np.mean([r['ssim'] for r in successful_tests if r['algorithm'] == a]) for a in algorithms]
            all_snr = [np.mean([r['snr'] for r in successful_tests if r['algorithm'] == a and r['snr'] != float('inf')]) 
                      for a in algorithms]
            all_ncc = [np.mean([r['ncc'] for r in successful_tests if r['algorithm'] == a]) for a in algorithms]
            all_inv_mse = [1 / (np.mean([r['mse'] for r in successful_tests if r['algorithm'] == a]) + 1) for a in algorithms]
            all_unchanged = [1 - np.mean([r['changed_pixels_percent'] for r in successful_tests if r['algorithm'] == a]) / 100 
                           for a in algorithms]
            
            max_vals = [max(all_psnr), max(all_ssim), max(all_snr), max(all_ncc), max(all_inv_mse), max(all_unchanged)]
            
            avg_psnr = np.mean([r['psnr'] for r in algo_tests if r['psnr'] != float('inf')])
            avg_ssim = np.mean([r['ssim'] for r in algo_tests])
            avg_snr = np.mean([r['snr'] for r in algo_tests if r['snr'] != float('inf')])
            avg_ncc = np.mean([r['ncc'] for r in algo_tests])
            avg_inv_mse = 1 / (np.mean([r['mse'] for r in algo_tests]) + 1)
            avg_unchanged = 1 - np.mean([r['changed_pixels_percent'] for r in algo_tests]) / 100
            
            values = [
                avg_psnr / max_vals[0] if max_vals[0] > 0 else 0,
                avg_ssim / max_vals[1] if max_vals[1] > 0 else 0,
                avg_snr / max_vals[2] if max_vals[2] > 0 else 0,
                avg_ncc / max_vals[3] if max_vals[3] > 0 else 0,
                avg_inv_mse / max_vals[4] if max_vals[4] > 0 else 0,
                avg_unchanged / max_vals[5] if max_vals[5] > 0 else 0
            ]
            values += values[:1]
            
            ax.plot(angles, values, 'o-', linewidth=2, label=algo.upper(), 
                   color=self.ALGORITHMS[algo]['color'])
            ax.fill(angles, values, alpha=0.15, color=self.ALGORITHMS[algo]['color'])
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(quality_metrics, fontsize=10)
        ax.set_ylim(0, 1)
        ax.set_title('Сравнение качества алгоритмов (нормализованные метрики)', 
                    fontsize=14, fontweight='bold', pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
        ax.grid(True)
        
        plt.tight_layout()
        plt.savefig(quality_charts_dir / 'quality_radar.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 4. Тепловая карта корреляции метрик
        fig, ax = plt.subplots(figsize=(10, 8))
        
        metric_names = ['PSNR', 'SSIM', 'MSE', 'SNR', 'NCC', 'MAE', 'Changed Pixels']
        metric_data = []
        
        for r in successful_tests:
            metric_data.append([
                r['psnr'] if r['psnr'] != float('inf') else 100,
                r['ssim'],
                r['mse'],
                r['snr'] if r['snr'] != float('inf') else 100,
                r['ncc'],
                r['mae'],
                r['changed_pixels_percent']
            ])
        
        metric_data = np.array(metric_data)
        corr_matrix = np.corrcoef(metric_data.T)
        
        im = ax.imshow(corr_matrix, cmap='coolwarm', vmin=-1, vmax=1)
        ax.set_xticks(np.arange(len(metric_names)))
        ax.set_yticks(np.arange(len(metric_names)))
        ax.set_xticklabels(metric_names, rotation=45, ha='right')
        ax.set_yticklabels(metric_names)
        ax.set_title('Корреляция метрик качества', fontsize=14, fontweight='bold')
        
        # Добавляем значения
        for i in range(len(metric_names)):
            for j in range(len(metric_names)):
                text = ax.text(j, i, f'{corr_matrix[i, j]:.2f}',
                             ha="center", va="center", color="black", fontsize=8)
        
        plt.colorbar(im, ax=ax)
        plt.tight_layout()
        plt.savefig(quality_charts_dir / 'metrics_correlation.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Графики качества сохранены в {quality_charts_dir}")
    
    def generate_per_image_analysis(self):
        """Генерирует анализ для каждого изображения"""
        successful_tests = [r for r in self.results if r['success'] and r['extraction_success']]
        
        if not successful_tests:
            return
            
        per_image_dir = self.output_dir / 'charts' / 'per_image_analysis'
        
        # Группируем по изображениям
        image_groups = {}
        for r in successful_tests:
            img_key = r['image']
            if img_key not in image_groups:
                image_groups[img_key] = []
            image_groups[img_key].append(r)
        
        # Создаем сводную таблицу по изображениям
        image_summary = []
        for img_name, tests in image_groups.items():
            summary = {
                'image': img_name,
                'tests_count': len(tests),
                'avg_psnr': np.mean([t['psnr'] for t in tests if t['psnr'] != float('inf')]),
                'avg_ssim': np.mean([t['ssim'] for t in tests]),
                'avg_mse': np.mean([t['mse'] for t in tests]),
                'avg_changed_pixels': np.mean([t['changed_pixels_percent'] for t in tests])
            }
            image_summary.append(summary)
        
        # Сохраняем сводку по изображениям
        summary_path = self.output_dir / 'reports' / 'image_summary.csv'
        with open(summary_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['image', 'tests_count', 'avg_psnr', 'avg_ssim', 'avg_mse', 'avg_changed_pixels'])
            writer.writeheader()
            writer.writerows(image_summary)
        
        # График: PSNR для каждого изображения по алгоритмам
        fig, ax = plt.subplots(figsize=(14, 8))
        
        images = list(set([r['image'] for r in successful_tests]))
        images.sort()
        
        x = np.arange(len(images))
        width = 0.2
        
        for i, algo in enumerate(self.ALGORITHMS.keys()):
            algo_psnr = []
            for img in images:
                img_tests = [r for r in successful_tests if r['image'] == img and r['algorithm'] == algo]
                if img_tests:
                    psnr_vals = [r['psnr'] for r in img_tests if r['psnr'] != float('inf')]
                    algo_psnr.append(np.mean(psnr_vals) if psnr_vals else 0)
                else:
                    algo_psnr.append(0)
            
            ax.bar(x + i*width, algo_psnr, width, label=algo.upper(), 
                  color=self.ALGORITHMS[algo]['color'])
        
        ax.set_xlabel('Изображение')
        ax.set_ylabel('PSNR (dB)')
        ax.set_title('PSNR для каждого изображения по алгоритмам', fontsize=14, fontweight='bold')
        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels([img[:20] + '...' if len(img) > 20 else img for img in images], rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(per_image_dir / 'psnr_per_image.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Анализ по изображениям сохранен в {per_image_dir}")
    
    def analyze_time_performance(self):
        """Детальный анализ временных характеристик"""
        successful_tests = [r for r in self.results if r['success'] and r['extraction_success']]
        
        if not successful_tests:
            print("Нет успешных тестов для анализа времени")
            return
            
        time_stats = {
            'overall': {},
            'by_algorithm': {},
            'by_text_size': {},
            'by_image_size': {}
        }
        
        # Общая статистика
        time_stats['overall'] = {
            'avg_hide_time': np.mean([r['hide_time'] for r in successful_tests]),
            'std_hide_time': np.std([r['hide_time'] for r in successful_tests]),
            'avg_extract_time': np.mean([r['extract_time'] for r in successful_tests]),
            'std_extract_time': np.std([r['extract_time'] for r in successful_tests]),
            'avg_total_time': np.mean([r['total_time'] for r in successful_tests]),
            'std_total_time': np.std([r['total_time'] for r in successful_tests]),
            'avg_hide_speed': np.mean([r['hide_speed_bps'] for r in successful_tests if r['hide_speed_bps'] > 0]),
            'avg_extract_speed': np.mean([r['extract_speed_bps'] for r in successful_tests if r['extract_speed_bps'] > 0]),
        }
        
        # По алгоритмам
        for algo in self.ALGORITHMS.keys():
            algo_tests = [r for r in successful_tests if r['algorithm'] == algo]
            if algo_tests:
                time_stats['by_algorithm'][algo] = {
                    'count': len(algo_tests),
                    'avg_hide_time': np.mean([r['hide_time'] for r in algo_tests]),
                    'std_hide_time': np.std([r['hide_time'] for r in algo_tests]),
                    'avg_extract_time': np.mean([r['extract_time'] for r in algo_tests]),
                    'std_extract_time': np.std([r['extract_time'] for r in algo_tests]),
                    'avg_total_time': np.mean([r['total_time'] for r in algo_tests]),
                    'avg_hide_speed': np.mean([r['hide_speed_bps'] for r in algo_tests if r['hide_speed_bps'] > 0]),
                    'avg_extract_speed': np.mean([r['extract_speed_bps'] for r in algo_tests if r['extract_speed_bps'] > 0]),
                    'min_hide_time': np.min([r['hide_time'] for r in algo_tests]),
                    'max_hide_time': np.max([r['hide_time'] for r in algo_tests]),
                    'min_extract_time': np.min([r['extract_time'] for r in algo_tests]),
                    'max_extract_time': np.max([r['extract_time'] for r in algo_tests]),
                }
        
        # По размеру текста
        text_sizes = {}
        for r in successful_tests:
            size_key = r['text_length_bytes']
            if size_key not in text_sizes:
                text_sizes[size_key] = []
            text_sizes[size_key].append(r)
        
        for size, tests in text_sizes.items():
            time_stats['by_text_size'][str(size)] = {
                'count': len(tests),
                'avg_hide_time': np.mean([r['hide_time'] for r in tests]),
                'avg_extract_time': np.mean([r['extract_time'] for r in tests]),
                'avg_total_time': np.mean([r['total_time'] for r in tests]),
                'avg_hide_speed': np.mean([r['hide_speed_bps'] for r in tests if r['hide_speed_bps'] > 0]),
            }
        
        # Сохраняем статистику времени
        time_stats_path = self.output_dir / 'reports' / 'time_statistics.json'
        
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.float32, np.float64)):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            return obj
        
        with open(time_stats_path, 'w', encoding='utf-8') as f:
            json.dump(convert_to_serializable(time_stats), f, indent=2, ensure_ascii=False)
        
        return time_stats
    
    def generate_time_charts(self):
        """Генерирует графики, связанные со временем выполнения"""
        successful_tests = [r for r in self.results if r['success'] and r['extraction_success']]
        
        if not successful_tests:
            print("Нет успешных тестов для визуализации времени")
            return
            
        time_charts_dir = self.output_dir / 'charts' / 'time_analysis'
        algorithms = list(self.ALGORITHMS.keys())
        
        # 1. Сравнение времени выполнения по алгоритмам
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Box-plot времени скрытия
        ax = axes[0, 0]
        hide_times_data = []
        algo_labels = []
        for algo in algorithms:
            times = [r['hide_time'] * 1000 for r in successful_tests if r['algorithm'] == algo]
            if times:
                hide_times_data.append(times)
                algo_labels.append(algo.upper())
        
        if hide_times_data:
            bp = ax.boxplot(hide_times_data, labels=algo_labels, patch_artist=True)
            for patch, algo in zip(bp['boxes'], [a for a in algorithms if any(r['algorithm'] == a for r in successful_tests)]):
                patch.set_facecolor(self.ALGORITHMS[algo]['color'])
        
        ax.set_title('Время скрытия текста по алгоритмам', fontsize=14, fontweight='bold')
        ax.set_ylabel('Время (мс)')
        ax.set_xlabel('Алгоритм')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Box-plot времени извлечения
        ax = axes[0, 1]
        extract_times_data = []
        algo_labels = []
        for algo in algorithms:
            times = [r['extract_time'] * 1000 for r in successful_tests if r['algorithm'] == algo]
            if times:
                extract_times_data.append(times)
                algo_labels.append(algo.upper())
        
        if extract_times_data:
            bp = ax.boxplot(extract_times_data, labels=algo_labels, patch_artist=True)
            for patch, algo in zip(bp['boxes'], [a for a in algorithms if any(r['algorithm'] == a for r in successful_tests)]):
                patch.set_facecolor(self.ALGORITHMS[algo]['color'])
        
        ax.set_title('Время извлечения текста по алгоритмам', fontsize=14, fontweight='bold')
        ax.set_ylabel('Время (мс)')
        ax.set_xlabel('Алгоритм')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Столбчатая диаграмма среднего времени
        ax = axes[1, 0]
        algos_with_data = []
        hide_means = []
        extract_means = []
        hide_stds = []
        extract_stds = []
        
        for algo in algorithms:
            algo_tests = [r for r in successful_tests if r['algorithm'] == algo]
            if algo_tests:
                algos_with_data.append(algo)
                hide_means.append(np.mean([r['hide_time'] for r in algo_tests]) * 1000)
                extract_means.append(np.mean([r['extract_time'] for r in algo_tests]) * 1000)
                hide_stds.append(np.std([r['hide_time'] for r in algo_tests]) * 1000)
                extract_stds.append(np.std([r['extract_time'] for r in algo_tests]) * 1000)
        
        x = np.arange(len(algos_with_data))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, hide_means, width, label='Скрытие', 
                      color=[self.ALGORITHMS[a]['color'] for a in algos_with_data],
                      yerr=hide_stds, capsize=5)
        bars2 = ax.bar(x + width/2, extract_means, width, label='Извлечение',
                      color=[self.ALGORITHMS[a]['color'] for a in algos_with_data], 
                      alpha=0.7, yerr=extract_stds, capsize=5)
        
        ax.set_title('Среднее время выполнения (со стандартным отклонением)', fontsize=14, fontweight='bold')
        ax.set_ylabel('Время (мс)')
        ax.set_xlabel('Алгоритм')
        ax.set_xticks(x)
        ax.set_xticklabels([a.upper() for a in algos_with_data])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        # Скорость обработки (бит/сек)
        ax = axes[1, 1]
        hide_speeds = []
        extract_speeds = []
        
        for algo in algorithms:
            hide_speed = np.mean([r['hide_speed_bps'] for r in successful_tests 
                                 if r['algorithm'] == algo and r['hide_speed_bps'] > 0])
            extract_speed = np.mean([r['extract_speed_bps'] for r in successful_tests 
                                    if r['algorithm'] == algo and r['extract_speed_bps'] > 0])
            hide_speeds.append(hide_speed / 1000)  # в кбит/сек
            extract_speeds.append(extract_speed / 1000)
        
        x = np.arange(len(algorithms))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, hide_speeds, width, label='Скрытие',
                      color=[self.ALGORITHMS[a]['color'] for a in algorithms])
        bars2 = ax.bar(x + width/2, extract_speeds, width, label='Извлечение',
                      color=[self.ALGORITHMS[a]['color'] for a in algorithms], alpha=0.7)
        
        ax.set_title('Скорость обработки данных', fontsize=14, fontweight='bold')
        ax.set_ylabel('Скорость (кбит/сек)')
        ax.set_xlabel('Алгоритм')
        ax.set_xticks(x)
        ax.set_xticklabels([a.upper() for a in algorithms])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(time_charts_dir / 'time_comparison_by_algorithm.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 2. Зависимость времени от размера текста
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Время скрытия vs размер текста
        ax = axes[0, 0]
        for algo in algorithms:
            algo_data = [(r['text_length_bytes'], r['hide_time'] * 1000) 
                        for r in successful_tests if r['algorithm'] == algo]
            if algo_data:
                x, y = zip(*sorted(algo_data))
                ax.scatter(x, y, label=algo.upper(), alpha=0.6, 
                          color=self.ALGORITHMS[algo]['color'], s=50)
                
                if len(x) > 1:
                    z = np.polyfit(x, y, 1)
                    p = np.poly1d(z)
                    ax.plot(x, p(x), '--', color=self.ALGORITHMS[algo]['color'], alpha=0.5, linewidth=2)
        
        ax.set_title('Время скрытия vs Размер текста', fontsize=14, fontweight='bold')
        ax.set_xlabel('Размер текста (байт)')
        ax.set_ylabel('Время скрытия (мс)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Время извлечения vs размер текста
        ax = axes[0, 1]
        for algo in algorithms:
            algo_data = [(r['text_length_bytes'], r['extract_time'] * 1000) 
                        for r in successful_tests if r['algorithm'] == algo]
            if algo_data:
                x, y = zip(*sorted(algo_data))
                ax.scatter(x, y, label=algo.upper(), alpha=0.6, 
                          color=self.ALGORITHMS[algo]['color'], s=50)
                
                if len(x) > 1:
                    z = np.polyfit(x, y, 1)
                    p = np.poly1d(z)
                    ax.plot(x, p(x), '--', color=self.ALGORITHMS[algo]['color'], alpha=0.5, linewidth=2)
        
        ax.set_title('Время извлечения vs Размер текста', fontsize=14, fontweight='bold')
        ax.set_xlabel('Размер текста (байт)')
        ax.set_ylabel('Время извлечения (мс)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(time_charts_dir / 'time_vs_textsize.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Графики времени сохранены в {time_charts_dir}")
    
    def generate_statistics(self):
        """Генерирует статистику по результатам"""
        if not self.results:
            print("Нет результатов для анализа")
            return
            
        successful_tests = [r for r in self.results if r['success'] and r['extraction_success']]
        
        if not successful_tests:
            print("Нет успешных тестов для анализа")
            return
            
        stats = {
            'total_tests': len(self.results),
            'successful_tests': len(successful_tests),
            'success_rate': len(successful_tests) / len(self.results) * 100,
            'algorithms': {}
        }
        
        print("\n" + "=" * 80)
        print("СТАТИСТИКА ТЕСТИРОВАНИЯ")
        print("=" * 80)
        
        print(f"\nВсего тестов: {stats['total_tests']}")
        print(f"Успешных: {stats['successful_tests']} ({stats['success_rate']:.1f}%)")
        
        print("\nСтатистика по алгоритмам:")
        print("-" * 80)
        
        for algo in self.ALGORITHMS.keys():
            algo_tests = [r for r in successful_tests if r['algorithm'] == algo]
            if algo_tests:
                psnr_values = [r['psnr'] for r in algo_tests if r['psnr'] and r['psnr'] != float('inf')]
                ssim_values = [r['ssim'] for r in algo_tests if r['ssim']]
                mse_values = [r['mse'] for r in algo_tests if r['mse']]
                
                algo_stat = {
                    'count': len(algo_tests),
                    'avg_psnr': np.mean(psnr_values) if psnr_values else float('inf'),
                    'std_psnr': np.std(psnr_values) if psnr_values else 0,
                    'avg_ssim': np.mean(ssim_values) if ssim_values else 1.0,
                    'std_ssim': np.std(ssim_values) if ssim_values else 0,
                    'avg_mse': np.mean(mse_values) if mse_values else 0,
                    'std_mse': np.std(mse_values) if mse_values else 0,
                    'avg_hide_time': np.mean([r['hide_time'] for r in algo_tests]),
                    'std_hide_time': np.std([r['hide_time'] for r in algo_tests]),
                    'avg_extract_time': np.mean([r['extract_time'] for r in algo_tests]),
                    'std_extract_time': np.std([r['extract_time'] for r in algo_tests]),
                    'avg_total_time': np.mean([r['total_time'] for r in algo_tests]),
                    'avg_hide_speed': np.mean([r['hide_speed_bps'] for r in algo_tests if r['hide_speed_bps'] > 0]),
                    'avg_extract_speed': np.mean([r['extract_speed_bps'] for r in algo_tests if r['extract_speed_bps'] > 0]),
                    'avg_size_increase': np.mean([r['size_increase_percent'] for r in algo_tests if r['size_increase_percent']]),
                    'avg_intensity_change': np.mean([r['avg_intensity_change'] for r in algo_tests if r['avg_intensity_change']])
                }
                
                stats['algorithms'][algo] = algo_stat
                
                print(f"\n{algo.upper()}:")
                print(f"  Тестов: {algo_stat['count']}")
                print(f"  PSNR: {algo_stat['avg_psnr']:.2f} ± {algo_stat['std_psnr']:.2f} dB")
                print(f"  SSIM: {algo_stat['avg_ssim']:.4f} ± {algo_stat['std_ssim']:.4f}")
                print(f"  MSE: {algo_stat['avg_mse']:.4f} ± {algo_stat['std_mse']:.4f}")
                print(f"  Время скрытия: {algo_stat['avg_hide_time']*1000:.2f} ± {algo_stat['std_hide_time']*1000:.2f} мс")
                print(f"  Время извлечения: {algo_stat['avg_extract_time']*1000:.2f} ± {algo_stat['std_extract_time']*1000:.2f} мс")
                print(f"  Скорость скрытия: {algo_stat['avg_hide_speed']/1000:.1f} кбит/сек")
                print(f"  Скорость извлечения: {algo_stat['avg_extract_speed']/1000:.1f} кбит/сек")
        
        # Сохраняем статистику в JSON
        stats_path = self.output_dir / 'reports' / 'statistics.json'
        
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.float32, np.float64)):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            return obj
        
        serializable_stats = convert_to_serializable(stats)
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_stats, f, indent=2, ensure_ascii=False)
            
        print(f"\nСтатистика сохранена в {stats_path}")
        
        return stats
    
    def generate_report(self):
        """Генерирует полный отчет"""
        print("\n" + "█" * 80)
        print("█" + " " * 78 + "█")
        print("█" + " " * 20 + "ГЕНЕРАЦИЯ ОТЧЕТА" + " " * 38 + "█")
        print("█" + " " * 78 + "█")
        print("█" * 80)
        
        # Сохраняем результаты
        self.save_results_to_csv()
        
        # Анализируем качество и время
        quality_stats = self.analyze_quality_metrics()
        time_stats = self.analyze_time_performance()
        
        # Генерируем статистику
        stats = self.generate_statistics()
        
        # Генерируем графики
        self.generate_quality_charts()
        self.generate_time_charts()
        self.generate_per_image_analysis()
        
        # Создаем текстовый отчет
        report_path = self.output_dir / 'reports' / 'report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ОТЧЕТ ПО ТЕСТИРОВАНИЮ СТЕГАНОГРАФИЧЕСКИХ АЛГОРИТМОВ\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Всего тестов: {stats['total_tests']}\n")
            f.write(f"Успешных: {stats['successful_tests']} ({stats['success_rate']:.1f}%)\n\n")
            
            f.write("МЕТРИКИ КАЧЕСТВА:\n")
            f.write("-" * 40 + "\n")
            
            if quality_stats:
                overall = quality_stats['overall']
                f.write(f"\nОбщие метрики качества:\n")
                f.write(f"  Средний PSNR: {overall['avg_psnr']:.2f} ± {overall['std_psnr']:.2f} dB\n")
                f.write(f"  Средний SSIM: {overall['avg_ssim']:.4f} ± {overall['std_ssim']:.4f}\n")
                f.write(f"  Средний MSE: {overall['avg_mse']:.4f} ± {overall['std_mse']:.4f}\n")
                f.write(f"  Средний MAE: {overall['avg_mae']:.4f}\n")
                f.write(f"  Средний SNR: {overall['avg_snr']:.2f} dB\n")
                f.write(f"  Средний NCC: {overall['avg_ncc']:.4f}\n")
                f.write(f"  Средний процент измененных пикселей: {overall['avg_changed_pixels']:.2f}%\n")
            
            f.write("\n\nРЕЗУЛЬТАТЫ ПО АЛГОРИТМАМ:\n")
            f.write("-" * 40 + "\n")
            
            for algo, algo_stat in stats['algorithms'].items():
                f.write(f"\n{algo.upper()}:\n")
                f.write(f"  Количество тестов: {algo_stat['count']}\n")
                f.write(f"  PSNR: {algo_stat['avg_psnr']:.2f} ± {algo_stat['std_psnr']:.2f} dB\n")
                f.write(f"  SSIM: {algo_stat['avg_ssim']:.4f} ± {algo_stat['std_ssim']:.4f}\n")
                f.write(f"  MSE: {algo_stat['avg_mse']:.4f} ± {algo_stat['std_mse']:.4f}\n")
                f.write(f"  Время скрытия: {algo_stat['avg_hide_time']*1000:.2f} мс\n")
                f.write(f"  Время извлечения: {algo_stat['avg_extract_time']*1000:.2f} мс\n")
                f.write(f"  Скорость скрытия: {algo_stat['avg_hide_speed']/1000:.1f} кбит/сек\n")
                f.write(f"  Скорость извлечения: {algo_stat['avg_extract_speed']/1000:.1f} кбит/сек\n")
        
        print(f"\nОтчет сохранен в {report_path}")
        print("\n" + "█" * 80)
        print("Тестирование завершено!")
        print("Результаты доступны в директории:", self.output_dir)
        print("  - Метрики качества: test/test_results/charts/quality_metrics/")
        print("  - Анализ времени: test/test_results/charts/time_analysis/")
        print("  - Анализ по изображениям: test/test_results/charts/per_image_analysis/")
        print("  - Отчеты: test/test_results/reports/")


def main():
    """Главная функция для запуска тестирования"""
    print("=" * 80)
    print("ТЕСТИРОВАНИЕ СТЕГАНОГРАФИЧЕСКИХ АЛГОРИТМОВ")
    print("=" * 80)
    
    # Обновляем конфигурацию алгоритмов с функциями
    SteganoAnalyzer.ALGORITHMS['png']['hide'] = hide_text_png
    SteganoAnalyzer.ALGORITHMS['png']['extract'] = extract_text_png
    SteganoAnalyzer.ALGORITHMS['jpg']['hide'] = hide_text_jpg
    SteganoAnalyzer.ALGORITHMS['jpg']['extract'] = extract_text_jpg
    SteganoAnalyzer.ALGORITHMS['bmp']['hide'] = hide_text_bmp
    SteganoAnalyzer.ALGORITHMS['bmp']['extract'] = extract_text_bmp
    SteganoAnalyzer.ALGORITHMS['webp']['hide'] = hide_text_webp
    SteganoAnalyzer.ALGORITHMS['webp']['extract'] = extract_text_webp
    
    # Создаем анализатор
    analyzer = SteganoAnalyzer(
        test_images_dir='test/test_images',
        output_dir='test/test_results'
    )
    
    # Запускаем все тесты
    analyzer.run_all_tests()
    
    # Генерируем отчет
    analyzer.generate_report()


if __name__ == '__main__':
    main()