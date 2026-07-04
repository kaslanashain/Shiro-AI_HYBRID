/**
 * Shiro AI — Vision capture (webcam + upload) → multimodal backend
 */
(function(global) {
    'use strict';

    var webcamStream = null;
    var capturedBlob = null;
    var activeTab = 'upload';

    function getActiveCharacter() {
        if (global.CharacterState) return CharacterState.get();
        return global.currentCharacter || 'shiro';
    }

    function getAffectionLevel() {
        if (global.AffectionEngine && typeof AffectionEngine.getScore === 'function') {
            return AffectionEngine.getScore();
        }
        if (typeof global.currentAffection === 'number') return global.currentAffection;
        return 50;
    }

    function setTab(tab) {
        activeTab = tab;
        var uploadPanel = document.getElementById('visionUploadPanel');
        var webcamPanel = document.getElementById('visionWebcamPanel');
        var tabUpload = document.getElementById('visionTabUpload');
        var tabWebcam = document.getElementById('visionTabWebcam');
        if (uploadPanel) uploadPanel.style.display = tab === 'upload' ? 'block' : 'none';
        if (webcamPanel) webcamPanel.style.display = tab === 'webcam' ? 'block' : 'none';
        if (tabUpload) tabUpload.classList.toggle('active', tab === 'upload');
        if (tabWebcam) tabWebcam.classList.toggle('active', tab === 'webcam');
        if (tab === 'webcam') startWebcam();
        else stopWebcam();
    }

    function updateModalTitle() {
        var title = document.getElementById('cameraTitle');
        var char = getActiveCharacter();
        if (title) {
            title.textContent = char === 'sishin'
                ? 'Kirim Foto untuk Sishin'
                : 'Kirim Foto untuk Shiro';
        }
        var btn = document.getElementById('visionSendBtn');
        if (btn) {
            btn.textContent = char === 'sishin' ? 'Kirim ke Sishin' : 'Kirim ke Shiro';
        }
    }

    function showPreviewFromBlob(blob, previewEl) {
        if (!previewEl || !blob) return;
        var url = URL.createObjectURL(blob);
        previewEl.innerHTML = '<img src="' + url + '" alt="Preview">';
        previewEl.dataset.objectUrl = url;
    }

    function clearPreview() {
        var preview = document.getElementById('imagePreview');
        if (!preview) return;
        if (preview.dataset.objectUrl) {
            URL.revokeObjectURL(preview.dataset.objectUrl);
            delete preview.dataset.objectUrl;
        }
        preview.innerHTML = '';
        capturedBlob = null;
    }

    async function startWebcam() {
        var video = document.getElementById('webcamVideo');
        if (!video || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert('Webcam tidak didukung di browser/perangkat ini.');
            return;
        }
        try {
            stopWebcam();
            webcamStream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false
            });
            video.srcObject = webcamStream;
            await video.play();
        } catch (e) {
            console.error('[Vision] webcam error:', e);
            alert('Gagal akses kamera. Izinkan permission kamera di browser.');
        }
    }

    function stopWebcam() {
        if (webcamStream) {
            webcamStream.getTracks().forEach(function(t) { t.stop(); });
            webcamStream = null;
        }
        var video = document.getElementById('webcamVideo');
        if (video) video.srcObject = null;
    }

    function captureWebcamFrame() {
        var video = document.getElementById('webcamVideo');
        var canvas = document.getElementById('webcamCanvas');
        var preview = document.getElementById('imagePreview');
        if (!video || !canvas || !video.videoWidth) {
            alert('Kamera belum siap.');
            return;
        }
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        var ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);
        canvas.toBlob(function(blob) {
            if (!blob) return;
            capturedBlob = blob;
            showPreviewFromBlob(blob, preview);
        }, 'image/jpeg', 0.88);
    }

    function blobToBase64(blob) {
        return new Promise(function(resolve, reject) {
            var reader = new FileReader();
            reader.onload = function() { resolve(reader.result); };
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }

    async function getImageBlob() {
        if (capturedBlob) return capturedBlob;
        var fileInput = document.getElementById('imageUpload');
        if (fileInput && fileInput.files && fileInput.files[0]) {
            return fileInput.files[0];
        }
        return null;
    }

    async function sendVisionImage() {
        var blob = await getImageBlob();
        if (!blob) {
            alert('Pilih atau ambil foto terlebih dahulu.');
            return;
        }

        var char = getActiveCharacter();
        var affection = getAffectionLevel();
        var captionEl = document.getElementById('visionCaption');
        var caption = captionEl ? captionEl.value.trim() : '';
        var sendBtn = document.getElementById('visionSendBtn');
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = 'Menganalisis...';
        }

        try {
            var formData = new FormData();
            formData.append('image', blob, 'capture.jpg');
            formData.append('karakter', char);
            formData.append('character_name', char);
            formData.append('affection_level', String(affection));
            if (caption) formData.append('caption', caption);

            var response = await fetch('/upload', { method: 'POST', body: formData });
            var data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Upload gagal');
            }

            if (typeof global.closeCamera === 'function') {
                global.closeCamera();
            } else if (window.VisionCapture && VisionCapture.close) {
                VisionCapture.close();
            }
            if (typeof global.openChat === 'function') global.openChat();
            if (data.reply && typeof global.addMessage === 'function') {
                global.addMessage(caption || '[📷 Foto]', 'user');
                global.addMessage(data.reply, data.karakter || char);
            }
            if (data.status && typeof global.updateStatusBar === 'function') {
                global.updateStatusBar(data.status);
            }
            if (typeof global.putarAudio === 'function') {
                global.putarAudio(data.suara || data.reply, data.karakter || char);
            }

            if (!data.vision_ok) {
                console.warn('[Vision] API fallback — set GEMINI_API_KEY in .env');
            }
        } catch (err) {
            console.error('[Vision] send error:', err);
            alert(err.message || 'Gagal mengirim foto.');
        } finally {
            if (sendBtn) {
                sendBtn.disabled = false;
                updateModalTitle();
            }
        }
    }

    function openVisionModal() {
        updateModalTitle();
        setTab('upload');
        var modal = document.getElementById('cameraModal');
        if (modal) modal.classList.add('active');
    }

    function closeVisionModal() {
        stopWebcam();
        clearPreview();
        var fileInput = document.getElementById('imageUpload');
        if (fileInput) fileInput.value = '';
        var caption = document.getElementById('visionCaption');
        if (caption) caption.value = '';
        var modal = document.getElementById('cameraModal');
        if (modal) modal.classList.remove('active');
    }

    function init() {
        var tabUpload = document.getElementById('visionTabUpload');
        var tabWebcam = document.getElementById('visionTabWebcam');
        if (tabUpload) tabUpload.addEventListener('click', function() { setTab('upload'); });
        if (tabWebcam) tabWebcam.addEventListener('click', function() { setTab('webcam'); });

        var captureBtn = document.getElementById('webcamCaptureBtn');
        if (captureBtn) captureBtn.addEventListener('click', captureWebcamFrame);

        var sendBtn = document.getElementById('visionSendBtn');
        if (sendBtn) sendBtn.addEventListener('click', sendVisionImage);

        var fileInput = document.getElementById('imageUpload');
        if (fileInput) {
            fileInput.addEventListener('change', function() {
                capturedBlob = null;
                var preview = document.getElementById('imagePreview');
                if (this.files && this.files[0] && preview) {
                    showPreviewFromBlob(this.files[0], preview);
                }
            });
        }
    }

    global.VisionCapture = {
        open: openVisionModal,
        close: closeVisionModal,
        send: sendVisionImage,
        captureWebcam: captureWebcamFrame,
        blobToBase64: blobToBase64
    };

    global.uploadImage = sendVisionImage;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}(window));
