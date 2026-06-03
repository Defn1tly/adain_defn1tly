document.addEventListener('DOMContentLoaded', function() {
    const contentInput = document.getElementById('content-input');
    const styleInput = document.getElementById('style-input');
    const contentImg = document.getElementById('content-img');
    const styleImg = document.getElementById('style-img');
    const stylizeBtn = document.getElementById('stylize-btn');
    const resultSection = document.getElementById('result-section');
    const resultImg = document.getElementById('result-img');
    const resultInfo = document.getElementById('result-info');
    const downloadBtn = document.getElementById('download-btn');
    const alphaSlider = document.getElementById('alpha');
    const alphaValue = document.getElementById('alpha-value');
    const contentSize = document.getElementById('content-size');
    const styleSize = document.getElementById('style-size');
    const cropCheck = document.getElementById('crop');
    const preserveColor = document.getElementById('preserve-color');
    const btnText = document.querySelector('.btn-text');
    const btnLoading = document.querySelector('.btn-loading');

// Проверка при вводе
    contentSize.addEventListener('input', function() {
        if (this.value > 1024) this.value = 1024;
        if (this.value <= 0) this.value = 1;
    });

    styleSize.addEventListener('input', function() {
        if (this.value > 1024) this.value = 1024;
        if (this.value <= 0) this.value = 1;
    });

    // Запрет 'e', '.', '-', '+'
    contentSize.addEventListener('keydown', function(e) {
        if (e.key === 'e' || e.key === 'E' || e.key === '.' || e.key === '-' || e.key === '+') {
            e.preventDefault();
        }
    });

    styleSize.addEventListener('keydown', function(e) {
        if (e.key === 'e' || e.key === 'E' || e.key === '.' || e.key === '-' || e.key === '+') {
            e.preventDefault();
        }
    });

    // Загрузка изображений
    contentInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                contentImg.src = e.target.result;
            };
            reader.readAsDataURL(file);
        }
    });

    styleInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                styleImg.src = e.target.result;
            };
            reader.readAsDataURL(file);
        }
    });

    // Клик по зоне загрузки
    document.getElementById('content-upload').addEventListener('click', () => contentInput.click());
    document.getElementById('style-upload').addEventListener('click', () => styleInput.click());

    // Слайдер alpha
    alphaSlider.addEventListener('input', function() {
        alphaValue.textContent = this.value;
    });

    // Кнопка стилизации
    stylizeBtn.addEventListener('click', async function() {
        if (!contentInput.files[0] || !styleInput.files[0]) {
            alert('Пожалуйста, выберите оба изображения');
            return;
        }

        btnText.style.display = 'none';
        btnLoading.style.display = 'inline-flex';
        stylizeBtn.disabled = true;

        const formData = new FormData();
        formData.append('content_image', contentInput.files[0]);
        formData.append('style_image', styleInput.files[0]);
        formData.append('alpha', alphaSlider.value);
        formData.append('preserve_color', preserveColor.checked);
        formData.append('content_size', contentSize.value);
        formData.append('style_size', styleSize.value);
        formData.append('crop', cropCheck.checked);

        const startTime = Date.now();

        try {
            const response = await fetch('/upload_and_stylize', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                resultImg.src = data.output_image;
                contentImg.src = data.content_image;
                styleImg.src = data.style_image;
                resultSection.style.display = 'block';
                
                // Информация о результате
                resultInfo.innerHTML = `
                    Время обработки: ${data.elapsed_time} сек<br>
                    Размер выхода: ${data.output_size.join(' × ')}
                `;
                
                downloadBtn.href = data.output_image;
                resultSection.scrollIntoView({ behavior: 'smooth' });
            } else {
                alert('Ошибка: ' + data.error);
            }
        } catch (error) {
            alert('Ошибка соединения с сервером');
            console.error(error);
        } finally {
            btnText.style.display = 'inline';
            btnLoading.style.display = 'none';
            stylizeBtn.disabled = false;
        }
    });

    // Drag & Drop
    setupDragDrop('content-upload', contentInput, contentImg);
    setupDragDrop('style-upload', styleInput, styleImg);

    function setupDragDrop(areaId, input, img) {
        const area = document.getElementById(areaId);
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            area.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        area.addEventListener('drop', (e) => {
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                input.files = e.dataTransfer.files;
                const reader = new FileReader();
                reader.onload = (e) => img.src = e.target.result;
                reader.readAsDataURL(file);
            }
        });
    }
});