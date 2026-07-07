/**
 * Shiro AI — Vision & video capture (upload + webcam) → multimodal backend
 */
(function(global) {
    'use strict';

    var webcamStream = null;
    var capturedBlob = null;
    var capturedKind = null; /* 'image' | 'video' */
    var activeTab = 'photo';
    var mediaRecorder = null;
    var recordedChunks = [];
    var recordTimer = null;
    var recordStartedAt = 0;
    var MAX_RECORD_MS = 30000;

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

    function setProgress(visible, pct, label) {
        var wrap = document.getElementById('visionProgress');
        var bar = document.getElementById('visionProgressBar');
        var text = document.getElementById('visionProgressText');
        if (wrap) wrap.style.display = visible ? 'block' : 'none';
        if (bar) bar.style.width = (pct || 0) + '%';
        if (text) text.textContent = label || '';
    }

    function setTab(tab) {
        activeTab = tab;
        var photoPanel = document.getElementById('visionPhotoPanel');
        var videoPanel = document.getElementById('visionVideoPanel');
        var webcamPanel = document.getElementById('visionWebcamPanel');
        var tabPhoto = document.getElementById('visionTabPhoto');
        var tabVideo = document.getElementById('visionTabVideo');
        var tabWebcam = document.getElementById('visionTabWebcam');

        if (photoPanel) photoPanel.style.display = tab === 'photo' ? 'block' : 'none';
        if (videoPanel) videoPanel.style.display = tab === 'video' ? 'block' : 'none';
        if (webcamPanel) webcamPanel.style.display = tab === 'webcam' ? 'block' : 'none';
        if (tabPhoto) tabPhoto.classList.toggle('active', tab === 'photo');
        if (tabVideo) tabVideo.classList.toggle('active', tab === 'video');
        if (tabWebcam) tabWebcam.classList.toggle('active', tab === 'webcam');

        if (tab === 'webcam') startWebcam();
        else {
            stopWebcam();
            stopRecording(false);
        }
        updateModalTitle();
    }

    function updateModalTitle() {
        var title = document.getElementById('cameraTitle');
        var char = getActiveCharacter();
        var name = char === 'sishin' ? 'Sishin' : 'Shiro';
        if (title) {
            if (activeTab === 'video') title.textContent = 'Kirim Video untuk ' + name;
            else if (activeTab === 'webcam') title.textContent = 'Kamera — ' + name;
            else title.textContent = 'Kirim Foto untuk ' + name;
        }
        var btn = document.getElementById('visionSendBtn');
        if (btn) btn.textContent = 'Kirim ke ' + name;
    }

    function showPreviewFromBlob(blob, previewEl, kind) {
        if (!previewEl || !blob) return;
        clearPreview();
        capturedBlob = blob;
        capturedKind = kind || (blob.type && blob.type.indexOf('video') === 0 ? 'video' : 'image');
        var url = URL.createObjectURL(blob);
        previewEl.dataset.objectUrl = url;
        if (capturedKind === 'video') {
            previewEl.innerHTML = '<video src="' + url + '" controls playsinline class="vision-preview-video"></video>';
        } else {
            previewEl.innerHTML = '<img src="' + url + '" alt="Preview">';
        }
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
        capturedKind = null;
    }

    async function startWebcam() {
        var video = document.getElementById('webcamVideo');
        if (!video || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert('Webcam tidak didukung di browser/perangkat ini.');
            return;
        }
        try {
            stopWebcam();
            stopRecording(false);
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
        stopRecording(false);
        if (webcamStream) {
            webcamStream.getTracks().forEach(function(t) { t.stop(); });
            webcamStream = null;
        }
        var video = document.getElementById('webcamVideo');
        if (video) video.srcObject = null;
        var recBtn = document.getElementById('webcamRecordBtn');
        if (recBtn) {
            recBtn.classList.remove('recording');
            recBtn.innerHTML = '<i class="fas fa-video"></i> Rekam Video';
        }
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
            showPreviewFromBlob(blob, preview, 'image');
        }, 'image/jpeg', 0.88);
    }

    function getRecorderMime() {
        var types = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm', 'video/mp4'];
        for (var i = 0; i < types.length; i++) {
            if (window.MediaRecorder && MediaRecorder.isTypeSupported(types[i])) {
                return types[i];
            }
        }
        return 'video/webm';
    }

    function stopRecording(saveClip) {
        if (recordTimer) {
            clearInterval(recordTimer);
            recordTimer = null;
        }
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            try { mediaRecorder.stop(); } catch (e) { /* ignore */ }
        }
        if (!saveClip) {
            recordedChunks = [];
            mediaRecorder = null;
        }
    }

    function toggleWebcamRecording() {
        var recBtn = document.getElementById('webcamRecordBtn');
        var preview = document.getElementById('imagePreview');

        if (mediaRecorder && mediaRecorder.state === 'recording') {
            stopRecording(true);
            if (recBtn) {
                recBtn.classList.remove('recording');
                recBtn.innerHTML = '<i class="fas fa-video"></i> Rekam Video';
            }
            return;
        }

        if (!webcamStream) {
            alert('Kamera belum siap.');
            return;
        }
        if (!window.MediaRecorder) {
            alert('Browser tidak mendukung rekam video. Coba upload file video.');
            return;
        }

        recordedChunks = [];
        var mime = getRecorderMime();
        try {
            mediaRecorder = new MediaRecorder(webcamStream, { mimeType: mime });
        } catch (e) {
            mediaRecorder = new MediaRecorder(webcamStream);
            mime = mediaRecorder.mimeType || 'video/webm';
        }

        mediaRecorder.ondataavailable = function(ev) {
            if (ev.data && ev.data.size > 0) recordedChunks.push(ev.data);
        };
        mediaRecorder.onstop = function() {
            if (!recordedChunks.length) return;
            var blob = new Blob(recordedChunks, { type: mime });
            recordedChunks = [];
            mediaRecorder = null;
            showPreviewFromBlob(blob, preview, 'video');
        };

        mediaRecorder.start(250);
        recordStartedAt = Date.now();
        if (recBtn) {
            recBtn.classList.add('recording');
            recBtn.innerHTML = '<i class="fas fa-stop"></i> Berhenti';
        }
        recordTimer = setInterval(function() {
            if (Date.now() - recordStartedAt >= MAX_RECORD_MS) {
                stopRecording(true);
                if (recBtn) {
                    recBtn.classList.remove('recording');
                    recBtn.innerHTML = '<i class="fas fa-video"></i> Rekam Video';
                }
            }
        }, 500);
    }

    async function getMediaBlob() {
        if (capturedBlob) return { blob: capturedBlob, kind: capturedKind || 'image' };

        if (activeTab === 'photo') {
            var fileInput = document.getElementById('imageUpload');
            if (fileInput && fileInput.files && fileInput.files[0]) {
                return { blob: fileInput.files[0], kind: 'image' };
            }
        }
        if (activeTab === 'video') {
            var videoInput = document.getElementById('videoUpload');
            if (videoInput && videoInput.files && videoInput.files[0]) {
                return { blob: videoInput.files[0], kind: 'video' };
            }
        }
        return { blob: null, kind: null };
    }

    function handleVisionResponse(data, char, caption, media) {
        if (typeof global.closeCamera === 'function') global.closeCamera();
        else closeVisionModal();
        if (typeof global.openChat === 'function') global.openChat();

        var userLabel = caption;
        if (!userLabel) {
            if (media && media.kind === 'video') userLabel = '[🎬 Video]';
            else userLabel = '[📷 Foto]';
        }

        if (typeof global.addMessage === 'function') {
            if (media && media.previewUrl) {
                global.addMessage(userLabel, 'user', {
                    type: media.kind === 'video' ? 'video' : 'image',
                    url: media.previewUrl || media.serverUrl
                });
            } else {
                global.addMessage(userLabel, 'user');
            }
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
    }

    async function sendVisionMedia() {
        var media = await getMediaBlob();
        if (!media.blob) {
            alert('Pilih atau rekam media terlebih dahulu.');
            return;
        }

        var char = getActiveCharacter();
        var affection = getAffectionLevel();
        var captionEl = document.getElementById('visionCaption');
        var caption = captionEl ? captionEl.value.trim() : '';
        var sendBtn = document.getElementById('visionSendBtn');
        var isVideo = media.kind === 'video';

        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.textContent = isVideo ? 'Memproses video...' : 'Menganalisis...';
        }
        setProgress(true, 12, isVideo ? 'Mengunggah video...' : 'Mengunggah foto...');

        var previewUrl = null;
        if (capturedBlob) {
            previewUrl = URL.createObjectURL(capturedBlob);
        }

        try {
            var formData = new FormData();
            formData.append(isVideo ? 'video' : 'image', media.blob, isVideo ? 'capture.webm' : 'capture.jpg');
            formData.append('karakter', char);
            formData.append('character_name', char);
            formData.append('affection_level', String(affection));
            if (caption) formData.append('caption', caption);

            var endpoint = isVideo ? '/upload_video' : '/upload';
            setProgress(true, 35, isVideo ? 'Mengekstrak frame video...' : 'Menganalisis gambar...');

            var response = await fetch(endpoint, { method: 'POST', body: formData });
            setProgress(true, 78, 'Menunggu respons AI...');
            var data = await response.json();

            if (!response.ok) throw new Error(data.error || 'Upload gagal');

            setProgress(true, 100, 'Selesai!');
            handleVisionResponse(data, char, caption, {
                kind: isVideo ? 'video' : 'image',
                previewUrl: isVideo ? (data.video_url || previewUrl) : previewUrl,
                serverUrl: data.video_url
            });
        } catch (err) {
            console.error('[Vision] send error:', err);
            alert(err.message || 'Gagal mengirim media.');
        } finally {
            setProgress(false, 0, '');
            if (sendBtn) {
                sendBtn.disabled = false;
                updateModalTitle();
            }
        }
    }

    function openVisionModal(tab) {
        updateModalTitle();
        setTab(tab || 'photo');
        setProgress(false, 0, '');
        var modal = document.getElementById('cameraModal');
        if (modal) modal.classList.add('active');
    }

    function closeVisionModal() {
        stopWebcam();
        clearPreview();
        setProgress(false, 0, '');
        var fileInput = document.getElementById('imageUpload');
        var videoInput = document.getElementById('videoUpload');
        if (fileInput) fileInput.value = '';
        if (videoInput) videoInput.value = '';
        var caption = document.getElementById('visionCaption');
        if (caption) caption.value = '';
        var modal = document.getElementById('cameraModal');
        if (modal) modal.classList.remove('active');
    }

    function init() {
        var tabPhoto = document.getElementById('visionTabPhoto');
        var tabVideo = document.getElementById('visionTabVideo');
        var tabWebcam = document.getElementById('visionTabWebcam');
        if (tabPhoto) tabPhoto.addEventListener('click', function() { setTab('photo'); });
        if (tabVideo) tabVideo.addEventListener('click', function() { setTab('video'); });
        if (tabWebcam) tabWebcam.addEventListener('click', function() { setTab('webcam'); });

        var captureBtn = document.getElementById('webcamCaptureBtn');
        if (captureBtn) captureBtn.addEventListener('click', captureWebcamFrame);

        var recordBtn = document.getElementById('webcamRecordBtn');
        if (recordBtn) recordBtn.addEventListener('click', toggleWebcamRecording);

        var sendBtn = document.getElementById('visionSendBtn');
        if (sendBtn) sendBtn.addEventListener('click', sendVisionMedia);

        var fileInput = document.getElementById('imageUpload');
        if (fileInput) {
            fileInput.addEventListener('change', function() {
                var preview = document.getElementById('imagePreview');
                if (this.files && this.files[0] && preview) {
                    showPreviewFromBlob(this.files[0], preview, 'image');
                }
            });
        }

        var videoInput = document.getElementById('videoUpload');
        if (videoInput) {
            videoInput.addEventListener('change', function() {
                var preview = document.getElementById('imagePreview');
                var file = this.files && this.files[0];
                if (!file || !preview) return;
                if (file.size > 20 * 1024 * 1024) {
                    alert('Video maksimal 20 MB.');
                    this.value = '';
                    return;
                }
                showPreviewFromBlob(file, preview, 'video');
            });
        }
    }

    global.VisionCapture = {
        open: openVisionModal,
        close: closeVisionModal,
        send: sendVisionMedia,
        captureWebcam: captureWebcamFrame,
        openPhoto: function() { openVisionModal('photo'); },
        openVideo: function() { openVisionModal('video'); },
        openWebcam: function() { openVisionModal('webcam'); }
    };

    global.openVideoModal = function() { openVisionModal('video'); };
    global.uploadImage = sendVisionMedia;
    global.sendVisionImage = sendVisionMedia;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}(window));
