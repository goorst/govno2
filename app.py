from flask import Flask, render_template, request, jsonify, send_file
import os
from stegano_png import hide_text_png, extract_text_png
from stegano_jpg import hide_text_jpg, extract_text_jpg
from stegano_bmp import hide_text_bmp, extract_text_bmp
from stegano_webp import hide_text_webp, extract_text_webp
import io

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/hide_text', methods=['POST'])
def hide_text():
    """Основной эндпоинт для скрытия текста в изображении"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file'}), 400
            
        image_file = request.files['image']
        text = request.form.get('text', '').strip()
        
        if image_file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
            
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Определяем формат изображения
        filename_lower = image_file.filename.lower()
        
        if filename_lower.endswith('.png'):
            # Используем PNG алгоритм (LSB)
            output_stream = hide_text_png(image_file, text)
            output_extension = '.png'
            
        elif filename_lower.endswith(('.jpg', '.jpeg', '.jpe')):
            # Используем JPG алгоритм (DCT)
            output_stream = hide_text_jpg(image_file, text)
            output_extension = '.jpg'
            
        elif filename_lower.endswith('.bmp'):
            # Используем BMP алгоритм (LSB)
            output_stream = hide_text_bmp(image_file, text)
            output_extension = '.bmp'
            
        elif filename_lower.endswith('.webp'):
            # Используем WebP алгоритм (LSB)
            output_stream = hide_text_webp(image_file, text)
            output_extension = '.webp'
            
        else:
            return jsonify({'error': 'Unsupported image format. Use PNG, JPG, BMP, or WebP'}), 400

        # Сохраняем результат в uploads
        original_name = os.path.splitext(image_file.filename)[0]
        output_filename = f"{original_name}_stego{output_extension}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        with open(output_path, 'wb') as f:
            f.write(output_stream.getvalue())
        
        return jsonify({
            'success': True,
            'message': 'Text hidden successfully',
            'stego_filename': output_filename,
            'download_url': f'/download/{output_filename}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/extract_text', methods=['POST'])
def extract_text():
    """Эндпоинт для извлечения текста из изображения"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file'}), 400
            
        image_file = request.files['image']
        
        if image_file.filename == '':
            return jsonify({'error': 'No image selected'}), 400

        # Определяем формат изображения
        filename_lower = image_file.filename.lower()
        
        if filename_lower.endswith('.png'):
            extracted_text = extract_text_png(image_file)
            
        elif filename_lower.endswith(('.jpg', '.jpeg', '.jpe')):
            extracted_text = extract_text_jpg(image_file)
            
        elif filename_lower.endswith('.bmp'):
            extracted_text = extract_text_bmp(image_file)
            
        elif filename_lower.endswith('.webp'):
            extracted_text = extract_text_webp(image_file)
            
        else:
            return jsonify({'error': 'Unsupported image format. Use PNG, JPG, BMP, or WebP'}), 400
        
        if not extracted_text:
            return jsonify({'error': 'No hidden text found in the image'}), 400
        
        return jsonify({
            'success': True,
            'message': 'Text extracted successfully',
            'text': extracted_text
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Скачивание файла"""
    try:
        return send_file(
            os.path.join(app.config['UPLOAD_FOLDER'], filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': f'File not found: {e}'}), 404

@app.route('/upload_text_file', methods=['POST'])
def upload_text_file():
    """Загрузка текстового файла"""
    try:
        if 'text_file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['text_file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Для простоты - поддерживаем только TXT
        if not file.filename.lower().endswith('.txt'):
            return jsonify({'error': 'Only TXT files supported'}), 400
            
        content = file.read().decode('utf-8')
        return jsonify({'text': content})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)