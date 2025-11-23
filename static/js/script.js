// document.addEventListener('DOMContentLoaded', function() {
//     const imageBox = document.getElementById('imageBox');
//     const uploadPlaceholder = document.getElementById('uploadPlaceholder');
//     const previewImage = document.getElementById('previewImage');
//     const imageUpload = document.getElementById('imageUpload');

//     // Кнопка "Загрузить DOCX/TXT"
//     const uploadTextBtn = document.getElementById('uploadTextBtn');
//     uploadTextBtn.addEventListener('click', function() {
//         alert('test');
//     });

//     // Клик по блоку — открывает файловый диалог
//     imageBox.addEventListener('click', function(e) {
//         if (!e.target.closest('#previewImage')) {
//             imageUpload.click();
//         }
//     });

//     // Изменение файла
//     imageUpload.addEventListener('change', handleFileSelect);

//     // Перетаскивание
//     imageBox.addEventListener('dragover', function(e) {
//         e.preventDefault();
//         imageBox.style.backgroundColor = '#2a2436';
//     });

//     imageBox.addEventListener('dragleave', function(e) {
//         e.preventDefault();
//         imageBox.style.backgroundColor = '#221B2A';
//     });

//     imageBox.addEventListener('drop', function(e) {
//         e.preventDefault();
//         imageBox.style.backgroundColor = '#221B2A';
//         if (e.dataTransfer.files.length > 0) {
//             handleFileSelect({ target: { files: e.dataTransfer.files } });
//         }
//     });

//     function handleFileSelect(e) {
//         const file = e.target.files[0];
//         if (!file) return;

//         if (!file.type.startsWith('image/')) {
//             alert('Пожалуйста, выберите изображение!');
//             return;
//         }

//         const reader = new FileReader();
//         reader.onload = function(e) {
//             previewImage.src = e.target.result;
//             previewImage.style.display = 'block';
//             uploadPlaceholder.style.display = 'none';
//         };
//         reader.readAsDataURL(file);
//     }

//     // Кнопка Clear
//     clearBtn.addEventListener('click', function() {
//         // Очистить текстовое поле
//         textInput.value = '';
//         // Сбросить input file
//         imageUpload.value = '';
//         // Скрыть preview, показать placeholder
//         previewImage.style.display = 'none';
//         uploadPlaceholder.style.display = 'flex';

//         // Сбросить фон (на случай, если остался hover)
//         imageBox.style.backgroundColor = '#221B2A';
//     });

// });


document.addEventListener('DOMContentLoaded', function() {
    const imageBox = document.getElementById('imageBox');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const previewImage = document.getElementById('previewImage');
    const imageUpload = document.getElementById('imageUpload');
    const textInput = document.getElementById('textInput');
    const clearBtn = document.getElementById('clearBtn');

    // === ЗАГРУЗКА ИЗОБРАЖЕНИЯ НА СЕРВЕР ===
    function handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            alert('Пожалуйста, выберите изображение!');
            return;
        }

        // Показываем preview в браузере
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            previewImage.style.display = 'block';
            uploadPlaceholder.style.display = 'none';
        };
        reader.readAsDataURL(file);

        // === ОТПРАВКА НА PYTHON (/upload_image) ===
        const formData = new FormData();
        formData.append('image', file);

        fetch('/upload_image', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert('Ошибка загрузки: ' + data.error);
            } else {
                console.log('Изображение сохранено на сервере:', data.path);
            }
        })
        .catch(err => {
            console.error('Ошибка сети:', err);
            alert('Не удалось отправить изображение на сервер');
        });
    }

    // === ЗАГРУЗКА ТЕКСТОВОГО ФАЙЛА ===
    const uploadTextBtn = document.getElementById('uploadTextBtn');
    uploadTextBtn.addEventListener('click', function() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.txt,.docx';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('text_file', file);

            fetch('/upload_text', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert('Ошибка: ' + data.error);
                } else {
                    textInput.value = data.text; // Вставить текст в поле
                    alert('Текст загружен!');
                }
            })
            .catch(err => {
                console.error('Ошибка:', err);
                alert('Не удалось загрузить текст');
            });
        };
        input.click();
    });

    // === ОСТАЛЬНЫЕ СОБЫТИЯ ===
    imageBox.addEventListener('click', function(e) {
        if (!e.target.closest('#previewImage')) {
            imageUpload.click();
        }
    });

    imageUpload.addEventListener('change', handleFileSelect);

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
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect({ target: { files: e.dataTransfer.files } });
        }
    });

    // === CLEAR ===
    clearBtn.addEventListener('click', function() {
        textInput.value = '';
        imageUpload.value = '';
        previewImage.style.display = 'none';
        uploadPlaceholder.style.display = 'flex';
        imageBox.style.backgroundColor = '#221B2A';
    });
});