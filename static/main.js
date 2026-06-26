document.addEventListener('DOMContentLoaded', () => {

    const kotakObrolan = document.getElementById('kotak-obrolan');
    const maskot = document.getElementById('shiro-mascot');
    const btnTutup = document.getElementById('tombol-tutup');
    const inputPesan = document.getElementById('input-pesan');
    const tombolKirim = document.getElementById('tombol-kirim');
    const tombolMic = document.getElementById('tombol-mic');
    const tombolUpload = document.getElementById('tombol-upload');
    const fileInput = document.getElementById('file-input');
    const riwayat = document.getElementById('riwayat-pesan');
    const bubbleIntro = document.getElementById('bubbleIntro');
    const charCount = document.getElementById('charCount');
    const statusText = document.getElementById('status-text');

    let isListening = false;
    let audioPlayer = null;

    function tampilkanObrolan() {
        kotakObrolan.classList.remove('sembunyi');
        bubbleIntro.style.display = 'none';
        setTimeout(() => inputPesan.focus(), 300);
    }

    function sembunyikanObrolan() {
        kotakObrolan.classList.add('sembunyi');
        setTimeout(() => { bubbleIntro.style.display = 'block'; }, 500);
    }

    function tambahPesanUser(teks) {
        const div = document.createElement('div');
        div.className = 'pesan-user';
        div.textContent = teks;
        riwayat.appendChild(div);
        riwayat.scrollTop = riwayat.scrollHeight;
    }

    function tambahPesanShiro(teks) {
        const div = document.createElement('div');
        div.className = 'pesan-shiro';
        div.textContent = teks;
        riwayat.appendChild(div);
        riwayat.scrollTop = riwayat.scrollHeight;
    }

    function updateCharCount() {
        const panjang = inputPesan.value.length;
        charCount.textContent = panjang;
        charCount.style.color = panjang > 180 ? '#ff6b8a' : '#a07a7a';
    }

    // ===== PUTAR AUDIO DENGAN DUKUNGAN KARAKTER =====
    async function putarAudio(teks, karakter = 'shiro') {
        if (!teks) return;
        try {
            const response = await fetch('/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    text: teks,
                    karakter: karakter  // ← KIRIM KARAKTER KE SERVER
                })
            });
            if (!response.ok) throw new Error('Gagal generate suara');
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            if (audioPlayer) {
                audioPlayer.pause();
                audioPlayer.src = '';
            }
            audioPlayer = new Audio(url);
            audioPlayer.play();
            audioPlayer.onended = () => {
                URL.revokeObjectURL(url);
            };
        } catch (error) {
            console.warn('TTS error:', error);
        }
    }

    // ===== KIRIM PESAN DENGAN DUKUNGAN KARAKTER =====
    async function kirimPesan() {
        const teks = inputPesan.value.trim();
        if (!teks) return;
        if (teks.length > 200) {
            alert('Pesan maksimal 200 karakter!');
            return;
        }

        tambahPesanUser(teks);
        inputPesan.value = '';
        updateCharCount();

        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'pesan-shiro';
        loadingDiv.textContent = '💭 Shiro sedang mengetik...';
        loadingDiv.id = 'loading-indicator';
        riwayat.appendChild(loadingDiv);
        riwayat.scrollTop = riwayat.scrollHeight;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: teks, karakter: 'shiro' })
            });
            const data = await response.json();
            const loading = document.getElementById('loading-indicator');
            if (loading) loading.remove();

            if (data.reply) {
                tambahPesanShiro(data.reply);
                // Kirim karakter ke putarAudio (default 'shiro' jika tidak ada)
                putarAudio(data.reply, data.karakter || 'shiro');
                if (data.status) {
                    updateStatusBar(data.status);
                }
            } else {
                tambahPesanShiro('Maaf, Shiro sedang bermasalah... 😢');
            }
        } catch (error) {
            const loading = document.getElementById('loading-indicator');
            if (loading) loading.remove();
            tambahPesanShiro('Koneksi ke Shiro terputus... 😭');
            console.error(error);
        }
    }

    // ===== UPLOAD GAMBAR =====
    tombolUpload.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            alert('Hanya file gambar yang diizinkan!');
            fileInput.value = '';
            return;
        }

        tambahPesanUser(`📷 Mengirim gambar: ${file.name}`);

        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'pesan-shiro';
        loadingDiv.textContent = '💭 Shiro sedang melihat gambarmu...';
        loadingDiv.id = 'loading-indicator';
        riwayat.appendChild(loadingDiv);
        riwayat.scrollTop = riwayat.scrollHeight;

        const formData = new FormData();
        formData.append('image', file);
        formData.append('caption', inputPesan.value.trim() || '');

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            const loading = document.getElementById('loading-indicator');
            if (loading) loading.remove();

            if (data.reply) {
                tambahPesanShiro(data.reply);
                putarAudio(data.reply, data.karakter || 'shiro');
                if (data.status) {
                    updateStatusBar(data.status);
                }
            } else {
                tambahPesanShiro('Shiro tidak bisa melihat gambar itu... 😢');
            }
        } catch (error) {
            const loading = document.getElementById('loading-indicator');
            if (loading) loading.remove();
            tambahPesanShiro('Gagal mengirim gambar... 😭');
            console.error(error);
        }

        fileInput.value = '';
        inputPesan.value = '';
        updateCharCount();
    });

    // ===== STATUS =====
    async function refreshStatus() {
        try {
            const res = await fetch('/status');
            const status = await res.json();
            updateStatusBar(status);
        } catch (e) { console.warn('Gagal refresh status'); }
    }

    function updateStatusBar(status) {
        const score = status.affection || 50;
        const level = status.level || 1;
        let moodEmoji, moodText;
        if (score < 20) { moodEmoji = '😠'; moodText = 'Posesif'; }
        else if (score >= 75) { moodEmoji = '😍'; moodText = 'Bucin'; }
        else if (score >= 50) { moodEmoji = '😊'; moodText = 'Bahagia'; }
        else { moodEmoji = '😐'; moodText = 'Biasa'; }

        const barLength = 20;
        const filled = Math.round((score / 100) * barLength);
        const bar = '█'.repeat(filled) + '░'.repeat(barLength - filled);
        statusText.textContent = `${moodEmoji} ${moodText} · Level ${level} · [${bar}] ${score}%`;
    }

    // ===== MIKROFON =====
    function mulaiDengar() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('Browser tidak mendukung fitur suara. Gunakan Chrome atau Edge.');
            return;
        }
        if (isListening) return;
        isListening = true;
        tombolMic.style.background = '#ff4444';
        tombolMic.innerHTML = '<i class="fas fa-stop"></i>';

        const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = 'id-ID';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.start();

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            inputPesan.value = transcript;
            updateCharCount();
            kirimPesan();
        };

        recognition.onerror = (event) => {
            console.warn('Mic error:', event.error);
            if (event.error === 'not-allowed') {
                alert('Izin mikrofon ditolak. Izinkan akses mikrofon di pengaturan browser.');
            }
            hentikanDengar();
        };

        recognition.onend = () => {
            hentikanDengar();
        };

        window._recognition = recognition;
    }

    function hentikanDengar() {
        if (window._recognition) {
            try { window._recognition.stop(); } catch (e) {}
            delete window._recognition;
        }
        isListening = false;
        tombolMic.style.background = '';
        tombolMic.innerHTML = '<i class="fas fa-microphone"></i>';
    }

    // ===== EVENT LISTENER =====
    maskot.addEventListener('click', tampilkanObrolan);
    btnTutup.addEventListener('click', sembunyikanObrolan);
    tombolKirim.addEventListener('click', kirimPesan);
    inputPesan.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); kirimPesan(); } });
    inputPesan.addEventListener('input', updateCharCount);

    tombolMic.addEventListener('click', () => {
        if (isListening) {
            hentikanDengar();
        } else {
            mulaiDengar();
        }
    });

    // ===== INISIALISASI =====
    updateCharCount();
    refreshStatus();
    setInterval(refreshStatus, 10000);

    if (riwayat.children.length === 0) {
        const welcome = document.createElement('div');
        welcome.className = 'pesan-shiro';
        welcome.textContent = 'Halo Kakak Shin! Ketuk aku untuk ngobrol ya~ 🐱';
        riwayat.appendChild(welcome);
    }
});