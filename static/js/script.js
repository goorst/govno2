document.addEventListener('DOMContentLoaded', function() {
        const uploadTextBtn = document.getElementById('uploadTextBtn');
        uploadTextBtn.addEventListener('click', function() {
            alert('test');
        });

        const imageBox = document.querySelector('.image-box');
        imageBox.addEventListener('click', function() {
            alert('Кликнуто на область загрузки изображения!');

            // document.getElementById('imageUpload').click();
        });
    });