// ==========================================
// SHIRO AI - MAIN APPLICATION (FINAL)
// ==========================================

// ==========================================
// GLOBAL VARIABLES
// ==========================================
var currentCharacter = 'shiro';
var chatHistory = { shiro: [], sishin: [] };
var bgmIndex = 0;
// ===== SESUAIKAN DENGAN FILE MP3 ANDA (MAKS 9) =====
var bgmList = [
    'bgm_1.mp3', 'bgm_2.mp3', 'bgm_3.mp3', 'bgm_4.mp3', 'bgm_5.mp3',
    'bgm_6.mp3', 'bgm_7.mp3', 'bgm_8.mp3', 'bgm_9.mp3'
];
var bgmNames = [
    'Lagu Santai', 'Lagu Ceria', 'Lagu Romantis', 'Lagu Semangat', 'Lagu Malam',
    'Lagu Sedih', 'Lagu Bahagia', 'Lagu Tenang', 'Lagu Cinta'
];
var mediaRecorder = null;
var audioChunks = [];
var isRecording = false;
var audioPlayer = null;

// ==========================================
// DOM REFS (dengan fallback)
// ==========================================
const kotakObrolan = document.getElementById('kotak-obrolan');
const maskot = document.getElementById('shiro-mascot');
const btnTutup = document.getElementById('tombol-tutup');
const inputPesan = document.getElementById('userInput');
const tombolKirim = document.getElementById('sendBtn');
const tombolMic = document.getElementById('tombol-mic');
const tombolUpload = document.querySelector('.btn-upload') || document.getElementById('tombol-upload');
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
// TIME & GREETING
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
    if (!kotakObrolan) return;
    kotakObrolan.classList.remove('sembunyi');
    if (bubbleIntro) bubbleIntro.style.display = 'none';
    setTimeout(() => { if (inputPesan) inputPesan.focus(); }, 300);
}

function sembunyikanObrolan() {
    if (!kotakObrolan) return;
    kotakObrolan.classList.add('sembunyi');
    setTimeout(() => { if (bubbleIntro) bubbleIntro.style.display = 'block'; }, 500);
}

function tambahPesanUser(teks) {
    if (!riwayat) return;
    const div = document.createElement('div');
    div.className = 'pesan-user';
    div.textContent = teks;
    riwayat.appendChild(div);
    riwayat.scrollTop = riwayat.scrollHeight;
}

function tambahPesanShiro(teks) {
    if (!riwayat) return;
    const div = document.createElement('div');
    div.className = 'pesan-shiro';
    div.textContent = teks;
    riwayat.appendChild(div);
    riwayat.scrollTop = riwayat.scrollHeight;
}

function updateCharCount() {
    if (!charCount || !inputPesan) return;
    const panjang = inputPesan.value.length;
    charCount.textContent = panjang;
    charCount.style.color = panjang > 180 ? '#ff6b8a' : '#a07a7a';
}

// ==========================================
// ADD MESSAGE (CHAT BOX)
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
// BLINK AVATAR (OPSI 1 - TAMBAHAN)
// ==========================================
function blinkAvatar() {
    const overlay = document.getElementById('blinkOverlay');
    if (!overlay) return;
    overlay.classList.add('active');
    setTimeout(function() {
        overlay.classList.remove('active');
    }, 150);
}

// ==========================================
// TYPING INDICATOR (TAMBAHAN POLISH)
// ==========================================
function showTypingIndicator() {
    var chatBox = document.getElementById('chatBox');
    if (!chatBox) return;
    var old = document.getElementById('typingIndicator');
    if (old) old.remove();
    var indicator = document.createElement('div');
    indicator.className = 'msg msg-shiro typing-indicator';
    indicator.id = 'typingIndicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    chatBox.appendChild(indicator);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function hideTypingIndicator() {
    var indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

// ==========================================
// PUTAR AUDIO (TTS) - DIPERBAIKI DENGAN ANIMASI BICARA
// ==========================================
async function putarAudio(teks, karakter) {
    if (!teks) return;

    const avatar = document.getElementById('homeAvatar');
    // Aktifkan animasi bicara
    if (avatar) {
        avatar.classList.remove('idle');
        avatar.classList.add('speaking');
    }

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

        audioPlayer.onended = function() {
            URL.revokeObjectURL(url);
            // Kembali ke idle setelah bicara selesai
            if (avatar) {
                avatar.classList.remove('speaking');
                avatar.classList.add('idle');
            }
        };

        // Fallback: jika audio gagal, kembali ke idle setelah 5 detik
        setTimeout(function() {
            if (avatar) {
                avatar.classList.remove('speaking');
                avatar.classList.add('idle');
            }
        }, 5000);

    } catch (error) {
        console.warn('TTS error:', error);
        if (avatar) {
            avatar.classList.remove('speaking');
            avatar.classList.add('idle');
        }
    }
}

// ==========================================
// SWITCH CHARACTER (DIPERBAIKI - MEMPERTAHANKAN IDLE)
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
        if (avatar) {
            avatar.src = '/static/images/shiro.png';
            avatar.classList.remove('shiro-mode', 'sishin-mode');
            avatar.classList.add('shiro-mode');
            // Jika tidak sedang bicara, tambahkan idle
            if (!avatar.classList.contains('speaking')) {
                avatar.classList.add('idle');
            }
        }
        if (name) name.textContent = 'Shiro';
        if (subtitle) subtitle.textContent = 'Onee-san yang manja';
        if (btnShiro) btnShiro.classList.add('active');
        if (btnSishin) btnSishin.classList.remove('active');
        if (ring) ring.className = 'avatar-ring shiro-ring';
        if (glow) glow.className = 'avatar-glow shiro-glow';
        if (status) status.textContent = 'Afeksi 50%';
        var cameraTitle = document.getElementById('cameraTitle');
        if (cameraTitle) cameraTitle.textContent = 'Kirim Foto untuk Shiro';
        var voiceTitle = document.getElementById('voiceTitle');
        if (voiceTitle) voiceTitle.textContent = 'Rekam Suara untuk Shiro';
        var sawerTitle = document.getElementById('sawerTitle');
        if (sawerTitle) sawerTitle.textContent = 'Sawer Shiro';
        var sawerDesc = document.getElementById('sawerDesc');
        if (sawerDesc) sawerDesc.textContent = 'Dukung Shiro dengan saweran virtual.';
    } else {
        if (avatar) {
            avatar.src = '/static/images/sishin.png';
            avatar.classList.remove('shiro-mode', 'sishin-mode');
            avatar.classList.add('sishin-mode');
            if (!avatar.classList.contains('speaking')) {
                avatar.classList.add('idle');
            }
        }
        if (name) name.textContent = 'Sishin';
        if (subtitle) subtitle.textContent = 'Adik kecil yang imut';
        if (btnSishin) btnSishin.classList.add('active');
        if (btnShiro) btnShiro.classList.remove('active');
        if (ring) ring.className = 'avatar-ring sishin-ring';
        if (glow) glow.className = 'avatar-glow sishin-glow';
        if (status) status.textContent = 'Afeksi 50%';
        var cameraTitle = document.getElementById('cameraTitle');
        if (cameraTitle) cameraTitle.textContent = 'Kirim Foto untuk Sishin';
        var voiceTitle = document.getElementById('voiceTitle');
        if (voiceTitle) voiceTitle.textContent = 'Rekam Suara untuk Sishin';
        var sawerTitle = document.getElementById('sawerTitle');
        if (sawerTitle) sawerTitle.textContent = 'Sawer Sishin';
        var sawerDesc = document.getElementById('sawerDesc');
        if (sawerDesc) sawerDesc.textContent = 'Dukung Sishin dengan saweran virtual.';
    }

    currentCharacter = char;
    var chatName = document.getElementById('chatCharName');
    if (chatName) chatName.textContent = char === 'shiro' ? 'Shiro' : 'Sishin';
    console.log('Switched to:', char);

    var chatScreen = document.getElementById('chatScreen');
    if (chatScreen && chatScreen.style.display !== 'none') {
        loadChatHistory(char);
    }

    // Fallback: pastikan idle tetap ada setelah switch
    setTimeout(function() {
        if (avatar && !avatar.classList.contains('speaking')) {
            avatar.classList.add('idle');
        }
    }, 50);
}

// ==========================================
// SEND MESSAGE (FUNGSI UTAMA – GLOBAL)
// ==========================================
window.sendMessage = function() {
    console.log('🚀 sendMessage dipanggil!');

    var input = document.getElementById('userInput');
    if (!input) {
        console.warn('❌ userInput tidak ditemukan');
        return;
    }

    var message = input.value.trim();
    if (!message) {
        console.warn('⚠️ Pesan kosong');
        return;
    }

    var char = window.currentCharacter || 'shiro';
    console.log('📤 Mengirim pesan untuk karakter:', char);

    addMessage(message, 'user');
    showTypingIndicator();

    input.value = '';
    input.disabled = true;

    var button = document.getElementById('sendBtn');
    if (button) button.disabled = true;

    var avatar = document.getElementById('homeAvatar');
    var glow = document.getElementById('avatarGlow');
    if (avatar) avatar.classList.add('speaking');
    if (glow) glow.classList.add('active');

    fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message, karakter: char })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        var reply = data.reply || 'Maaf, aku sedang sibuk.';
        var detectedChar = data.karakter || char;
        addMessage(reply, detectedChar);
        putarAudio(reply, detectedChar);
        input.disabled = false;
        if (button) button.disabled = false;
        input.focus();
        if (avatar) avatar.classList.remove('speaking');
        if (glow) glow.classList.remove('active');
        hideTypingIndicator();
    })
    .catch(function(error) {
        console.error('❌ Send error:', error);
        addMessage('Maaf, ada masalah koneksi.', 'shiro');
        input.disabled = false;
        if (button) button.disabled = false;
        input.focus();
        if (avatar) avatar.classList.remove('speaking');
        if (glow) glow.classList.remove('active');
        hideTypingIndicator();
    });
};

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
    if (!statusText) return;
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
if (tombolUpload && fileInput) {
    tombolUpload.addEventListener('click', function() {
        fileInput.click();
    });
} else {
    console.warn('tombolUpload atau fileInput tidak ditemukan, abaikan upload gambar');
}

if (fileInput) {
    fileInput.addEventListener('change', async function(event) {
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
        if (riwayat) riwayat.appendChild(loadingDiv);
        if (riwayat) riwayat.scrollTop = riwayat.scrollHeight;

        const formData = new FormData();
        formData.append('image', file);
        formData.append('caption', inputPesan ? inputPesan.value.trim() || '' : '');
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

        if (fileInput) fileInput.value = '';
        if (inputPesan) { inputPesan.value = ''; updateCharCount(); }
    });
}

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
    if (tombolMic) {
        tombolMic.style.background = '#ff4444';
        tombolMic.innerHTML = '<i class="fas fa-stop"></i>';
    }

    const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'id-ID';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.start();

    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        if (inputPesan) { inputPesan.value = transcript; updateCharCount(); }
        sendMessage();
    };

    recognition.onerror = function(event) {
        console.warn('Mic error:', event.error);
        if (event.error === 'not-allowed') {
            alert('Izin mikrofon ditolak. Izinkan akses mikrofon di pengaturan browser.');
        }
        hentikanDengar();
    };

    recognition.onend = function() {
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
    if (tombolMic) {
        tombolMic.style.background = '';
        tombolMic.innerHTML = '<i class="fas fa-microphone"></i>';
    }
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

    setTimeout(function() {
        if (notif.parentNode) notif.remove();
    }, 10000);
}

// ==========================================
// NAVIGASI CHAT
// ==========================================
function openChat() {
    var homeScreen = document.getElementById('homeScreen');
    var chatScreen = document.getElementById('chatScreen');
    var fab = document.getElementById('fabChat');
    if (homeScreen) homeScreen.style.display = 'none';
    if (chatScreen) chatScreen.style.display = 'flex';
    if (fab) fab.style.display = 'none';

    loadChatHistory(currentCharacter);

    var userInput = document.getElementById('userInput');
    if (userInput) userInput.focus();
}

function closeChat() {
    var homeScreen = document.getElementById('homeScreen');
    var chatScreen = document.getElementById('chatScreen');
    var fab = document.getElementById('fabChat');
    if (homeScreen) homeScreen.style.display = 'flex';
    if (chatScreen) chatScreen.style.display = 'none';
    if (fab) fab.style.display = 'flex';
    refreshStatus();
}

// ==========================================
// EVENT LISTENERS (DIPASANG SETELAH DOM SIAP)
// ==========================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM siap, memasang event listener...');

    var sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.sendMessage();
        });
        console.log('✅ Event listener tombol kirim terpasang');
    } else {
        console.warn('❌ tombol kirim (sendBtn) tidak ditemukan di HTML');
    }

    var userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                window.sendMessage();
            }
        });
        console.log('✅ Event listener Enter terpasang');
    }

    var micBtn = document.getElementById('tombol-mic');
    if (micBtn) {
        micBtn.addEventListener('click', function() {
            if (isRecording) {
                hentikanDengar();
            } else {
                mulaiDengar();
            }
        });
    }

    var mascot = document.getElementById('shiro-mascot');
    if (mascot) {
        mascot.addEventListener('click', tampilkanObrolan);
    }

    var tutupBtn = document.getElementById('tombol-tutup');
    if (tutupBtn) {
        tutupBtn.addEventListener('click', sembunyikanObrolan);
    }

    var uploadBtn = document.querySelector('.btn-upload');
    if (uploadBtn && fileInput) {
        uploadBtn.addEventListener('click', function() { fileInput.click(); });
    }

    var avatar = document.getElementById('homeAvatar');
    if (avatar) {
        avatar.classList.add('idle');
    }

    setInterval(function() {
        blinkAvatar();
    }, 3000 + Math.random() * 2000);

    createRain();
    createGlint();
    createSakura();
    createLeaves();
    createSnow();

    var savedTheme = localStorage.getItem('shiro_theme');
    if (savedTheme) setTheme(savedTheme);
    else setTheme('night');

    refreshStatus();
    console.log('✅ Shiro AI initialized.');
});

// ==========================================
// CAMERA (Modal)
// ==========================================
function openCamera() {
    var modal = document.getElementById('cameraModal');
    if (modal) modal.classList.add('active');
    var title = document.getElementById('cameraTitle');
    if (title) title.textContent = currentCharacter === 'shiro' ? 'Kirim Foto untuk Shiro' : 'Kirim Foto untuk Sishin';
}

function closeCamera() {
    var modal = document.getElementById('cameraModal');
    if (modal) modal.classList.remove('active');
    var preview = document.getElementById('imagePreview');
    if (preview) preview.innerHTML = '';
    var upload = document.getElementById('imageUpload');
    if (upload) upload.value = '';
}

var imageUpload = document.getElementById('imageUpload');
if (imageUpload) {
    imageUpload.addEventListener('change', function(event) {
        var preview = document.getElementById('imagePreview');
        if (this.files && this.files[0]) {
            var reader = new FileReader();
            reader.onload = function(e) {
                if (preview) preview.innerHTML = '<img src="' + e.target.result + '" alt="Preview">';
            };
            reader.readAsDataURL(this.files[0]);
        }
    });
}

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
    var modal = document.getElementById('voiceModal');
    if (modal) modal.classList.add('active');
    var title = document.getElementById('voiceTitle');
    if (title) title.textContent = currentCharacter === 'shiro' ? 'Rekam Suara untuk Shiro' : 'Rekam Suara untuk Sishin';
}

function closeVoice() {
    var modal = document.getElementById('voiceModal');
    if (modal) modal.classList.remove('active');
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
            if (button) {
                button.innerHTML = '<i class="fas fa-stop"></i> Mendengarkan...';
                button.classList.add('recording');
            }
            if (text) text.textContent = 'Mendengarkan... bicara sekarang.';

            recognition.onresult = async function(event) {
                var transcript = event.results[0][0].transcript;
                if (text) text.textContent = 'Kamu bilang: "' + transcript + '"';
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
                    if (text) text.textContent = 'Gagal mengirim suara.';
                }
                isRecording = false;
                if (button) {
                    button.innerHTML = '<i class="fas fa-microphone"></i> Mulai Rekam';
                    button.classList.remove('recording');
                }
            };

            recognition.onerror = function(event) {
                console.error('Speech error:', event.error);
                if (event.error === 'not-allowed') {
                    alert('Akses mikrofon ditolak.');
                }
                isRecording = false;
                if (button) {
                    button.innerHTML = '<i class="fas fa-microphone"></i> Mulai Rekam';
                    button.classList.remove('recording');
                }
                if (text) text.textContent = 'Tekan tombol untuk mulai bicara.';
            };

            recognition.onend = function() {
                if (isRecording) {
                    isRecording = false;
                    if (button) {
                        button.innerHTML = '<i class="fas fa-microphone"></i> Mulai Rekam';
                        button.classList.remove('recording');
                    }
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
        if (button) {
            button.innerHTML = '<i class="fas fa-microphone"></i> Mulai Rekam';
            button.classList.remove('recording');
        }
        if (text) text.textContent = 'Tekan tombol untuk mulai bicara.';
    }
}

// ==========================================
// SAWER
// ==========================================
function openSawer() {
    var modal = document.getElementById('sawerModal');
    if (modal) modal.classList.add('active');
    var title = document.getElementById('sawerTitle');
    if (title) title.textContent = currentCharacter === 'shiro' ? 'Sawer Shiro' : 'Sawer Sishin';
    var desc = document.getElementById('sawerDesc');
    if (desc) desc.textContent = currentCharacter === 'shiro' ? 'Dukung Shiro dengan saweran virtual.' : 'Dukung Sishin dengan saweran virtual.';
}

function closeSawer() {
    var modal = document.getElementById('sawerModal');
    if (modal) modal.classList.remove('active');
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
    if (messageEl) {
        messageEl.textContent = randomResponse + ' (+' + amount + ' poin afeksi untuk ' + charName + ')';
        messageEl.style.color = '#ff8a9b';
    }

    fetch('/sawer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: amount, karakter: currentCharacter })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.affection) {
            var affDisplay = document.getElementById('affectionDisplay');
            if (affDisplay) affDisplay.textContent = data.affection;
        }
        if (data.reply) addMessage(data.reply, currentCharacter);
    })
    .catch(function(error) {
        console.error('Sawer error:', error);
    });

    setTimeout(function() {
        if (messageEl) messageEl.textContent = '';
    }, 5000);
}

function sawerCustom() {
    var input = document.getElementById('sawerCustom');
    if (!input) return;
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

    for (var key in effects) {
        if (effects[key]) effects[key].classList.remove('active');
    }

    switch (theme) {
        case 'morning': if (effects.sunRay) effects.sunRay.classList.add('active'); break;
        case 'afternoon': if (effects.glint) effects.glint.classList.add('active'); break;
        case 'evening': if (effects.sunsetGlow) effects.sunsetGlow.classList.add('active'); break;
        case 'spring': if (effects.sakura) { effects.sakura.classList.add('active'); createSakura(); } break;
        case 'summer': if (effects.heatHaze) effects.heatHaze.classList.add('active'); break;
        case 'autumn': if (effects.leaf) { effects.leaf.classList.add('active'); createLeaves(); } break;
        case 'winter': if (effects.snow) { effects.snow.classList.add('active'); createSnow(); } break;
        case 'rain': if (effects.rain) { effects.rain.classList.add('active'); createRain(); } break;
        default: break;
    }
}

// ==========================================
// BGM FUNCTIONS (TANPA DUPLIKAT - PLAYLIST DINAMIS)
// ==========================================
function togglePlaylist() {
    var menu = document.getElementById('playlistMenu');
    if (!menu) return;
    menu.classList.toggle('active');

    if (menu.classList.contains('active')) {
        var container = menu.querySelector('.playlist-items');
        if (!container) {
            container = document.createElement('div');
            container.className = 'playlist-items';
            menu.appendChild(container);
        }
        // KOSONGKAN DAHULU AGAR TIDAK DUPLIKAT
        container.innerHTML = '';
        for (var i = 0; i < bgmList.length; i++) {
            var item = document.createElement('div');
            item.className = 'playlist-item';
            if (i === bgmIndex) item.classList.add('active');
            item.innerHTML = '<span class="play-icon"><i class="fas fa-play"></i></span><span class="play-name">' + bgmNames[i] + '</span>';
            item.onclick = (function(index) {
                return function() {
                    playMusic(index);
                    menu.classList.remove('active');
                };
            })(i);
            container.appendChild(item);
        }
    }
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
            // Tutup playlist setelah memilih
            var menu = document.getElementById('playlistMenu');
            if (menu) menu.classList.remove('active');
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
// THEME EFFECTS
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
// INITIALIZATION (FALLBACK)
// ==========================================
console.log('Shiro AI initialized.');
console.log('Fitur konteks antar karakter diaktifkan (30% kemungkinan).');