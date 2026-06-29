// ==========================================
// SHIRO AI - MAIN APPLICATION
// ==========================================

// ==========================================
// GLOBAL VARIABLES
// ==========================================
var currentCharacter = 'shiro';
var chatHistory = { shiro: [], sishin: [] };
var bgmIndex = 0;
var bgmList = ['bgm_1.mp3', 'bgm_2.mp3', 'bgm_3.mp3', 'bgm_4.mp3', 'bgm_5.mp3'];
var bgmNames = ['Lagu Santai', 'Lagu Ceria', 'Lagu Romantis', 'Lagu Semangat', 'Lagu Malam'];
var mediaRecorder = null;
var audioChunks = [];
var isRecording = false;
var audioPlayer = null;

// ==========================================
// DOM REFS
// ==========================================
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

// ==========================================
// FULLSCREEN
// ==========================================
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen();
    } else if (document.exitFullscreen) {
        document.exitFullscreen();
    }
}

// ==========================================
// TIME
// ==========================================
function updateTime() {
    var now = new Date();
    var hours = String(now.getHours()).padStart(2, '0');
    var minutes = String(now.getMinutes()).padStart(2, '0');
    document.getElementById('timeDisplay').textContent = hours + ':' + minutes;
}
updateTime();
setInterval(updateTime, 10000);

function updateGreeting() {
    var hour = new Date().getHours();
    var greet = 'Selamat Malam';
    if (hour < 5) greet = 'Selamat Malam';
    else if (hour < 11) greet = 'Selamat Pagi';
    else if (hour < 18) greet = 'Selamat Sore';
    document.getElementById('greetingText').textContent = greet;
}
updateGreeting();

// ==========================================
// BATTERY
// ==========================================
var battery = 85;
setInterval(function() {
    battery = Math.max(10, battery - 0.2);
    document.getElementById('batteryDisplay').textContent = Math.round(battery);
}, 30000);

// ==========================================
// CHAT UI FUNCTIONS
// ==========================================
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

// ==========================================
// ADD MESSAGE (dengan dukungan karakter)
// ==========================================
function addMessage(text, sender) {
    var chatBox = document.getElementById('chatBox');
    if (!chatBox) return;

    var messageDiv = document.createElement('div');
    messageDiv.className = 'msg';

    if (sender === 'user') {
        messageDiv.classList.add('msg-user');
    } else if (sender === 'shiro') {
        messageDiv.classList.add('msg-shiro');
    } else if (sender === 'sishin') {
        messageDiv.classList.add('msg-sishin');
    }

    var bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.textContent = text;
    messageDiv.appendChild(bubble);
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// ===== OVERRIDE addMessage untuk menyimpan riwayat =====
var originalAddMessage = addMessage;
addMessage = function(text, sender) {
    originalAddMessage(text, sender);
    if (sender === 'shiro' || sender === 'sishin') {
        chatHistory[sender].push({ text: text, sender: sender });
    } else if (sender === 'user') {
        var char = currentCharacter || 'shiro';
        chatHistory[char].push({ text: text, sender: 'user' });
    }
};

// ==========================================
// PUTAR AUDIO (TTS)
// ==========================================
async function putarAudio(teks, karakter) {
    if (!teks) return;
    try {
        const response = await fetch('/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                text: teks,
                karakter: karakter || currentCharacter || 'shiro'
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

// ==========================================
// SWITCH CHARACTER
// ==========================================
function switchCharacter(char) {
    if (char === currentCharacter) return;

    var avatar = document.getElementById('homeAvatar');
    var name = document.getElementById('homeCharName');
    var subtitle = document.getElementById('homeCharSub');
    var status = document.getElementById('chatCharStatus');
    var btnShiro = document.getElementById('btnShiro');
    var btnSishin = document.getElementById('btnSishin');
    var ring = document.getElementById('avatarRing');
    var glow = document.getElementById('avatarGlow');

    if (char === 'shiro') {
        avatar.src = '/static/images/shiro.png';
        avatar.className = 'avatar shiro-mode';
        name.textContent = 'Shiro';
        subtitle.textContent = 'Onee-san yang manja';
        btnShiro.classList.add('active');
        btnSishin.classList.remove('active');
        ring.className = 'avatar-ring shiro-ring';
        glow.className = 'avatar-glow shiro-glow';
        status.textContent = 'Afeksi 50%';
        document.getElementById('cameraTitle').textContent = 'Kirim Foto untuk Shiro';
        document.getElementById('voiceTitle').textContent = 'Rekam Suara untuk Shiro';
        document.getElementById('sawerTitle').textContent = 'Sawer Shiro';
        document.getElementById('sawerDesc').textContent = 'Dukung Shiro dengan saweran virtual.';
    } else {
        avatar.src = '/static/images/sishin.png';
        avatar.className = 'avatar sishin-mode';
        name.textContent = 'Sishin';
        subtitle.textContent = 'Adik kecil yang imut';
        btnSishin.classList.add('active');
        btnShiro.classList.remove('active');
        ring.className = 'avatar-ring sishin-ring';
        glow.className = 'avatar-glow sishin-glow';
        status.textContent = 'Afeksi 50%';
        document.getElementById('cameraTitle').textContent = 'Kirim Foto untuk Sishin';
        document.getElementById('voiceTitle').textContent = 'Rekam Suara untuk Sishin';
        document.getElementById('sawerTitle').textContent = 'Sawer Sishin';
        document.getElementById('sawerDesc').textContent = 'Dukung Sishin dengan saweran virtual.';
    }

    currentCharacter = char;
    var chatName = document.getElementById('chatCharName');
    if (chatName) chatName.textContent = char === 'shiro' ? 'Shiro' : 'Sishin';
    console.log('Switched to:', char);

    // Jika chatScreen terbuka, refresh riwayat
    var chatScreen = document.getElementById('chatScreen');
    if (chatScreen && chatScreen.style.display !== 'none') {
        loadChatHistory(char);
    }
}

// ==========================================
// LOAD CHAT HISTORY
// ==========================================
function loadChatHistory(char) {
    var chatBox = document.getElementById('chatBox');
    if (!chatBox) return;

    chatBox.innerHTML = '';

    var history = chatHistory[char] || [];
    if (history.length === 0) {
        var greeting = (char === 'shiro')
            ? 'Halo Sayang! Yuk ngobrol~'
            : 'Kak! Sishin siap main bareng!';
        chatHistory[char].push({ text: greeting, sender: char });
        originalAddMessage(greeting, char);
    } else {
        history.forEach(function(msg) {
            originalAddMessage(msg.text, msg.sender);
        });
    }

    var chatName = document.getElementById('chatCharName');
    if (chatName) {
        chatName.textContent = char === 'shiro' ? 'Shiro' : 'Sishin';
    }
}

// ==========================================
// SEND MESSAGE (dengan konteks silang)
// ==========================================
(function() {
    function getLastMessagesFromCharacter(char, count) {
        var history = chatHistory[char] || [];
        var messages = history.filter(function(msg) {
            return msg.sender === char;
        });
        return messages.slice(-count);
    }

    function buildContext(char) {
        var otherChar = (char === 'shiro') ? 'sishin' : 'shiro';
        var lastMessages = getLastMessagesFromCharacter(otherChar, 2);
        if (lastMessages.length === 0) return null;

        var name = otherChar === 'shiro' ? 'Shiro' : 'Sishin';
        var messagesStr = lastMessages.map(function(msg) {
            return '"' + msg.text + '"';
        }).join(', ');
        return 'Oh iya, sebelumnya ' + name + ' pernah bilang: ' + messagesStr + '.';
    }

    window.sendMessage = function() {
        var input = document.getElementById('userInput');
        if (!input) return;
        var message = input.value.trim();
        if (!message) return;

        var char = window.currentCharacter || 'shiro';
        console.log('Mengirim pesan untuk karakter:', char);

        var shouldAddContext = (Math.random() < 0.3);
        var modifiedMessage = message;

        if (shouldAddContext) {
            var context = buildContext(char);
            if (context) {
                modifiedMessage = message + ' ' + context;
                console.log('Menambahkan konteks:', context);
            }
        }

        chatHistory[char].push({ text: message, sender: 'user' });
        originalAddMessage(message, 'user');

        input.value = '';
        var button = document.getElementById('sendBtn');
        if (button) button.disabled = true;
        input.disabled = true;

        var avatar = document.getElementById('homeAvatar');
        var glow = document.getElementById('avatarGlow');
        if (avatar) avatar.classList.add('speaking');
        if (glow) glow.classList.add('active');

        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: modifiedMessage, karakter: char })
        })
        .then(function(response) { return response.json(); })
        .then(function(data) {
            var reply = data.reply || 'Maaf, aku sedang sibuk.';
            var detectedChar = data.karakter || char;

            chatHistory[detectedChar].push({ text: reply, sender: detectedChar });
            originalAddMessage(reply, detectedChar);

            return fetch('/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: data.suara || reply, karakter: detectedChar })
            })
            .then(function(ttsResponse) {
                if (!ttsResponse.ok) return null;
                return ttsResponse.blob();
            })
            .catch(function() { return null; });
        })
        .then(function(blob) {
            if (blob && blob.size > 0) {
                var audioUrl = URL.createObjectURL(blob);
                var audio = new Audio(audioUrl);
                audio.play().catch(function(e) { console.warn('Audio play error:', e); });
                audio.onended = function() {
                    var av = document.getElementById('homeAvatar');
                    var gl = document.getElementById('avatarGlow');
                    if (av) av.classList.remove('speaking');
                    if (gl) gl.classList.remove('active');
                    URL.revokeObjectURL(audioUrl);
                };
                setTimeout(function() {
                    var av = document.getElementById('homeAvatar');
                    var gl = document.getElementById('avatarGlow');
                    if (av) av.classList.remove('speaking');
                    if (gl) gl.classList.remove('active');
                }, 5000);
            } else {
                var av = document.getElementById('homeAvatar');
                var gl = document.getElementById('avatarGlow');
                if (av) av.classList.remove('speaking');
                if (gl) gl.classList.remove('active');
            }
        })
        .catch(function(error) {
            console.error('Send message error:', error);
            originalAddMessage('Maaf, ada masalah koneksi.', 'shiro');
            var av = document.getElementById('homeAvatar');
            var gl = document.getElementById('avatarGlow');
            if (av) av.classList.remove('speaking');
            if (gl) gl.classList.remove('active');
        })
        .finally(function() {
            input.disabled = false;
            if (button) button.disabled = false;
            input.focus();
        });
    };

    console.log('Fitur konteks antar karakter diaktifkan (30% kemungkinan).');
})();

// ==========================================
// STATUS UPDATE
// ==========================================
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
refreshStatus();
setInterval(refreshStatus, 10000);

// ==========================================
// UPLOAD GAMBAR
// ==========================================
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
    formData.append('karakter', currentCharacter || 'shiro');

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
            putarAudio(data.reply, data.karakter || currentCharacter || 'shiro');
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

// ==========================================
// MIKROFON
// ==========================================
function mulaiDengar() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert('Browser tidak mendukung fitur suara. Gunakan Chrome atau Edge.');
        return;
    }
    if (isRecording) return;
    isRecording = true;
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
        sendMessage();
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
    isRecording = false;
    tombolMic.style.background = '';
    tombolMic.innerHTML = '<i class="fas fa-microphone"></i>';
}

// ==========================================
// NOTIFIKASI POP-UP
// ==========================================
function showNotification(karakter, pesan) {
    const notif = document.createElement('div');
    notif.style.cssText = `
        position: fixed;
        bottom: 100px;
        right: 20px;
        background: rgba(30, 20, 50, 0.92);
        backdrop-filter: blur(10px);
        color: white;
        padding: 16px 22px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        max-width: 300px;
        z-index: 9999;
        animation: slideIn 0.5s ease;
        cursor: pointer;
        box-shadow: 0 10px 40px rgba(0,0,0,0.4);
        font-family: 'Quicksand', sans-serif;
    `;
    const nama = karakter === 'shiro' ? '💕 Shiro' : '🌸 Sishin';
    notif.innerHTML = `<strong>${nama}</strong><br>${pesan}`;
    notif.onclick = function() {
        this.remove();
        openChat();
    };
    document.body.appendChild(notif);
    
    setTimeout(() => {
        if (notif.parentNode) notif.remove();
    }, 10000);
}

// ==========================================
// NAVIGASI CHAT
// ==========================================
function openChat() {
    document.getElementById('homeScreen').style.display = 'none';
    document.getElementById('chatScreen').style.display = 'flex';
    var fab = document.getElementById('fabChat');
    if (fab) fab.style.display = 'none';
    loadChatHistory(currentCharacter);
    document.getElementById('userInput').focus();
}

function closeChat() {
    document.getElementById('homeScreen').style.display = 'flex';
    document.getElementById('chatScreen').style.display = 'none';
    var fab = document.getElementById('fabChat');
    if (fab) fab.style.display = 'flex';
    refreshStatus();
}

// ==========================================
// EVENT LISTENERS
// ==========================================
maskot.addEventListener('click', tampilkanObrolan);
btnTutup.addEventListener('click', sembunyikanObrolan);
tombolKirim.addEventListener('click', sendMessage);
inputPesan.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); sendMessage(); } });
inputPesan.addEventListener('input', updateCharCount);

tombolMic.addEventListener('click', () => {
    if (isRecording) {
        hentikanDengar();
    } else {
        mulaiDengar();
    }
});

document.getElementById('sendBtn')?.addEventListener('click', function(e) {
    e.preventDefault();
    sendMessage();
});
document.getElementById('userInput')?.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        sendMessage();
    }
});

// ==========================================
// POLLING: INISIATIF KARAKTER (30 detik)
// ==========================================
setInterval(async function() {
    try {
        const response = await fetch('/initiative');
        const data = await response.json();
        if (data && data.pesan) {
            console.log('💬 Inisiatif dari', data.karakter, ':', data.pesan);
            const chatScreen = document.getElementById('chatScreen');
            if (chatScreen && chatScreen.style.display !== 'none') {
                addMessage(data.pesan, data.karakter);
                putarAudio(data.pesan, data.karakter);
            } else {
                showNotification(data.karakter, data.pesan);
            }
        }
    } catch (e) {
        console.warn('Inisiatif polling error:', e);
    }
}, 30000);

// ==========================================
// POLLING: EVENT (60 detik)
// ==========================================
setInterval(async function() {
    try {
        const response = await fetch('/event');
        const data = await response.json();
        if (data && data.pesan) {
            console.log('🎉 Event dari', data.karakter, ':', data.pesan);
            const chatScreen = document.getElementById('chatScreen');
            if (chatScreen && chatScreen.style.display !== 'none') {
                addMessage(data.pesan, data.karakter);
                putarAudio(data.pesan, data.karakter);
            } else {
                showNotification(data.karakter, data.pesan);
            }
        }
    } catch (e) {
        console.warn('Event polling error:', e);
    }
}, 60000);

// ==========================================
// POLLING: MOOD / EKSPRESI (10 detik)
// ==========================================
setInterval(async function() {
    try {
        const response = await fetch(`/mood?karakter=${currentCharacter}`);
        const data = await response.json();
        if (data && data.mood) {
            const avatar = document.getElementById('homeAvatar');
            if (avatar) {
                const basePath = `/static/images/expressions/${data.karakter || currentCharacter}`;
                avatar.src = `${basePath}_${data.mood}.png`;
            }
        }
    } catch (e) {
        // fallback ke gambar default (abaikan error)
    }
}, 10000);

// ==========================================
// CAMERA (Modal)
// ==========================================
function openCamera() {
    document.getElementById('cameraModal').classList.add('active');
    var title = currentCharacter === 'shiro' ? 'Kirim Foto untuk Shiro' : 'Kirim Foto untuk Sishin';
    document.getElementById('cameraTitle').textContent = title;
}

function closeCamera() {
    document.getElementById('cameraModal').classList.remove('active');
    document.getElementById('imagePreview').innerHTML = '';
    document.getElementById('imageUpload').value = '';
}

document.getElementById('imageUpload')?.addEventListener('change', function(event) {
    var preview = document.getElementById('imagePreview');
    if (this.files && this.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            preview.innerHTML = '<img src="' + e.target.result + '" alt="Preview">';
        };
        reader.readAsDataURL(this.files[0]);
    }
});

async function uploadImage() {
    var fileInput = document.getElementById('imageUpload');
    if (!fileInput.files || !fileInput.files[0]) {
        alert('Silakan pilih gambar terlebih dahulu.');
        return;
    }

    var formData = new FormData();
    formData.append('image', fileInput.files[0]);
    formData.append('karakter', currentCharacter);

    try {
        var response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        var data = await response.json();
        closeCamera();
        if (data.reply) {
            openChat();
            addMessage(data.reply, data.karakter || currentCharacter);
            var ttsResponse = await fetch('/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: data.suara || data.reply,
                    karakter: data.karakter || currentCharacter
                })
            });
            if (ttsResponse.ok) {
                var blob = await ttsResponse.blob();
                var url = URL.createObjectURL(blob);
                var audio = new Audio(url);
                audio.play();
                audio.onended = function() { URL.revokeObjectURL(url); };
            }
        }
        alert('Foto berhasil dikirim!');
    } catch (error) {
        alert('Gagal mengirim foto.');
        console.error('Upload error:', error);
    }
}

// ==========================================
// VOICE (Modal)
// ==========================================
function startVoice() {
    document.getElementById('voiceModal').classList.add('active');
    var title = currentCharacter === 'shiro' ? 'Rekam Suara untuk Shiro' : 'Rekam Suara untuk Sishin';
    document.getElementById('voiceTitle').textContent = title;
}

function closeVoice() {
    document.getElementById('voiceModal').classList.remove('active');
    if (isRecording) toggleRecording();
}

async function toggleRecording() {
    var button = document.getElementById('recordBtn');
    var text = document.getElementById('voiceText');

    if (!isRecording) {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('Browser tidak mendukung fitur suara. Gunakan Chrome atau Edge.');
            return;
        }
        try {
            var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.lang = 'id-ID';
            recognition.continuous = false;
            recognition.interimResults = false;
            isRecording = true;
            button.innerHTML = '<i class="fas fa-stop"></i> Mendengarkan...';
            button.classList.add('recording');
            text.textContent = 'Mendengarkan... bicara sekarang.';

            recognition.onresult = async function(event) {
                var transcript = event.results[0][0].transcript;
                text.textContent = 'Kamu bilang: "' + transcript + '"';
                try {
                    var response = await fetch('/voice', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text: transcript, karakter: currentCharacter })
                    });
                    var data = await response.json();
                    if (data.reply) {
                        openChat();
                        addMessage(transcript, 'user');
                        addMessage(data.reply, data.karakter || currentCharacter);
                        var ttsResponse = await fetch('/tts', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                text: data.suara || data.reply,
                                karakter: data.karakter || currentCharacter
                            })
                        });
                        if (ttsResponse.ok) {
                            var blob = await ttsResponse.blob();
                            var url = URL.createObjectURL(blob);
                            var audio = new Audio(url);
                            audio.play();
                            audio.onended = function() { URL.revokeObjectURL(url); };
                        }
                    }
                } catch (error) {
                    console.error('Voice chat error:', error);
                    text.textContent = 'Gagal mengirim suara.';
                }
                isRecording = false;
                button.innerHTML = '<i class="fas fa-microphone"></i> Mulai Rekam';
                button.classList.remove('recording');
            };

            recognition.onerror = function(event) {
                console.error('Speech error:', event.error);
                if (event.error === 'not-allowed') {
                    alert('Akses mikrofon ditolak.');
                }
                isRecording = false;
                button.innerHTML = '<i class="fas fa-microphone"></i> Mulai Rekam';
                button.classList.remove('recording');
                text.textContent = 'Tekan tombol untuk mulai bicara.';
            };

            recognition.onend = function() {
                if (isRecording) {
                    isRecording = false;
                    button.innerHTML = '<i class="fas fa-microphone"></i> Mulai Rekam';
                    button.classList.remove('recording');
                }
            };

            window._recognition = recognition;
            recognition.start();
        } catch (error) {
            alert('Gagal memulai rekaman suara.');
            console.error('Microphone error:', error);
        }
    } else {
        if (window._recognition) {
            try { window._recognition.stop(); } catch (e) {}
            delete window._recognition;
        }
        isRecording = false;
        button.innerHTML = '<i class="fas fa-microphone"></i> Mulai Rekam';
        button.classList.remove('recording');
        text.textContent = 'Tekan tombol untuk mulai bicara.';
    }
}

// ==========================================
// SAWER
// ==========================================
function openSawer() {
    document.getElementById('sawerModal').classList.add('active');
    var title = currentCharacter === 'shiro' ? 'Sawer Shiro' : 'Sawer Sishin';
    var desc = currentCharacter === 'shiro' ? 'Dukung Shiro dengan saweran virtual.' : 'Dukung Sishin dengan saweran virtual.';
    document.getElementById('sawerTitle').textContent = title;
    document.getElementById('sawerDesc').textContent = desc;
}

function closeSawer() {
    document.getElementById('sawerModal').classList.remove('active');
}

function sawer(amount) {
    var messageEl = document.getElementById('sawerMessage');
    var charName = currentCharacter === 'shiro' ? 'Shiro' : 'Sishin';
    var responses = [
        'Terima kasih banyak, Sayang!',
        'Kamu baik banget! Aku senang!',
        'Untuk aku? Makasih! Aku sayang kamu.',
        'Ehehe~ Kamu perhatian banget.'
    ];
    var randomResponse = responses[Math.floor(Math.random() * responses.length)];
    messageEl.textContent = randomResponse + ' (+' + amount + ' poin afeksi untuk ' + charName + ')';
    messageEl.style.color = '#ff8a9b';

    fetch('/sawer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: amount, karakter: currentCharacter })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.affection) {
            document.getElementById('affectionDisplay').textContent = data.affection;
        }
        if (data.reply) addMessage(data.reply, currentCharacter);
    })
    .catch(function(error) {
        console.error('Sawer error:', error);
    });

    setTimeout(function() {
        messageEl.textContent = '';
    }, 5000);
}

function sawerCustom() {
    var input = document.getElementById('sawerCustom');
    var value = parseInt(input.value);
    if (!value || value < 100) {
        alert('Masukkan nominal minimal Rp 100.');
        return;
    }
    sawer(value);
    input.value = '';
}

// ==========================================
// THEME MENU
// ==========================================
function toggleThemeMenu() {
    var menu = document.getElementById('themeMenu');
    if (menu) menu.classList.toggle('active');
}

// ==========================================
// SET THEME (DIPERBAIKI UNTUK EFEK MUSIM)
// ==========================================
function setTheme(theme) {
    var bg = document.getElementById('bgLayer');
    if (!bg) return;
    bg.className = 'bg-layer ' + theme;
    localStorage.setItem('shiro_theme', theme);

    var menu = document.getElementById('themeMenu');
    if (menu) menu.classList.remove('active');

    var options = document.querySelectorAll('.theme-option');
    for (var i = 0; i < options.length; i++) {
        options[i].classList.remove('active');
    }

    var activeOption = document.querySelector('.theme-option[onclick="setTheme(\'' + theme + '\')"]');
    if (activeOption) activeOption.classList.add('active');

    var effects = {
        sunRay: document.getElementById('sunRay'),
        glint: document.getElementById('glintEffect'),
        sunsetGlow: document.getElementById('sunsetGlow'),
        sakura: document.getElementById('sakuraEffect'),
        leaf: document.getElementById('leafEffect'),
        snow: document.getElementById('snowEffect'),
        heatHaze: document.getElementById('heatHaze'),
        rain: document.getElementById('bgRain')
    };

    // Nonaktifkan semua efek
    for (var key in effects) {
        if (effects[key]) effects[key].classList.remove('active');
    }

    // Aktifkan efek sesuai tema dan reset animasi
    switch (theme) {
        case 'morning':
            if (effects.sunRay) effects.sunRay.classList.add('active');
            break;
        case 'afternoon':
            if (effects.glint) effects.glint.classList.add('active');
            break;
        case 'evening':
            if (effects.sunsetGlow) effects.sunsetGlow.classList.add('active');
            break;
        case 'spring':
            if (effects.sakura) {
                effects.sakura.classList.add('active');
                createSakura(); // Reset bunga sakura
            }
            break;
        case 'summer':
            if (effects.heatHaze) effects.heatHaze.classList.add('active');
            break;
        case 'autumn':
            if (effects.leaf) {
                effects.leaf.classList.add('active');
                createLeaves(); // Reset daun maple
            }
            break;
        case 'winter':
            if (effects.snow) {
                effects.snow.classList.add('active');
                createSnow(); // Reset salju
            }
            break;
        case 'rain':
            if (effects.rain) {
                effects.rain.classList.add('active');
                createRain(); // Reset hujan
            }
            break;
        default:
            break;
    }
}

// ==========================================
// BGM FUNCTIONS
// ==========================================
function togglePlaylist() {
    var menu = document.getElementById('playlistMenu');
    if (menu) menu.classList.toggle('active');
}

function playMusic(index) {
    bgmIndex = index;
    var audio = document.getElementById('bgmAudio');
    if (!audio) {
        var newAudio = document.createElement('audio');
        newAudio.id = 'bgmAudio';
        newAudio.loop = true;
        newAudio.volume = 0.15;
        document.body.appendChild(newAudio);
        audio = newAudio;
    }

    audio.src = '/static/music/' + bgmList[index];
    audio.load();
    audio.play()
        .then(function() {
            var btn = document.getElementById('bgmBtn');
            if (btn) {
                btn.classList.add('playing');
                btn.innerHTML = '<i class="fas fa-pause"></i>';
            }
            var items = document.querySelectorAll('.playlist-item');
            for (var i = 0; i < items.length; i++) {
                items[i].classList.remove('active');
            }
            if (items[index]) items[index].classList.add('active');
            togglePlaylist();
        })
        .catch(function() {
            console.warn('BGM file missing:', bgmList[index]);
            alert('File musik belum ada. Taruh ' + bgmList[index] + ' di folder static/music/');
        });
}

function toggleBGM() {
    var button = document.getElementById('bgmBtn');
    var audio = document.getElementById('bgmAudio');

    if (!audio) {
        playMusic(0);
        return;
    }

    if (audio.paused) {
        audio.play()
            .then(function() {
                button.classList.add('playing');
                button.innerHTML = '<i class="fas fa-pause"></i>';
            })
            .catch(function() {});
    } else {
        audio.pause();
        button.classList.remove('playing');
        button.innerHTML = '<i class="fas fa-play"></i>';
    }
}

// ==========================================
// MEMORY
// ==========================================
function showMemori() {
    fetch('/status')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            alert('Memori ' + (currentCharacter === 'shiro' ? 'Shiro' : 'Sishin') + '\n\n' +
                  'Afeksi: ' + data.affection + '%\n' +
                  'Level: ' + data.level + '\n' +
                  'Interaksi: ' + data.interaksi);
        })
        .catch(function() {
            alert('Memori: Belum ada percakapan.');
        });
}

// ==========================================
// THEME EFFECTS (Rain, Glint, Sakura, dll.)
// ==========================================
function createRain() {
    var container = document.getElementById('bgRain');
    if (!container) return;
    container.innerHTML = '';
    for (var i = 0; i < 50; i++) {
        var drop = document.createElement('div');
        drop.className = 'rain-drop';
        drop.style.cssText = 'left:' + Math.random() * 100 + '%;' +
            'animation-duration:' + (0.4 + Math.random() * 0.8) + 's;' +
            'animation-delay:' + (Math.random() * 2) + 's;' +
            'height:' + (10 + Math.random() * 20) + 'px;';
        container.appendChild(drop);
    }
}

function createGlint() {
    var container = document.getElementById('glintEffect');
    if (!container) return;
    container.innerHTML = '';
    for (var i = 0; i < 8; i++) {
        var glint = document.createElement('div');
        glint.className = 'glint';
        glint.style.cssText = 'left:' + Math.random() * 100 + '%;' +
            'top:' + Math.random() * 100 + '%;' +
            'animation-delay:' + (Math.random() * 3) + 's;';
        container.appendChild(glint);
    }
}

function createSakura() {
    var container = document.getElementById('sakuraEffect');
    if (!container) return;
    container.innerHTML = '';
    for (var i = 0; i < 25; i++) {
        var petal = document.createElement('div');
        petal.className = 'sakura-petal';
        petal.style.cssText = 'left:' + Math.random() * 100 + '%;' +
            'animation-duration:' + (5 + Math.random() * 6) + 's;' +
            'animation-delay:' + (Math.random() * 8) + 's;' +
            'width:' + (12 + Math.random() * 12) + 'px;' +
            'height:' + (12 + Math.random() * 12) + 'px;';
        container.appendChild(petal);
    }
}

function createLeaves() {
    var container = document.getElementById('leafEffect');
    if (!container) return;
    container.innerHTML = '';
    for (var i = 0; i < 20; i++) {
        var leaf = document.createElement('div');
        leaf.className = 'leaf-fall';
        leaf.style.cssText = 'left:' + Math.random() * 100 + '%;' +
            'animation-duration:' + (6 + Math.random() * 8) + 's;' +
            'animation-delay:' + (Math.random() * 6) + 's;' +
            'width:' + (12 + Math.random() * 14) + 'px;' +
            'height:' + (12 + Math.random() * 14) + 'px;';
        container.appendChild(leaf);
    }
}

function createSnow() {
    var container = document.getElementById('snowEffect');
    if (!container) return;
    container.innerHTML = '';
    for (var i = 0; i < 50; i++) {
        var snow = document.createElement('div');
        snow.className = 'snow-flake';
        snow.style.cssText = 'left:' + Math.random() * 100 + '%;' +
            'animation-duration:' + (3 + Math.random() * 5) + 's;' +
            'animation-delay:' + (Math.random() * 6) + 's;' +
            'width:' + (3 + Math.random() * 6) + 'px;' +
            'height:' + (3 + Math.random() * 6) + 'px;';
        container.appendChild(snow);
    }
}

// ==========================================
// CHARACTER INTERACTION
// ==========================================
document.getElementById('homeAvatar')?.addEventListener('click', function() {
    openChat();
});

// ==========================================
// EVENT LISTENERS
// ==========================================
// (sudah ada di atas)

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    createRain();
    createGlint();
    createSakura();
    createLeaves();
    createSnow();

    var savedTheme = localStorage.getItem('shiro_theme');
    if (savedTheme) {
        setTheme(savedTheme);
    } else {
        setTheme('night');
    }

    // Inisialisasi karakter dari tombol aktif
    var activeBtn = document.querySelector('.switch-btn.active');
    if (activeBtn) {
        var initChar = activeBtn.id === 'btnShiro' ? 'shiro' : 'sishin';
        if (initChar !== currentCharacter) {
            currentCharacter = initChar;
            console.log('🔁 Inisialisasi karakter dari tombol aktif:', currentCharacter);
        }
    }
    var chatName = document.getElementById('chatCharName');
    if (chatName) {
        chatName.textContent = currentCharacter === 'shiro' ? 'Shiro' : 'Sishin';
    }

    refreshStatus();
    console.log('Shiro AI initialized.');
    console.log('Chat terpisah + konteks silang 30% aktif.');
});

console.log('Shiro AI initialized.');
console.log('Fitur konteks antar karakter diaktifkan (30% kemungkinan).');