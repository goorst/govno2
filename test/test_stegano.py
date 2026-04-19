# test/test_stegano.py (все 12 изображений, 2 текста)
import sys
import os
import io
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
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
    
    STEGANO_KEY = "my_secret_stegano_key_2026"
    
    def __init__(self, test_images_dir: str = 'test/test_images', output_dir: str = 'test/test_results'):
        self.test_images_dir = Path(test_images_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        (self.output_dir / 'charts').mkdir(exist_ok=True)
        (self.output_dir / 'stego_images').mkdir(exist_ok=True)
        (self.output_dir / 'reports').mkdir(exist_ok=True)
        
        self.results = []
        self.test_images = {}
        
    def find_test_images(self) -> Dict[str, List[Path]]:
        """Находит ВСЕ тестовые изображения в соответствующих поддиректориях"""
        self.test_images = {}
        
        for algo_name, algo_info in self.ALGORITHMS.items():
            format_dir = self.test_images_dir / algo_info['format_dir']
            
            if format_dir.exists():
                images = []
                for ext in [algo_info['extension'], algo_info['extension'].upper()]:
                    images.extend(format_dir.glob(f'*{ext}'))
                
                # Берем ВСЕ изображения (12 штук)
                self.test_images[algo_name] = images
                print(f"Найдено {len(images)} изображений для {algo_name.upper()}")
            else:
                print(f"Директория {format_dir} не найдена для {algo_name.upper()}")
                self.test_images[algo_name] = []
                
        total_images = sum(len(imgs) for imgs in self.test_images.values())
        print(f"Всего тестовых изображений: {total_images}")
        
        return self.test_images
    
    def generate_test_texts(self) -> List[tuple]:
        """
        Генерирует 2 тестовых текста: английский и русский среднего размера
        """
        texts = []
        
        # Английский текст среднего размера
        eng_text = """This is a medium-sized test text for steganography analysis."""
        texts.append(('medium_eng', eng_text))
        
        # Русский текст среднего размера
        rus_text = """Это тестовый текст среднего размера для анализа стеганографии."""
        texts.append(('medium_rus', rus_text))
        
        return texts
    
    def calculate_metrics(self, original: Image.Image, stego: Image.Image) -> Dict:
        """Вычисляет основные метрики качества"""
        orig_array = np.array(original.convert('RGB'))
        stego_array = np.array(stego.convert('RGB'))
        
        metrics = {}
        
        # PSNR
        try:
            metrics['psnr'] = psnr(orig_array, stego_array, data_range=255)
        except:
            metrics['psnr'] = float('inf')
        
        # SSIM
        try:
            metrics['ssim'] = ssim(orig_array, stego_array, channel_axis=2, data_range=255)
        except:
            metrics['ssim'] = 1.0
        
        # MSE
        metrics['mse'] = np.mean((orig_array.astype(float) - stego_array.astype(float)) ** 2)
        
        # MAE
        metrics['mae'] = np.mean(np.abs(orig_array.astype(float) - stego_array.astype(float)))
        
        # Процент измененных пикселей
        changed_pixels = np.sum(np.any(orig_array != stego_array, axis=2))
        total_pixels = orig_array.shape[0] * orig_array.shape[1]
        metrics['changed_pixels_percent'] = (changed_pixels / total_pixels) * 100
        
        return metrics
    
    def calculate_capacity(self, image: Image.Image, algorithm: str) -> Dict:
        """Рассчитывает емкость изображения"""
        width, height = image.size
        pixels = width * height
        channels = 3
        
        capacity = {}
        
        if algorithm in ['png', 'bmp', 'webp']:
            capacity['bits'] = pixels * channels
            capacity['bytes'] = capacity['bits'] // 8
        else:  # jpg
            blocks_h = height // 8
            blocks_w = width // 8
            capacity['bits'] = blocks_h * blocks_w * channels
            capacity['bytes'] = capacity['bits'] // 8
        
        return capacity
    
    def run_single_test(self, image_path: Path, algorithm: str, 
                        text_name: str, text: str) -> Optional[Dict]:
        """Запускает одиночный тест"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'image': str(image_path.name),
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
            'mae': None,
            'changed_pixels_percent': None,
            'capacity_bits': None,
            'capacity_bytes': None,
            'capacity_usage_percent': None,
            'file_size_original': 0,
            'file_size_stego': 0,
            'size_increase_percent': 0,
            'error': None
        }
        
        try:
            original_img = Image.open(image_path)
            
            # Емкость
            capacity = self.calculate_capacity(original_img, algorithm)
            result['capacity_bits'] = capacity['bits']
            result['capacity_bytes'] = capacity['bytes']
            result['file_size_original'] = image_path.stat().st_size
            
            # Процент использования
            text_bytes = len(text.encode('utf-8'))
            if capacity['bytes'] > 0:
                result['capacity_usage_percent'] = (text_bytes / capacity['bytes']) * 100
            
            # Проверка размера
            if text_bytes > capacity['bytes']:
                result['error'] = f"Text too large"
                return result
            
            # Скрытие
            with open(image_path, 'rb') as f:
                image_data = io.BytesIO(f.read())
            
            start_time = time.perf_counter()
            try:
                hide_func = self.ALGORITHMS[algorithm]['hide']
                if algorithm in ['png', 'bmp', 'webp']:
                    stego_data = hide_func(image_data, text, self.STEGANO_KEY)
                else:
                    stego_data = hide_func(image_data, text)
                    
                result['hide_time'] = time.perf_counter() - start_time
                result['success'] = True
                
                # Скорость скрытия
                bits_hidden = text_bytes * 8
                if result['hide_time'] > 0:
                    result['hide_speed_bps'] = bits_hidden / result['hide_time']
                    
            except Exception as e:
                result['error'] = f"Hide error: {str(e)}"
                return result
            
            # Размер файла
            result['file_size_stego'] = len(stego_data.getvalue())
            if result['file_size_original'] > 0:
                result['size_increase_percent'] = ((result['file_size_stego'] - result['file_size_original']) / 
                                                   result['file_size_original']) * 100
            
            # Сохранение стего
            stego_filename = f"{image_path.stem}_{algorithm}_{text_name}{self.ALGORITHMS[algorithm]['extension']}"
            stego_path = self.output_dir / 'stego_images' / stego_filename
            with open(stego_path, 'wb') as f:
                f.write(stego_data.getvalue())
            
            # Метрики
            stego_img = Image.open(stego_path)
            metrics = self.calculate_metrics(original_img, stego_img)
            result.update(metrics)
            
            # Извлечение
            with open(stego_path, 'rb') as f:
                stego_data_for_extract = io.BytesIO(f.read())
            
            start_time = time.perf_counter()
            try:
                extract_func = self.ALGORITHMS[algorithm]['extract']
                if algorithm in ['png', 'bmp', 'webp']:
                    extracted_text = extract_func(stego_data_for_extract, self.STEGANO_KEY)
                else:
                    extracted_text = extract_func(stego_data_for_extract)
                    
                result['extract_time'] = time.perf_counter() - start_time
                result['total_time'] = result['hide_time'] + result['extract_time']
                
                # Скорость извлечения
                if result['extract_time'] > 0:
                    result['extract_speed_bps'] = bits_hidden / result['extract_time']
                
                if extracted_text.strip() == text.strip():
                    result['extraction_success'] = True
                else:
                    result['error'] = "Extraction mismatch"
            except Exception as e:
                result['error'] = f"Extract error: {str(e)}"
                
        except Exception as e:
            result['error'] = f"General error: {str(e)}"
            
        return result
    
    def run_all_tests(self) -> List[Dict]:
        """Запускает все тесты"""
        if not self.test_images:
            self.find_test_images()
            
        if not any(self.test_images.values()):
            print("Нет тестовых изображений!")
            return []
            
        test_texts = self.generate_test_texts()
        self.results = []
        
        # Подсчет тестов
        total_tests = sum(len(images) * len(test_texts) 
                         for images in self.test_images.values())
        
        current_test = 0
        
        print(f"\n{'='*70}")
        print(f"ЗАПУСК ТЕСТОВ. ВСЕГО: {total_tests} (12 изобр. × 4 формата × 2 текста)")
        print(f"{'='*70}")
        
        for algo_name, images in self.test_images.items():
            if not images:
                continue
                
            print(f"\n{algo_name.upper()} ({len(images)} изображений)")
            print("-" * 50)
            
            for image_path in images:
                for text_name, text in test_texts:
                    current_test += 1
                    print(f"  [{current_test:3d}/{total_tests}] {image_path.name[:30]:30s} - {text_name:10s}...", end='', flush=True)
                    
                    result = self.run_single_test(image_path, algo_name, text_name, text)
                    
                    if result:
                        self.results.append(result)
                        if result['success'] and result['extraction_success']:
                            print(f" ✓ PSNR: {result['psnr']:5.1f} dB, {result['total_time']*1000:6.1f} мс")
                        else:
                            print(f" ✗ {result['error'][:30]}")
                    else:
                        print(" ✗ Ошибка")
        
        print("\n" + "=" * 70)
        successful = sum(1 for r in self.results if r['success'] and r['extraction_success'])
        print(f"Завершено. Успешно: {successful}/{len(self.results)} ({successful/len(self.results)*100:.1f}%)")
        
        return self.results
    
    def save_results_to_csv(self, filename: str = 'test_results.csv'):
        """Сохраняет результаты в CSV"""
        if not self.results:
            return
            
        csv_path = self.output_dir / 'reports' / filename
        
        fieldnames = [
            'timestamp', 'image', 'image_size', 'image_width', 'image_height', 'image_pixels',
            'algorithm', 'text_name', 'text_length_chars', 'text_length_bytes',
            'success', 'extraction_success', 'hide_time', 'extract_time', 'total_time',
            'hide_speed_bps', 'extract_speed_bps', 'psnr', 'ssim', 'mse', 'mae',
            'changed_pixels_percent', 'capacity_bits', 'capacity_bytes', 'capacity_usage_percent',
            'file_size_original', 'file_size_stego', 'size_increase_percent', 'error'
        ]
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.results)
            
        print(f"CSV сохранен: {csv_path}")
    
    def generate_charts(self):
        """Генерирует улучшенные графики"""
        successful_tests = [r for r in self.results if r['success'] and r['extraction_success']]
        
        if not successful_tests:
            return
            
        charts_dir = self.output_dir / 'charts'
        algorithms = list(self.ALGORITHMS.keys())
        algo_names = [a.upper() for a in algorithms]
        colors = [self.ALGORITHMS[a]['color'] for a in algorithms]
        
        # Устанавливаем стиль
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # ============================================================
        # 1. Сравнение PSNR и SSIM (столбчатая диаграмма со значениями)
        # ============================================================
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        
        # PSNR - столбчатая диаграмма
        ax = axes[0]
        psnr_means = []
        psnr_stds = []
        for algo in algorithms:
            vals = [r['psnr'] for r in successful_tests if r['algorithm'] == algo and r['psnr'] != float('inf')]
            psnr_means.append(np.mean(vals) if vals else 0)
            psnr_stds.append(np.std(vals) if vals else 0)
        
        bars = ax.bar(algo_names, psnr_means, color=colors, yerr=psnr_stds, capsize=5, 
                    error_kw={'elinewidth': 2, 'capthick': 2})
        
        # Добавляем значения над столбцами
        for bar, val, std in zip(bars, psnr_means, psnr_stds):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 2,
                    f'{val:.1f} dB', ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        ax.set_title('PSNR - Пиковое отношение сигнал/шум\n(>40 dB - отлично)', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_ylabel('PSNR (dB)', fontsize=11)
        ax.set_xlabel('Алгоритм', fontsize=11)
        ax.set_ylim(0, max(psnr_means) * 1.15 if max(psnr_means) > 0 else 100)
        ax.axhline(y=40, color='orange', linestyle='--', alpha=0.7, linewidth=1.5, label='Порог отличного качества')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')
        
        # SSIM - столбчатая диаграмма
        ax = axes[1]
        ssim_means = []
        ssim_stds = []
        for algo in algorithms:
            vals = [r['ssim'] for r in successful_tests if r['algorithm'] == algo]
            ssim_means.append(np.mean(vals) if vals else 0)
            ssim_stds.append(np.std(vals) if vals else 0)
        
        bars = ax.bar(algo_names, ssim_means, color=colors, yerr=ssim_stds, capsize=5,
                    error_kw={'elinewidth': 2, 'capthick': 2})
        
        for bar, val, std in zip(bars, ssim_means, ssim_stds):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.02,
                    f'{val:.4f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        ax.set_title('SSIM - Индекс структурного сходства\n(>0.95 - отлично)', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_ylabel('SSIM', fontsize=11)
        ax.set_xlabel('Алгоритм', fontsize=11)
        ax.set_ylim(0.9, 1.05)
        ax.axhline(y=0.95, color='orange', linestyle='--', alpha=0.7, linewidth=1.5, label='Порог отличного качества')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(charts_dir / 'quality_metrics.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # ============================================================
        # 2. Время выполнения (группированная столбчатая диаграмма)
        # ============================================================
        fig, ax = plt.subplots(figsize=(12, 7))
        
        x = np.arange(len(algorithms))
        width = 0.35
        
        hide_means = []
        hide_stds = []
        extract_means = []
        extract_stds = []
        
        for algo in algorithms:
            h_vals = [r['hide_time']*1000 for r in successful_tests if r['algorithm'] == algo]
            e_vals = [r['extract_time']*1000 for r in successful_tests if r['algorithm'] == algo]
            hide_means.append(np.mean(h_vals) if h_vals else 0)
            hide_stds.append(np.std(h_vals) if h_vals else 0)
            extract_means.append(np.mean(e_vals) if e_vals else 0)
            extract_stds.append(np.std(e_vals) if e_vals else 0)
        
        bars1 = ax.bar(x - width/2, hide_means, width, label='Скрытие', 
                    color=['#2ecc71' if a != 'jpg' else '#c0392b' for a in algorithms],
                    yerr=hide_stds, capsize=5, error_kw={'elinewidth': 2, 'capthick': 2})
        bars2 = ax.bar(x + width/2, extract_means, width, label='Извлечение',
                    color=['#27ae60' if a != 'jpg' else '#e74c3c' for a in algorithms],
                    yerr=extract_stds, capsize=5, error_kw={'elinewidth': 2, 'capthick': 2})
        
        # Добавляем значения
        for bar, val in zip(bars1, hide_means):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(hide_stds)*0.5,
                    f'{val:.1f}', ha='center', va='bottom', fontsize=9, rotation=0)
        for bar, val in zip(bars2, extract_means):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(extract_stds)*0.5,
                    f'{val:.1f}', ha='center', va='bottom', fontsize=9, rotation=0)
        
        ax.set_title('Среднее время выполнения операций\n(с планками погрешностей)', 
                    fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel('Время (мс)', fontsize=12)
        ax.set_xlabel('Алгоритм', fontsize=12)
        ax.set_xticks(x)
        ax.set_xticklabels(algo_names)
        ax.legend(loc='upper left', fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(charts_dir / 'time_performance.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # ============================================================
        # 3. Увеличение размера файла + MSE (два графика)
        # ============================================================
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        
        # Увеличение размера
        ax = axes[0]
        size_means = []
        size_stds = []
        for algo in algorithms:
            vals = [r['size_increase_percent'] for r in successful_tests if r['algorithm'] == algo]
            size_means.append(np.mean(vals) if vals else 0)
            size_stds.append(np.std(vals) if vals else 0)
        
        bars = ax.bar(algo_names, size_means, color=colors, yerr=size_stds, capsize=5,
                    error_kw={'elinewidth': 2, 'capthick': 2})
        
        for bar, val in zip(bars, size_means):
            color = 'red' if val > 100 else 'black'
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(size_stds)*0.5 + abs(val)*0.05,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold', color=color)
        
        ax.set_title('Увеличение размера файла', fontsize=13, fontweight='bold', pad=15)
        ax.set_ylabel('Увеличение (%)', fontsize=11)
        ax.set_xlabel('Алгоритм', fontsize=11)
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.5, linewidth=1)
        ax.grid(True, alpha=0.3, axis='y')
        
        # MSE
        ax = axes[1]
        mse_means = []
        mse_stds = []
        for algo in algorithms:
            vals = [r['mse'] for r in successful_tests if r['algorithm'] == algo]
            mse_means.append(np.mean(vals) if vals else 0)
            mse_stds.append(np.std(vals) if vals else 0)
        
        bars = ax.bar(algo_names, mse_means, color=colors, yerr=mse_stds, capsize=5,
                    error_kw={'elinewidth': 2, 'capthick': 2})
        
        for bar, val in zip(bars, mse_means):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(mse_stds)*0.5,
                    f'{val:.2f}', ha='center', va='bottom', fontsize=10)
        
        ax.set_title('MSE - Среднеквадратичная ошибка\n(чем меньше, тем лучше)', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_ylabel('MSE', fontsize=11)
        ax.set_xlabel('Алгоритм', fontsize=11)
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(charts_dir / 'size_and_mse.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # ============================================================
        # 4. Круговая диаграмма успешности тестов
        # ============================================================
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        # Общая успешность
        ax = axes[0]
        success_count = len(successful_tests)
        fail_count = len(self.results) - success_count
        
        sizes = [success_count, fail_count]
        labels = [f'Успешно\n{success_count} тестов', f'Ошибка\n{fail_count} тестов']
        colors_pie = ['#2ecc71', '#e74c3c']
        explode = (0.05, 0)
        
        wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, colors=colors_pie,
                                            autopct='%1.1f%%', shadow=True, startangle=90,
                                            textprops={'fontsize': 13, 'fontweight': 'bold'})
        
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(14)
            autotext.set_fontweight('bold')
        
        ax.set_title(f'Общая успешность тестов\n({len(self.results)} всего)', 
                    fontsize=14, fontweight='bold', pad=20)
        
        # Успешность по алгоритмам
        ax = axes[1]
        algo_success_rates = []
        algo_test_counts = []
        
        for algo in algorithms:
            algo_tests = [r for r in self.results if r['algorithm'] == algo]
            algo_successful = [r for r in algo_tests if r['success'] and r['extraction_success']]
            if algo_tests:
                rate = len(algo_successful) / len(algo_tests) * 100
                algo_success_rates.append(rate)
                algo_test_counts.append(len(algo_tests))
            else:
                algo_success_rates.append(0)
                algo_test_counts.append(0)
        
        bars = ax.bar(algo_names, algo_success_rates, color=colors, edgecolor='black', linewidth=1.5)
        
        for bar, rate, count in zip(bars, algo_success_rates, algo_test_counts):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
                    f'{rate:.1f}%\n({count} тестов)', ha='center', va='bottom', 
                    fontsize=11, fontweight='bold')
        
        ax.set_title('Успешность по алгоритмам', fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel('Успешность (%)', fontsize=12)
        ax.set_xlabel('Алгоритм', fontsize=12)
        ax.set_ylim(0, 110)
        ax.axhline(y=80, color='orange', linestyle='--', alpha=0.7, linewidth=1.5, label='Хороший результат')
        ax.axhline(y=95, color='green', linestyle='--', alpha=0.7, linewidth=1.5, label='Отличный результат')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        plt.savefig(charts_dir / 'success_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # ============================================================
        # 5. Сводная таблица метрик (сохраняем как текст)
        # ============================================================
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.axis('off')
        
        # Создаем данные для таблицы
        table_data = []
        headers = ['Алгоритм', 'PSNR (dB)', 'SSIM', 'MSE', 'Время (мс)', 'Размер (%)', 'Успех (%)']
        table_data.append(headers)
        
        for algo in algorithms:
            algo_tests = [r for r in successful_tests if r['algorithm'] == algo]
            if algo_tests:
                psnr = np.mean([r['psnr'] for r in algo_tests if r['psnr'] != float('inf')])
                ssim = np.mean([r['ssim'] for r in algo_tests])
                mse = np.mean([r['mse'] for r in algo_tests])
                time_tot = np.mean([r['total_time']*1000 for r in algo_tests])
                size_inc = np.mean([r['size_increase_percent'] for r in algo_tests])
                
                all_tests = [r for r in self.results if r['algorithm'] == algo]
                success = len([r for r in all_tests if r['success'] and r['extraction_success']])
                success_rate = success / len(all_tests) * 100 if all_tests else 0
                
                table_data.append([
                    algo.upper(),
                    f'{psnr:.1f}',
                    f'{ssim:.4f}',
                    f'{mse:.2f}',
                    f'{time_tot:.1f}',
                    f'{size_inc:.1f}',
                    f'{success_rate:.1f}'
                ])
        
        # Создаем таблицу
        table = ax.table(cellText=table_data, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 2.5)
        
        # Раскрашиваем заголовки
        for i in range(len(headers)):
            table[(0, i)].set_facecolor('#34495e')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        # Раскрашиваем строки
        for i, algo in enumerate(algorithms, 1):
            if i < len(table_data):
                color = self.ALGORITHMS[algo]['color']
                for j in range(len(headers)):
                    table[(i, j)].set_facecolor(color + '30')  # 30 - прозрачность
        
        ax.set_title('СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ', 
                    fontsize=16, fontweight='bold', pad=20, loc='center')
        
        plt.tight_layout()
        plt.savefig(charts_dir / 'summary_table.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"Графики сохранены в {charts_dir}")


    def generate_statistics(self) -> Dict:
        """Генерирует статистику"""
        successful_tests = [r for r in self.results if r['success'] and r['extraction_success']]
        
        if not successful_tests:
            return {}
        
        stats = {
            'total_tests': len(self.results),
            'successful_tests': len(successful_tests),
            'success_rate': len(successful_tests) / len(self.results) * 100,
            'algorithms': {}
        }
        
        for algo in self.ALGORITHMS.keys():
            algo_tests = [r for r in successful_tests if r['algorithm'] == algo]
            if algo_tests:
                stats['algorithms'][algo] = {
                    'count': len(algo_tests),
                    'avg_psnr': np.mean([r['psnr'] for r in algo_tests if r['psnr'] != float('inf')]),
                    'std_psnr': np.std([r['psnr'] for r in algo_tests if r['psnr'] != float('inf')]),
                    'avg_ssim': np.mean([r['ssim'] for r in algo_tests]),
                    'std_ssim': np.std([r['ssim'] for r in algo_tests]),
                    'avg_mse': np.mean([r['mse'] for r in algo_tests]),
                    'std_mse': np.std([r['mse'] for r in algo_tests]),
                    'avg_hide_time': np.mean([r['hide_time']*1000 for r in algo_tests]),
                    'std_hide_time': np.std([r['hide_time']*1000 for r in algo_tests]),
                    'avg_extract_time': np.mean([r['extract_time']*1000 for r in algo_tests]),
                    'std_extract_time': np.std([r['extract_time']*1000 for r in algo_tests]),
                    'avg_total_time': np.mean([r['total_time']*1000 for r in algo_tests]),
                    'avg_hide_speed': np.mean([r['hide_speed_bps'] for r in algo_tests if r['hide_speed_bps'] > 0]),
                    'avg_extract_speed': np.mean([r['extract_speed_bps'] for r in algo_tests if r['extract_speed_bps'] > 0]),
                    'avg_size_increase': np.mean([r['size_increase_percent'] for r in algo_tests]),
                    'avg_changed_pixels': np.mean([r['changed_pixels_percent'] for r in algo_tests]),
                }
        
        # Сохранение в JSON
        stats_path = self.output_dir / 'reports' / 'statistics.json'
        
        def convert(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, (np.float32, np.float64)):
                return float(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            return obj
        
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(convert(stats), f, indent=2, ensure_ascii=False)
        
        return stats
    
    def generate_report(self):
        """Генерирует отчет"""
        print("\n" + "█" * 70)
        print("█" + " " * 68 + "█")
        print("█" + " " * 23 + "ГЕНЕРАЦИЯ ОТЧЕТА" + " " * 24 + "█")
        print("█" + " " * 68 + "█")
        print("█" * 70)
        
        self.save_results_to_csv()
        stats = self.generate_statistics()
        self.generate_charts()
        
        # Вывод статистики
        print("\n" + "=" * 70)
        print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        print("=" * 70)
        
        print(f"\nВсего тестов: {stats['total_tests']}")
        print(f"Успешно: {stats['successful_tests']} ({stats['success_rate']:.1f}%)\n")
        
        print("По алгоритмам:")
        print("-" * 90)
        print(f"{'Алг.':<6} {'Тестов':<7} {'PSNR(dB)':<15} {'SSIM':<12} {'MSE':<12} {'Скрытие(мс)':<13} {'Извлеч.(мс)':<13} {'Размер(%)':<10}")
        print("-" * 90)
        
        for algo, s in stats['algorithms'].items():
            print(f"{algo.upper():<6} {s['count']:<7} {s['avg_psnr']:>6.1f} ± {s['std_psnr']:<5.1f} {s['avg_ssim']:>6.4f} ± {s['std_ssim']:<5.4f} {s['avg_mse']:>6.2f} ± {s['std_mse']:<5.2f} {s['avg_hide_time']:>6.1f} ± {s['std_hide_time']:<5.1f} {s['avg_extract_time']:>6.1f} ± {s['std_extract_time']:<5.1f} {s['avg_size_increase']:>6.1f}%")
        
        # Сохранение отчета
        report_path = self.output_dir / 'reports' / 'report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("ОТЧЕТ ПО ТЕСТИРОВАНИЮ СТЕГАНОГРАФИИ\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Всего тестов: {stats['total_tests']}\n")
            f.write(f"Успешно: {stats['successful_tests']} ({stats['success_rate']:.1f}%)\n\n")
            
            for algo, s in stats['algorithms'].items():
                f.write(f"\n{algo.upper()}:\n")
                f.write(f"  PSNR: {s['avg_psnr']:.1f} ± {s['std_psnr']:.1f} dB\n")
                f.write(f"  SSIM: {s['avg_ssim']:.4f} ± {s['std_ssim']:.4f}\n")
                f.write(f"  MSE: {s['avg_mse']:.2f} ± {s['std_mse']:.2f}\n")
                f.write(f"  Время скрытия: {s['avg_hide_time']:.1f} ± {s['std_hide_time']:.1f} мс\n")
                f.write(f"  Время извлечения: {s['avg_extract_time']:.1f} ± {s['std_extract_time']:.1f} мс\n")
                f.write(f"  Скорость скрытия: {s['avg_hide_speed']/1000:.1f} кбит/с\n")
                f.write(f"  Скорость извлечения: {s['avg_extract_speed']/1000:.1f} кбит/с\n")
                f.write(f"  Увеличение размера: {s['avg_size_increase']:.1f}%\n")
                f.write(f"  Изменено пикселей: {s['avg_changed_pixels']:.1f}%\n")
        
        print(f"\nОтчет сохранен: {report_path}")
        print(f"Статистика: {self.output_dir / 'reports' / 'statistics.json'}")
        print(f"CSV: {self.output_dir / 'reports' / 'test_results.csv'}")
        print("\n" + "█" * 70)
        print("Тестирование завершено!")


def main():
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ СТЕГАНОГРАФИЧЕСКИХ АЛГОРИТМОВ")
    print("=" * 70)
    
    analyzer = SteganoAnalyzer(
        test_images_dir='test/test_images',
        output_dir='test/test_results'
    )
    
    analyzer.run_all_tests()
    analyzer.generate_report()


if __name__ == '__main__':
    main()