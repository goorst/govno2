document.addEventListener('DOMContentLoaded', function() {
    // Элементы DOM
    const imageBox = document.getElementById('imageBox');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const previewImage = document.getElementById('previewImage');
    const imageUpload = document.getElementById('imageUpload');
    const textInput = document.getElementById('textInput');
    const uploadTextBtn = document.getElementById('uploadTextBtn');
    const writeBtn = document.getElementById('writeBtn');
    const readBtn = document.getElementById('readBtn');
    const clearBtn = document.getElementById('clearBtn');
    const downloadStegoBtn = document.getElementById('downloadStegoBtn');

    let currentImageFile = null;

    // === ФУНКЦИЯ СБРОСА В ДЕФОЛТНОЕ СОСТОЯНИЕ ===
    function resetToDefault() {
        textInput.value = '';
        imageUpload.value = '';
        previewImage.style.display = 'none';
        uploadPlaceholder.style.display = 'flex';
        downloadStegoBtn.style.display = 'none';
        currentImageFile = null;
    }

    // === ОБРАБОТКА ВЫБОРА ИЗОБРАЖЕНИЯ ===
    function handleImageSelect(e) {
        const file = e.target.files[0] || (e.dataTransfer && e.dataTransfer.files[0]);
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            alert('Пожалуйста, выберите изображение!');
            return;
        }

        // Сохраняем файл
        currentImageFile = file;

        // Показываем preview
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            previewImage.style.display = 'block';
            uploadPlaceholder.style.display = 'none';
        };
        reader.readAsDataURL(file);
    }

    // === ЗАГРУЗКА ТЕКСТОВОГО ФАЙЛА ===
    uploadTextBtn.addEventListener('click', function() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('text_file', file);

            uploadTextBtn.textContent = 'Загрузка...';
            uploadTextBtn.disabled = true;

            fetch('/upload_text_file', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Server error');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    alert('Ошибка: ' + data.error);
                } else {
                    textInput.value = data.text;
                }
            })
            .catch(err => {
                console.error('Ошибка:', err);
                alert('Не удалось загрузить файл');
            })
            .finally(() => {
                uploadTextBtn.textContent = 'Загрузить TXT';
                uploadTextBtn.disabled = false;
            });
        };
        input.click();
    });

    // === КНОПКА WRITE (скрыть текст) ===
    writeBtn.addEventListener('click', function() {
        if (!currentImageFile) {
            alert('Сначала загрузите PNG изображение!');
            return;
        }
        
        if (!textInput.value.trim()) {
            alert('Введите текст для скрытия!');
            return;
        }

        // Показываем индикатор загрузки
        const originalText = writeBtn.textContent;
        writeBtn.textContent = 'Обработка...';
        writeBtn.disabled = true;

        // Создаем FormData
        const formData = new FormData();
        formData.append('image', currentImageFile);
        formData.append('text', textInput.value);

        // Отправляем запрос
        fetch('/hide_text', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network error');
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Успех!
            alert('Текст успешно скрыт в изображении!');
            
            // Показываем кнопку скачивания
            downloadStegoBtn.style.display = 'inline-block';
            
            // Настраиваем скачивание с сбросом состояния после скачивания
            downloadStegoBtn.onclick = function() {
                // Создаем временную ссылку для скачивания
                const downloadUrl = data.download_url;
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = data.stego_filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                // Сбрасываем состояние после скачивания
                setTimeout(resetToDefault, 100);
            };
        })
        .catch(err => {
            console.error('Ошибка:', err);
            alert('Ошибка: ' + err.message);
        })
        .finally(() => {
            writeBtn.textContent = originalText;
            writeBtn.disabled = false;
        });
    });

    // === КНОПКА READ (извлечь текст) ===
    readBtn.addEventListener('click', function() {
        if (!currentImageFile) {
            alert('Сначала загрузите PNG изображение со скрытым текстом!');
            return;
        }

        // Показываем индикатор загрузки
        const originalText = readBtn.textContent;
        readBtn.textContent = 'Чтение...';
        readBtn.disabled = true;

        // Создаем FormData
        const formData = new FormData();
        formData.append('image', currentImageFile);

        // Отправляем запрос
        fetch('/extract_text', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network error');
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Успех! Показываем извлеченный текст
            textInput.value = data.text;
            alert('Текст успешно извлечен из изображения!');
        })
        .catch(err => {
            console.error('Ошибка:', err);
            alert('Ошибка: ' + err.message);
        })
        .finally(() => {
            readBtn.textContent = originalText;
            readBtn.disabled = false;
        });
    });

    // === КНОПКА CLEAR ===
    clearBtn.addEventListener('click', function() {
        resetToDefault();
    });

    // === ОБРАБОТЧИКИ СОБЫТИЙ ===
    imageBox.addEventListener('click', function() {
        imageUpload.click();
    });

    imageUpload.addEventListener('change', handleImageSelect);

    // Drag and Drop
    imageBox.addEventListener('dragover', function(e) {
        e.preventDefault();
        imageBox.style.backgroundColor = '#2a2436';
    });

    imageBox.addEventListener('dragleave', function(e) {
        e.preventDefault();
        imageBox.style.backgroundColor = '#221B2A';
    });

    imageBox.addEventListener('drop', function(e) {
        e.preventDefault();
        imageBox.style.backgroundColor = '#221B2A';
        handleImageSelect(e);
    });
});