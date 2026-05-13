import sys
import os
import io
import csv
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')

from skimage.metrics import structural_similarity as ssim
from skimage.metrics import peak_signal_noise_ratio as psnr

from stegano_png import hide_text_png, extract_text_png
from stegano_jpg import hide_text_jpg, extract_text_jpg
from stegano_bmp import hide_text_bmp, extract_text_bmp
from stegano_webp import hide_text_webp, extract_text_webp


class SteganoAnalyzer:
    ALGORITHMS = {
        'png': {
            'hide': hide_text_png,
            'extract': extract_text_png,
            'format_dir': 'png',
            'extension': '.png',
            'lossless': True,
            'color': '#e74c3c',
            'label': 'PNG'
        },
        'bmp': {
            'hide': hide_text_bmp,
            'extract': extract_text_bmp,
            'format_dir': 'bmp',
            'extension': '.bmp',
            'lossless': True,
            'color': '#3498db',
            'label': 'BMP'
        },
        'webp': {
            'hide': hide_text_webp,
            'extract': extract_text_webp,
            'format_dir': 'webp',
            'extension': '.webp',
            'lossless': True,
            'color': '#2ecc71',
            'label': 'WEBP'
        },
        'jpg': {
            'hide': hide_text_jpg,
            'extract': extract_text_jpg,
            'format_dir': 'jpg',
            'extension': '.jpg',
            'lossless': False,
            'color': '#9b59b6',
            'label': 'JPG'
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
        self.test_images = {}
        for algo_name, algo_info in self.ALGORITHMS.items():
            format_dir = self.test_images_dir / algo_info['format_dir']
            if format_dir.exists():
                images = []
                for ext in [algo_info['extension'], algo_info['extension'].upper()]:
                    images.extend(format_dir.glob(f'*{ext}'))
                self.test_images[algo_name] = images
                print(f"Найдено {len(images)} изображений для {algo_name.upper()}")
            else:
                print(f"Директория {format_dir} не найдена")
                self.test_images[algo_name] = []
        return self.test_images
    
    def generate_test_texts(self) -> List[tuple]:
        texts = [
            ('medium_eng', "This is a medium-sized test text for steganography analysis."),
            ('medium_rus', "Это тестовый текст среднего размера для анализа стеганографии.")
        ]
        return texts
    
    def generate_text_by_length(self, length: int, lang: str = 'eng') -> str:
        if lang == 'eng':
            base = "This is a test message for steganography analysis. " * 20
        else:
            base = "Это тестовое сообщение для анализа стеганографии. " * 20
        return base[:length]
    
    def calculate_metrics(self, original: Image.Image, stego: Image.Image) -> Dict:
        orig_array = np.array(original.convert('RGB'))
        stego_array = np.array(stego.convert('RGB'))
        metrics = {}
        try:
            metrics['psnr'] = psnr(orig_array, stego_array, data_range=255)
        except:
            metrics['psnr'] = float('inf')
        try:
            metrics['ssim'] = ssim(orig_array, stego_array, channel_axis=2, data_range=255)
        except:
            metrics['ssim'] = 1.0
        metrics['mse'] = np.mean((orig_array.astype(float) - stego_array.astype(float)) ** 2)
        metrics['mae'] = np.mean(np.abs(orig_array.astype(float) - stego_array.astype(float)))
        changed_pixels = np.sum(np.any(orig_array != stego_array, axis=2))
        total_pixels = orig_array.shape[0] * orig_array.shape[1]
        metrics['changed_pixels_percent'] = (changed_pixels / total_pixels) * 100
        return metrics
    
    def _run_single_test(self, image_path: Path, algorithm: str, text_name: str, text: str) -> Optional[Dict]:
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
            capacity = self.calculate_capacity(original_img, algorithm)
            result['capacity_bits'] = capacity['bits']
            result['capacity_bytes'] = capacity['bytes']
            result['file_size_original'] = image_path.stat().st_size
            text_bytes = len(text.encode('utf-8'))
            if capacity['bytes'] > 0:
                result['capacity_usage_percent'] = (text_bytes / capacity['bytes']) * 100
            if text_bytes > capacity['bytes']:
                result['error'] = "Text too large"
                return result
            with open(image_path, 'rb') as f:
                image_data = io.BytesIO(f.read())
            start_time = time.perf_counter()
            hide_func = self.ALGORITHMS[algorithm]['hide']
            if algorithm in ['png', 'bmp', 'webp']:
                stego_data = hide_func(image_data, text, self.STEGANO_KEY)
            else:
                stego_data = hide_func(image_data, text)
            result['hide_time'] = time.perf_counter() - start_time
            result['success'] = True
            bits_hidden = text_bytes * 8
            if result['hide_time'] > 0:
                result['hide_speed_bps'] = bits_hidden / result['hide_time']
            result['file_size_stego'] = len(stego_data.getvalue())
            if result['file_size_original'] > 0:
                result['size_increase_percent'] = ((result['file_size_stego'] - result['file_size_original']) /
                                                   result['file_size_original']) * 100
            stego_filename = f"{image_path.stem}_{algorithm}_{text_name}{self.ALGORITHMS[algorithm]['extension']}"
            stego_path = self.output_dir / 'stego_images' / stego_filename
            with open(stego_path, 'wb') as f:
                f.write(stego_data.getvalue())
            stego_img = Image.open(stego_path)
            metrics = self.calculate_metrics(original_img, stego_img)
            result.update(metrics)
            with open(stego_path, 'rb') as f:
                stego_data_for_extract = io.BytesIO(f.read())
            start_time = time.perf_counter()
            extract_func = self.ALGORITHMS[algorithm]['extract']
            if algorithm in ['png', 'bmp', 'webp']:
                extracted_text = extract_func(stego_data_for_extract, self.STEGANO_KEY)
            else:
                extracted_text = extract_func(stego_data_for_extract)
            result['extract_time'] = time.perf_counter() - start_time
            result['total_time'] = result['hide_time'] + result['extract_time']
            if result['extract_time'] > 0:
                result['extract_speed_bps'] = bits_hidden / result['extract_time']
            if extracted_text.strip() == text.strip():
                result['extraction_success'] = True
            else:
                result['error'] = "Extraction mismatch"
        except Exception as e:
            result['error'] = f"General: {str(e)[:30]}"
        return result
    
    def calculate_capacity(self, image: Image.Image, algorithm: str) -> Dict:
        width, height = image.size
        pixels = width * height
        if algorithm in ['png', 'bmp', 'webp']:
            return {'bits': pixels * 3, 'bytes': (pixels * 3) // 8}
        else:
            blocks_h = height // 8
            blocks_w = width // 8
            return {'bits': blocks_h * blocks_w, 'bytes': (blocks_h * blocks_w) // 8}
    
    # ========================================================================
    # ТЕСТ 1: Основной тест
    # ========================================================================
    def run_basic_tests(self):
        if not self.test_images:
            self.find_test_images()
        test_texts = self.generate_test_texts()
        self.results = []
        total_tests = sum(len(images) * len(test_texts) for images in self.test_images.values())
        current_test = 0
        print(f"\n{'='*70}")
        print(f"ТЕСТ 1: Основной тест. ВСЕГО: {total_tests}")
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
                    result = self._run_single_test(image_path, algo_name, text_name, text)
                    if result:
                        self.results.append(result)
                        if result['success'] and result['extraction_success']:
                            print(f" ✓ PSNR: {result['psnr']:5.1f} dB, {result['total_time']*1000:6.1f} мс")
                        else:
                            print(f" ✗ {result['error'][:30]}")
                    else:
                        print(" ✗ Ошибка")
        successful = sum(1 for r in self.results if r['success'] and r['extraction_success'])
        print(f"\nЗавершено. Успешно: {successful}/{len(self.results)} ({successful/len(self.results)*100:.1f}%)")
    
    # ========================================================================
    # ТЕСТ 2: Зависимость MSE и PSNR от длины сообщения
    # ========================================================================
    def test_message_length_impact(self):
        print(f"\n{'='*70}")
        print(f"ТЕСТ 2: Зависимость качества от длины сообщения")
        print(f"{'='*70}")
        message_lengths = [100, 250, 500, 1000]
        languages = ['eng', 'rus']
        formats = ['png', 'bmp', 'webp']
        images_per_format = 5
        results_length = {fmt: {lang: {length: {'mse': [], 'psnr': []}
                                       for length in message_lengths}
                                for lang in languages}
                         for fmt in formats}
        for fmt in formats:
            images = self.test_images.get(fmt, [])[:images_per_format]
            if not images:
                continue
            print(f"\n{self.ALGORITHMS[fmt]['label']} ({len(images)} изображений)")
            for image_path in images:
                for lang in languages:
                    for length in message_lengths:
                        text = self.generate_text_by_length(length, lang)
                        print(f"  {image_path.name[:20]:20s} - {lang}:{length:4d}...", end='', flush=True)
                        result = self._run_single_test(image_path, fmt, f'{lang}_{length}', text)
                        if result and result['success'] and result['extraction_success']:
                            results_length[fmt][lang][length]['mse'].append(result['mse'])
                            results_length[fmt][lang][length]['psnr'].append(result['psnr'])
                            print(f" ✓ MSE:{result['mse']:.4f} PSNR:{result['psnr']:.1f}")
                        else:
                            print(f" ✗")
        self._plot_message_length_impact(results_length, message_lengths, languages, formats)
        return results_length
    
    def _plot_message_length_impact(self, results, message_lengths, languages, formats):
        charts_dir = self.output_dir / 'charts'
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        markers_list = {'png': 'o', 'bmp': 's', 'webp': '^'}
        ax = axes[0]
        for fmt in formats:
            marker = markers_list[fmt]
            for lang in languages:
                mse_means = []
                for length in message_lengths:
                    vals = results[fmt][lang][length]['mse']
                    mse_means.append(np.mean(vals) if vals else np.nan)
                linestyle = '-' if lang == 'eng' else '--'
                label = f"{self.ALGORITHMS[fmt]['label']} ({'EN' if lang == 'eng' else 'RU'})"
                ax.plot(message_lengths, mse_means,
                    marker=marker, linestyle=linestyle,
                    color=self.ALGORITHMS[fmt]['color'],
                    label=label,
                    linewidth=2.5, markersize=10,
                    markerfacecolor='white', markeredgewidth=2.5)
        from matplotlib.lines import Line2D
        legend_elements = []
        for fmt in formats:
            legend_elements.append(Line2D([0], [0], marker=markers_list[fmt], color=self.ALGORITHMS[fmt]['color'],
                                        label=self.ALGORITHMS[fmt]['label'],
                                        markerfacecolor='white', markersize=10, markeredgewidth=2,
                                        linewidth=2.5))
        legend_elements.append(Line2D([0], [0], color='black', linestyle='-', linewidth=2.5, label='──── EN (английский)'))
        legend_elements.append(Line2D([0], [0], color='black', linestyle='--', linewidth=2.5, label='---- RU (русский)'))
        ax.set_title('MSE vs Длина сообщения', fontsize=14, fontweight='bold')
        ax.set_xlabel('Длина сообщения (символов)', fontsize=12)
        ax.set_ylabel('MSE', fontsize=12)
        ax.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.95, ncol=2)
        ax.grid(True, alpha=0.3)
        ax = axes[1]
        for fmt in formats:
            marker = markers_list[fmt]
            for lang in languages:
                psnr_means = []
                for length in message_lengths:
                    vals = results[fmt][lang][length]['psnr']
                    psnr_means.append(np.mean(vals) if vals else np.nan)
                linestyle = '-' if lang == 'eng' else '--'
                label = f"{self.ALGORITHMS[fmt]['label']} ({'EN' if lang == 'eng' else 'RU'})"
                ax.plot(message_lengths, psnr_means,
                    marker=marker, linestyle=linestyle,
                    color=self.ALGORITHMS[fmt]['color'],
                    label=label,
                    linewidth=2.5, markersize=10,
                    markerfacecolor='white', markeredgewidth=2.5)
        legend_elements_psnr = []
        for fmt in formats:
            legend_elements_psnr.append(Line2D([0], [0], marker=markers_list[fmt], color=self.ALGORITHMS[fmt]['color'],
                                            label=self.ALGORITHMS[fmt]['label'],
                                            markerfacecolor='white', markersize=10, markeredgewidth=2,
                                            linewidth=2.5))
        legend_elements_psnr.append(Line2D([0], [0], color='black', linestyle='-', linewidth=2.5, label='──── EN (английский)'))
        legend_elements_psnr.append(Line2D([0], [0], color='black', linestyle='--', linewidth=2.5, label='---- RU (русский)'))
        ax.set_title('PSNR vs Длина сообщения', fontsize=14, fontweight='bold')
        ax.set_xlabel('Длина сообщения (символов)', fontsize=12)
        ax.set_ylabel('PSNR (dB)', fontsize=12)
        ax.legend(handles=legend_elements_psnr, loc='upper right', fontsize=9, framealpha=0.95, ncol=2)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(charts_dir / 'message_length_impact.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\nГрафик зависимости от длины сохранен в {charts_dir}")

    # ========================================================================
    # НОВЫЙ ТЕСТ: Зависимость изменения размера от длины сообщения
    # ========================================================================
    def test_size_vs_message_length(self):
        print(f"\n{'='*70}")
        print(f"ТЕСТ: Зависимость изменения размера файла от длины сообщения")
        print(f"{'='*70}")
        message_lengths = [50, 100, 250, 500, 1000, 2000, 4000]
        formats = ['png', 'bmp', 'webp', 'jpg']
        images_per_format = 3
        size_data = {fmt: {length: [] for length in message_lengths} for fmt in formats}
        
        for fmt in formats:
            images = self.test_images.get(fmt, [])[:images_per_format]
            if not images:
                print(f"Предупреждение: нет изображений для {fmt}, пропускаем")
                continue
            print(f"\n{self.ALGORITHMS[fmt]['label']} ({len(images)} изображений)")
            for img_path in images:
                for length in message_lengths:
                    text = self.generate_text_by_length(length, 'eng')
                    print(f"  {img_path.name[:20]:20s} - длина {length:4d}...", end='', flush=True)
                    result = self._run_single_test(img_path, fmt, f'size_{length}', text)
                    if result and result['success'] and result['extraction_success']:
                        size_data[fmt][length].append(result['size_increase_percent'])
                        print(f" ✓ изменение: {result['size_increase_percent']:+.2f}%")
                    else:
                        print(f" ✗ ошибка")
        self._plot_size_vs_length(size_data, message_lengths, formats)
        return size_data

    def _plot_size_vs_length(self, size_data, message_lengths, formats):
        charts_dir = self.output_dir / 'charts'
        plt.figure(figsize=(10, 6))
        markers = {'png': 'o', 'bmp': 's', 'webp': '^', 'jpg': 'D'}
        for fmt in formats:
            means = []
            for length in message_lengths:
                vals = size_data[fmt][length]
                means.append(np.mean(vals) if vals else np.nan)
            valid = ~np.isnan(means)
            if np.any(valid):
                x = np.array(message_lengths)[valid]
                y = np.array(means)[valid]
                plt.plot(x, y,
                        marker=markers.get(fmt, 'o'),
                        color=self.ALGORITHMS[fmt]['color'],
                        label=self.ALGORITHMS[fmt]['label'],
                        linewidth=2.5, markersize=8)
        plt.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        plt.xlabel('Длина сообщения (символов)', fontsize=12)
        plt.ylabel('Изменение размера файла (%)', fontsize=12)
        plt.title('Зависимость изменения размера от длины скрытого сообщения', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(charts_dir / 'size_vs_length.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\nГрафик изменения размера сохранён: {charts_dir / 'size_vs_length.png'}")

    # ========================================================================
    # ТЕСТ 3: BER для JPG
    # ========================================================================
    def test_jpg_compression_ber(self):
        print(f"\n{'='*70}")
        print(f"ТЕСТ 3: BER для JPG в зависимости от сжатия")
        print(f"{'='*70}")
        quality_levels = [5, 10, 15, 30, 50, 70, 90, 100]
        languages = ['eng', 'rus']
        # Генерируем тексты одинаковой длины в БАЙТАХ (не символах!)
        # Английский: 200 символов = 200 байт
        # Русский: 100 символов = 200 байт (кириллица = 2 байта на символ в UTF-8)
        test_text = self.generate_text_by_length(200, 'eng')
        test_text_rus = self.generate_text_by_length(100, 'rus')  # ИСПРАВЛЕНО: 100 вместо 200
        
        images = self.test_images.get('jpg', [])[:3]
        if not images:
            print("Нет JPG изображений!")
            return
        
        ber_results = {lang: {q: [] for q in quality_levels} for lang in languages}
        
        for image_path in images:
            print(f"\n{image_path.name}")
            for lang, text in [('eng', test_text), ('rus', test_text_rus)]:
                with open(image_path, 'rb') as f:
                    image_data = io.BytesIO(f.read())
                try:
                    stego_data = self.ALGORITHMS['jpg']['hide'](image_data, text)
                    stego_img = Image.open(stego_data)
                except Exception as e:
                    print(f"  Ошибка встраивания: {e}")
                    continue
                
                # Вычисляем реальную длину сообщения в битах
                text_bytes_len = len(text.encode('utf-8'))
                actual_bits_len = text_bytes_len * 8
                
                original_bits = self._extract_bits_from_jpg(stego_img)
                
                for quality in quality_levels:
                    print(f"  {lang} quality={quality:3d}%...", end='', flush=True)
                    compressed = io.BytesIO()
                    stego_img.save(compressed, format='JPEG', quality=quality)
                    compressed.seek(0)
                    compressed_img = Image.open(compressed)
                    extracted_bits = self._extract_bits_from_jpg(compressed_img)
                    
                    if len(original_bits) > 0 and len(extracted_bits) > 0:
                        # Сравниваем ТОЛЬКО биты сообщения (не шум!)
                        min_len = min(actual_bits_len, len(original_bits), len(extracted_bits))
                        ber = sum(1 for i in range(min_len) if original_bits[i] != extracted_bits[i]) / min_len
                    else:
                        ber = 1.0
                    ber_results[lang][quality].append(ber)
                    print(f" BER: {ber:.4f}")
        
        self._plot_jpg_ber(ber_results, quality_levels, languages)
        return ber_results
    
    def _extract_bits_from_jpg(self, img: Image.Image) -> list:
        from scipy.fftpack import dct
        img_array = np.array(img.convert('RGB'), dtype=np.float32)
        height, width = img_array.shape[:2]
        r, g, b = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2]
        y_channel = 0.299 * r + 0.587 * g + 0.114 * b
        blocks_h = height // 8
        blocks_w = width // 8
        bits = []
        for y_block in range(min(blocks_h, 10)):
            for x_block in range(blocks_w):
                y_start = y_block * 8
                x_start = x_block * 8
                block = y_channel[y_start:y_start+8, x_start:x_start+8]
                dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
                value = dct_block[4, 4]
                bits.append(1 if value > 0 else 0)
        return bits
    
    def _plot_jpg_ber(self, ber_results, quality_levels, languages):
        charts_dir = self.output_dir / 'charts'
        fig, ax = plt.subplots(figsize=(12, 7))
        colors = {'eng': '#3498db', 'rus': '#e74c3c'}
        labels = {'eng': 'Английский текст', 'rus': 'Русский текст'}
        markers = {'eng': 'o', 'rus': 's'}
        compression_levels = [100 - q for q in quality_levels]
        for lang in languages:
            ber_means = []
            for q in quality_levels:
                vals = ber_results[lang][q]
                ber_means.append(np.mean(vals) if vals else np.nan)
            ax.plot(compression_levels, ber_means,
                color=colors[lang], linewidth=2,
                marker=markers[lang], markersize=10,
                label=labels[lang], zorder=3)
            for comp, ber in zip(compression_levels, ber_means):
                if not np.isnan(ber):
                    if lang == 'eng':
                        ax.annotate(f'{ber:.3f}', (comp, ber),
                                textcoords="offset points",
                                xytext=(0, 12),
                                ha='center', fontsize=9,
                                color=colors[lang], fontweight='bold')
                    else:
                        ax.annotate(f'{ber:.3f}', (comp, ber),
                                textcoords="offset points",
                                xytext=(0, -18),
                                ha='center', fontsize=9,
                                color=colors[lang], fontweight='bold')
        ax.axvspan(70, 100, alpha=0.05, color='red', label='Сильное сжатие')
        ax.axvspan(30, 70, alpha=0.05, color='yellow', label='Среднее сжатие')
        ax.axvspan(0, 30, alpha=0.05, color='green', label='Слабое сжатие')
        ax.set_title('BER vs Сила сжатия JPG\n(чем сильнее сжатие, тем выше BER)',
                    fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel('Сила сжатия (%)', fontsize=12)
        ax.set_ylabel('Bit Error Rate (BER)', fontsize=12)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 0.65)
        ax.set_xlim(0, 100)
        ax.axhline(y=0.1, color='orange', linestyle='--', alpha=0.7, linewidth=1.5,
                label='Порог BER = 0.1')
        ax.legend(loc='upper left', fontsize=10)
        plt.tight_layout()
        plt.savefig(charts_dir / 'jpg_ber_vs_quality.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\nГрафик BER сохранен в {charts_dir}")

    # ========================================================================
    # СТАРЫЕ ГРАФИКИ (качество, время, размер, успешность)
    # ========================================================================
    def generate_charts(self):
        successful_tests = [r for r in self.results if r['success'] and r['extraction_success']]
        if not successful_tests:
            return
        charts_dir = self.output_dir / 'charts'
        algorithms = list(self.ALGORITHMS.keys())
        algo_names = [a.upper() for a in algorithms]
        colors = [self.ALGORITHMS[a]['color'] for a in algorithms]
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # 1. PSNR и SSIM
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        ax = axes[0]
        psnr_means, psnr_stds = [], []
        for algo in algorithms:
            vals = [r['psnr'] for r in successful_tests if r['algorithm'] == algo and r['psnr'] != float('inf')]
            psnr_means.append(np.mean(vals) if vals else 0)
            psnr_stds.append(np.std(vals) if vals else 0)
        bars = ax.bar(algo_names, psnr_means, color=colors, yerr=psnr_stds, capsize=5)
        for bar, val, std in zip(bars, psnr_means, psnr_stds):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 2,
                    f'{val:.1f} dB', ha='center', va='bottom', fontsize=11, fontweight='bold')
        ax.set_title('PSNR (>40 dB - отлично)', fontsize=13, fontweight='bold', pad=15)
        ax.set_ylabel('PSNR (dB)')
        ax.axhline(y=40, color='orange', linestyle='--', alpha=0.7, label='Порог качества')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')
        ax = axes[1]
        ssim_means, ssim_stds = [], []
        for algo in algorithms:
            vals = [r['ssim'] for r in successful_tests if r['algorithm'] == algo]
            ssim_means.append(np.mean(vals) if vals else 0)
            ssim_stds.append(np.std(vals) if vals else 0)
        bars = ax.bar(algo_names, ssim_means, color=colors, yerr=ssim_stds, capsize=5)
        for bar, val, std in zip(bars, ssim_means, ssim_stds):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.02,
                    f'{val:.4f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
        ax.set_title('SSIM (>0.95 - отлично)', fontsize=13, fontweight='bold', pad=15)
        ax.set_ylabel('SSIM')
        ax.set_ylim(0.9, 1.05)
        ax.axhline(y=0.95, color='orange', linestyle='--', alpha=0.7, label='Порог качества')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(charts_dir / 'quality_metrics.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 2. Время выполнения
        fig, ax = plt.subplots(figsize=(12, 7))
        x = np.arange(len(algorithms))
        width = 0.35
        hide_means, hide_stds, extract_means, extract_stds = [], [], [], []
        for algo in algorithms:
            h_vals = [r['hide_time']*1000 for r in successful_tests if r['algorithm'] == algo]
            e_vals = [r['extract_time']*1000 for r in successful_tests if r['algorithm'] == algo]
            hide_means.append(np.mean(h_vals) if h_vals else 0)
            hide_stds.append(np.std(h_vals) if h_vals else 0)
            extract_means.append(np.mean(e_vals) if e_vals else 0)
            extract_stds.append(np.std(e_vals) if e_vals else 0)
        ax.bar(x - width/2, hide_means, width, label='Скрытие',
               color=['#2ecc71' if a != 'jpg' else '#c0392b' for a in algorithms],
               yerr=hide_stds, capsize=5)
        ax.bar(x + width/2, extract_means, width, label='Извлечение',
               color=['#27ae60' if a != 'jpg' else '#e74c3c' for a in algorithms],
               yerr=extract_stds, capsize=5)
        for bar, val in zip(ax.patches[:len(algorithms)], hide_means):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 100,
                       f'{val:.1f}', ha='center', fontsize=8)
        ax.set_title('Среднее время выполнения', fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel('Время (мс)')
        ax.set_xticks(x)
        ax.set_xticklabels(algo_names)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(charts_dir / 'time_performance.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 3. Размер файла и MSE (старый столбчатый график)
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        ax = axes[0]
        size_means, size_stds = [], []
        for algo in algorithms:
            vals = [r['size_increase_percent'] for r in successful_tests if r['algorithm'] == algo]
            size_means.append(np.mean(vals) if vals else 0)
            size_stds.append(np.std(vals) if vals else 0)
        bars = ax.bar(algo_names, size_means, color=colors, yerr=size_stds, capsize=5)
        for bar, val in zip(bars, size_means):
            c = 'red' if abs(val) > 100 else 'black'
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(size_stds)*0.5 + abs(val)*0.05,
                    f'{val:.1f}%', ha='center', fontsize=11, fontweight='bold', color=c)
        ax.set_title('Увеличение размера файла', fontsize=13, fontweight='bold', pad=15)
        ax.set_ylabel('Увеличение (%)')
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax.grid(True, alpha=0.3, axis='y')
        ax = axes[1]
        mse_means, mse_stds = [], []
        for algo in algorithms:
            vals = [r['mse'] for r in successful_tests if r['algorithm'] == algo]
            mse_means.append(np.mean(vals) if vals else 0)
            mse_stds.append(np.std(vals) if vals else 0)
        bars = ax.bar(algo_names, mse_means, color=colors, yerr=mse_stds, capsize=5)
        for bar, val in zip(bars, mse_means):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(mse_stds)*0.5,
                       f'{val:.2f}', ha='center', fontsize=10)
        ax.set_title('MSE (чем меньше, тем лучше)', fontsize=13, fontweight='bold', pad=15)
        ax.set_ylabel('MSE')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(charts_dir / 'size_and_mse.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 4. Успешность
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        ax = axes[0]
        success_count = len(successful_tests)
        fail_count = len(self.results) - success_count
        sizes = [success_count, fail_count]
        labels = [f'Успешно\n{success_count} тестов', f'Ошибка\n{fail_count} тестов']
        ax.pie(sizes, explode=(0.05, 0), labels=labels,
               colors=['#2ecc71', '#e74c3c'],
               autopct='%1.1f%%', shadow=True, startangle=90,
               textprops={'fontsize': 13, 'fontweight': 'bold'})
        ax.set_title(f'Общая успешность ({len(self.results)} тестов)', fontsize=14, fontweight='bold', pad=20)
        ax = axes[1]
        algo_success_rates = []
        algo_test_counts = []
        for algo in algorithms:
            algo_tests = [r for r in self.results if r['algorithm'] == algo]
            algo_successful = [r for r in algo_tests if r['success'] and r['extraction_success']]
            rate = len(algo_successful) / len(algo_tests) * 100 if algo_tests else 0
            algo_success_rates.append(rate)
            algo_test_counts.append(len(algo_tests))
        bars = ax.bar(algo_names, algo_success_rates, color=colors, edgecolor='black', linewidth=1.5)
        for bar, rate, count in zip(bars, algo_success_rates, algo_test_counts):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
                    f'{rate:.1f}%\n({count} тестов)', ha='center', fontsize=11, fontweight='bold')
        ax.set_title('Успешность по алгоритмам', fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel('Успешность (%)')
        ax.set_ylim(0, 110)
        ax.axhline(y=80, color='orange', linestyle='--', alpha=0.7, label='Хороший результат')
        ax.axhline(y=95, color='green', linestyle='--', alpha=0.7, label='Отличный результат')
        ax.legend(loc='lower right')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plt.savefig(charts_dir / 'success_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        
        # 5. Сводная таблица
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.axis('off')
        table_data = [['Алгоритм', 'PSNR (dB)', 'SSIM', 'MSE', 'Время (мс)', 'Размер (%)', 'Успех (%)']]
        for algo in algorithms:
            algo_tests = [r for r in successful_tests if r['algorithm'] == algo]
            if algo_tests:
                psnr_val = np.mean([r['psnr'] for r in algo_tests if r['psnr'] != float('inf')])
                ssim_val = np.mean([r['ssim'] for r in algo_tests])
                mse_val = np.mean([r['mse'] for r in algo_tests])
                time_val = np.mean([r['total_time']*1000 for r in algo_tests])
                size_val = np.mean([r['size_increase_percent'] for r in algo_tests])
                all_tests = [r for r in self.results if r['algorithm'] == algo]
                success_val = len([r for r in all_tests if r['success'] and r['extraction_success']]) / len(all_tests) * 100 if all_tests else 0
                table_data.append([algo.upper(), f'{psnr_val:.1f}', f'{ssim_val:.4f}',
                                  f'{mse_val:.2f}', f'{time_val:.1f}', f'{size_val:.1f}', f'{success_val:.1f}'])
        table = ax.table(cellText=table_data, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1.2, 2.5)
        for i in range(len(table_data[0])):
            table[(0, i)].set_facecolor('#34495e')
            table[(0, i)].set_text_props(weight='bold', color='white')
        for i, algo in enumerate(algorithms, 1):
            if i < len(table_data):
                for j in range(len(table_data[0])):
                    table[(i, j)].set_facecolor(self.ALGORITHMS[algo]['color'] + '30')
        ax.set_title('СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ', fontsize=16, fontweight='bold', pad=20, loc='center')
        plt.tight_layout()
        plt.savefig(charts_dir / 'summary_table.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Графики сохранены в {charts_dir}")
    
    def save_results_to_csv(self, filename: str = 'test_results.csv'):
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
    
    # ========================================================================
    # ПОЛНЫЙ ОТЧЕТ
    # ========================================================================
    def generate_full_report(self):
        print("\n" + "█" * 70)
        print("█" + " " * 68 + "█")
        print("█" + " " * 23 + "ПОЛНЫЙ ОТЧЕТ" + " " * 24 + "█")
        print("█" + " " * 68 + "█")
        print("█" * 70)
        
        self.run_basic_tests()
        self.save_results_to_csv()
        self.generate_charts()
        self.test_message_length_impact()
        self.test_jpg_compression_ber()
        self.test_size_vs_message_length()   # НОВЫЙ ТЕСТ размера vs длина
        
        print("\n" + "█" * 70)
        print("Все тесты завершены!")
        print(f"Результаты в: {self.output_dir}")
        print("  - charts/quality_metrics.png")
        print("  - charts/time_performance.png")
        print("  - charts/size_and_mse.png       (среднее увеличение размера)")
        print("  - charts/size_vs_length.png     (зависимость размера от длины)")
        print("  - charts/success_analysis.png")
        print("  - charts/summary_table.png")
        print("  - charts/message_length_impact.png")
        print("  - charts/jpg_ber_vs_quality.png")


def main():
    print("=" * 70)
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ СТЕГАНОГРАФИЧЕСКИХ АЛГОРИТМОВ")
    print("=" * 70)
    analyzer = SteganoAnalyzer(
        test_images_dir='test/test_images',
        output_dir='test/test_results'
    )
    analyzer.find_test_images()
    analyzer.generate_full_report()


if __name__ == '__main__':
    main()