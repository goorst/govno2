from flask import Flask, render_template, request, jsonify, send_file
import os
from stegano_png import hide_text_png, extract_text_png
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
        # Проверяем наличие файла и текста
        if 'image' not in request.files:
            return jsonify({'error': 'No image file'}), 400
            
        image_file = request.files['image']
        text = request.form.get('text', '').strip()
        
        if image_file.filename == '':
            return jsonify({'error': 'No image selected'}), 400
            
        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Проверяем что это PNG
        if not image_file.filename.lower().endswith('.png'):
            return jsonify({'error': 'Only PNG images supported'}), 400

        # Скрываем текст в изображении
        output_stream = hide_text_png(image_file, text)
        
        # Сохраняем результат в uploads
        original_name = os.path.splitext(image_file.filename)[0]
        output_filename = f"{original_name}_stego.png"
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

        # Проверяем что это PNG
        if not image_file.filename.lower().endswith('.png'):
            return jsonify({'error': 'Only PNG images supported'}), 400

        # Извлекаем текст из изображения
        extracted_text = extract_text_png(image_file)
        
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