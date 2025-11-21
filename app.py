from flask import Flask, render_template, request, jsonify, send_from_directory
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    return jsonify({'message': 'Image uploaded successfully', 'path': filepath})

@app.route('/upload_text', methods=['POST'])
def upload_text():
    if 'text_file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['text_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    content = file.read().decode('utf-8')
    return jsonify({'text': content})

if __name__ == '__main__':
    app.run(debug=True)