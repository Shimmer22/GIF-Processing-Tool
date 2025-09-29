document.addEventListener('DOMContentLoaded', () => {
    const uploadBox = document.getElementById('upload-box');
    const fileInput = document.getElementById('file-input');
    const resultsDiv = document.getElementById('results');
    const spinner = document.getElementById('spinner');

    // --- 事件监听 ---
    uploadBox.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (event) => {
        const files = event.target.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadBox.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        uploadBox.addEventListener(eventName, () => uploadBox.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        uploadBox.addEventListener(eventName, () => uploadBox.classList.remove('dragover'), false);
    });

    uploadBox.addEventListener('drop', (event) => {
        const dt = event.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // --- 文件上传与处理 ---
    async function handleFileUpload(file) {
        if (!file.type.startsWith('image/gif')) {
            alert('请只上传GIF文件！');
            return;
        }

        resultsDiv.innerHTML = '';
        spinner.style.display = 'block';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '上传失败');
            }

            const data = await response.json();
            displayResults(data.results);

        } catch (error) {
            alert(`发生错误: ${error.message}`);
        } finally {
            spinner.style.display = 'none';
        }
    }

    // --- 显示结果 ---
    function displayResults(results) {
        resultsDiv.innerHTML = '';
        results.forEach(result => {
            const filename = result.url.split('/').pop();
            const card = document.createElement('div');
            card.className = 'preview-card';

            const img = document.createElement('img');
            img.src = result.url;

            // --- 文件信息和可编辑的文件名 ---
            const fileInfo = document.createElement('div');
            fileInfo.className = 'file-info';

            const durationText = document.createElement('p');
            durationText.textContent = `持续时间: ${result.duration}s`;
            durationText.style.marginBottom = '5px';

            const nameInput = document.createElement('input');
            nameInput.type = 'text';
            nameInput.value = result.default_filename;
            
            fileInfo.appendChild(durationText);
            fileInfo.appendChild(nameInput);
            // --- 结束 文件信息 ---

            const controls = document.createElement('div');
            controls.className = 'controls';

            const flipButton = document.createElement('button');
            flipButton.textContent = '左右翻转';
            flipButton.onclick = () => flipImage(filename, img);

            const downloadLink = document.createElement('a');
            downloadLink.href = result.url;
            downloadLink.textContent = '下载';
            downloadLink.download = result.default_filename;
            
            // 当输入框内容改变时，更新下载链接的文件名
            nameInput.addEventListener('input', () => {
                downloadLink.download = nameInput.value;
            });

            controls.appendChild(flipButton);
            controls.appendChild(downloadLink);

            // --- RGB 交换控件 ---
            const rgbControlSet = document.createElement('div');
            rgbControlSet.style.marginTop = '10px';

            const rgbSelect = document.createElement('select');
            const permutations = ['rgb', 'rbg', 'grb', 'gbr', 'brg', 'bgr'];
            permutations.forEach(p => {
                const option = document.createElement('option');
                option.value = p;
                option.textContent = p.toUpperCase();
                rgbSelect.appendChild(option);
            });

            const swapButton = document.createElement('button');
            swapButton.textContent = '交换通道';
            swapButton.onclick = () => swapRgb(filename, rgbSelect.value, img);
            
            rgbControlSet.appendChild(rgbSelect);
            rgbControlSet.appendChild(swapButton);
            controls.appendChild(rgbControlSet);
            // --- 结束 RGB 交换控件 ---

            card.appendChild(img);
            card.appendChild(fileInfo); // 添加文件信息部分
            card.appendChild(controls);
            resultsDiv.appendChild(card);
        });
    }

    // --- 交换RGB通道 ---
    async function swapRgb(filename, rgbMap, imgElement) {
        try {
            const response = await fetch(`/swap_rgb?filename=${filename}&rgb_map=${rgbMap}`, {
                method: 'POST',
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'RGB交换失败');
            }

            // 添加时间戳以强制浏览器重新加载图片
            imgElement.src = `${imgElement.src.split('?')[0]}?t=${new Date().getTime()}`;

        } catch (error) {
            alert(`RGB交换失败: ${error.message}`);
        }
    }

    // --- 翻转图像 ---
    async function flipImage(filename, imgElement) {
        try {
            const response = await fetch(`/flip?filename=${filename}`, {
                method: 'POST',
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || '翻转失败');
            }

            // 添加时间戳以强制浏览器重新加载图片
            imgElement.src = `${imgElement.src.split('?')[0]}?t=${new Date().getTime()}`;

        } catch (error) {
            alert(`翻转失败: ${error.message}`);
        }
    }
});