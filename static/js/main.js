// ==========================================
// SHIRO AI - MAIN APPLICATION (FINAL)
// ==========================================

// ==========================================
// GLOBAL VARIABLES
// ==========================================
// Character + affection state: static/js/core/character-state.js, affection-engine.js

var AVATAR_EXPRESSIONS = {
    shiro: {
        sad: '/static/images/expressions/shiro_sad.png',
        happy: '/static/images/expressions/shiro_happy.png',
        default: '/static/images/shiro.png'
    },
    sishin: {
        sad: '/static/images/expressions/sishin_sad.png',
        happy: '/static/images/expressions/sishin_normal.png',
        default: '/static/images/sishin.png'
    }
};

function getActiveCharacter() {
    if (window.CharacterState) return CharacterState.get();
    return window.currentCharacter || 'shiro';
}

function getActiveAffection() {
    if (window.AffectionEngine) return AffectionEngine.getScore();
    return typeof window.currentAffection === 'number' ? window.currentAffection : 50;
}

function getAvatarExpressionSrc(char, affection) {
    if (window.AssetManager) {
        var resolved = AssetManager.resolve({
            character: char,
            affection: affection,
            context: 'home'
        });
        return resolved.url;
    }
    char = window.CharacterState ? CharacterState.normalize(char) : (char === 'sishin' ? 'sishin' : 'shiro');
    var s = typeof affection === 'number' ? affection : getActiveAffection();
    var paths = AVATAR_EXPRESSIONS[char];
    var threshold = window.AffectionEngine ? AffectionEngine.SAD_THRESHOLD : 40;
    return s < threshold ? paths.sad : paths.happy;
}

function applyHomeAvatarExpression(char, affection) {
    var avatar = document.getElementById('homeAvatar');
    if (!avatar) return;

    char = window.CharacterState ? CharacterState.normalize(char) : (char === 'sishin' ? 'sishin' : 'shiro');
    var score = typeof affection === 'number' ? affection : getActiveAffection();
    var src, fallback, tier;

    if (window.AssetManager) {
        var resolved = AssetManager.resolve({
            character: char,
            affection: score,
            context: 'home'
        });
        src = resolved.url;
        fallback = resolved.fallback;
        tier = resolved.tier;
    } else {
        src = getAvatarExpressionSrc(char, score);
        fallback = AVATAR_EXPRESSIONS[char].default;
        var threshold = window.AffectionEngine ? AffectionEngine.SAD_THRESHOLD : 40;
        tier = score < threshold ? 'sad' : 'happy';
    }

    if (avatar.getAttribute('data-expression-src') === src) return;

    avatar.onerror = function() {
        avatar.onerror = null;
        avatar.src = fallback;
        avatar.setAttribute('data-expression-src', fallback);
    };
    avatar.src = src;
    avatar.setAttribute('data-expression-src', src);
    avatar.setAttribute('data-affection-tier', tier);
}

function setAffectionScore(score) {
    if (window.AffectionEngine) {
        AffectionEngine.setScore(score);
    }
}

function initSystemAwarenessWiring() {
    if (!window.AffectionEngine || !window.CharacterState) {
        console.warn('[SystemAwareness] Core modules not loaded — using legacy fallbacks');
        return;
    }

    AffectionEngine.onChange(function(evt) {
        var affDisplay = document.getElementById('affectionDisplay');
        if (affDisplay) affDisplay.textContent = evt.score;
        var chatStatus = document.getElementById('chatCharStatus');
        if (chatStatus) chatStatus.textContent = 'Afeksi ' + evt.score + '%';
        if (SystemAwareness.canApplyHomeExpression()) {
            applyHomeAvatarExpression(CharacterState.get(), evt.score);
        }
    });

    CharacterState.onChange(function(char) {
        if (SystemAwareness.canApplyHomeExpression()) {
            applyHomeAvatarExpression(char, AffectionEngine.getScore());
        }
        if (SystemAwareness.canApplyCallOverlay() && typeof updateWACallCharacter === 'function') {
            updateWACallCharacter(char);
        }
        if (typeof updateVtuberPttHint === 'function') updateVtuberPttHint();
    });

    applyHomeAvatarExpression(CharacterState.get(), AffectionEngine.getScore());
}

window.setAffectionScore = setAffectionScore;
window.applyHomeAvatarExpression = applyHomeAvatarExpression;
initSystemAwarenessWiring();
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
        document.documentElement.exitFullscreen();
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
        if (typeof startLive2DLipSync === 'function') startLive2DLipSync(audioPlayer);
        audioPlayer.play();

        audioPlayer.onended = function() {
            URL.revokeObjectURL(url);
            if (typeof stopLive2DLipSync === 'function') stopLive2DLipSync();
            // Kembali ke idle setelah bicara selesai
            if (avatar) {
                avatar.classList.remove('speaking');
                avatar.classList.add('idle');
            }
        };

        // Fallback: jika audio gagal, kembali ke idle setelah 5 detik
        setTimeout(function() {
            if (avatar && avatar.classList.contains('speaking')) {
                avatar.classList.remove('speaking');
                avatar.classList.add('idle');
            }
            if (typeof stopLive2DLipSync === 'function') stopLive2DLipSync();
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
    if (window.CharacterState) char = CharacterState.normalize(char);
    if (char === getActiveCharacter()) return;

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
            avatar.classList.remove('shiro-mode', 'sishin-mode');
            avatar.classList.add('shiro-mode');
            applyHomeAvatarExpression('shiro', getActiveAffection());
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
        if (status) status.textContent = 'Afeksi ' + getActiveAffection() + '%';
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
            avatar.classList.remove('shiro-mode', 'sishin-mode');
            avatar.classList.add('sishin-mode');
            applyHomeAvatarExpression('sishin', getActiveAffection());
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
        if (status) status.textContent = 'Afeksi ' + getActiveAffection() + '%';
        var cameraTitle = document.getElementById('cameraTitle');
        if (cameraTitle) cameraTitle.textContent = 'Kirim Foto untuk Sishin';
        var voiceTitle = document.getElementById('voiceTitle');
        if (voiceTitle) voiceTitle.textContent = 'Rekam Suara untuk Sishin';
        var sawerTitle = document.getElementById('sawerTitle');
        if (sawerTitle) sawerTitle.textContent = 'Sawer Sishin';
        var sawerDesc = document.getElementById('sawerDesc');
        if (sawerDesc) sawerDesc.textContent = 'Dukung Sishin dengan saweran virtual.';
    }

    if (window.CharacterState) {
        CharacterState.set(char);
    } else {
        window.currentCharacter = char;
    }
    var chatName = document.getElementById('chatCharName');
    if (chatName) chatName.textContent = char === 'shiro' ? 'Shiro' : 'Sishin';
    console.log('Switched to:', char);

    if (typeof vtuberMode !== 'undefined' && vtuberMode) {
        vtuberWaitingForServer = false;
        vtuberPttActive = false;
        if (vtuberRecognition) {
            try { vtuberRecognition.abort(); } catch (e) {}
            vtuberRecognition = null;
        }
        var vBtn = document.getElementById('btnVTuber');
        if (vBtn) {
            vBtn.classList.remove('recording');
            vBtn.style.background = '#ff6b8a';
            vBtn.style.color = '#fff';
            var vSpan = vBtn.querySelector('span');
            if (vSpan) vSpan.textContent = 'Berhenti';
        }
        updateVtuberPttHint();
        showPttHint(true);
        if (typeof updateWACallCharacter === 'function') updateWACallCharacter(char);
    }

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
    console.log('sendMessage dipanggil');

    var input = document.getElementById('userInput');
    if (!input) {
        console.warn('userInput tidak ditemukan');
        return;
    }

    var message = input.value.trim();
    if (!message) {
        console.warn('Pesan kosong');
        return;
    }

    var char = window.currentCharacter || 'shiro';
    console.log('Mengirim pesan untuk karakter:', char);

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
        if (data.status) updateStatusBar(data.status);
        putarAudio(reply, detectedChar);
        input.disabled = false;
        if (button) button.disabled = false;
        input.focus();
        if (avatar) avatar.classList.remove('speaking');
        if (glow) glow.classList.remove('active');
        hideTypingIndicator();
    })
    .catch(function(error) {
        console.error('Send error:', error);
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
    if (!status) return;
    setAffectionScore(status.affection);
    if (!statusText) return;
    const score = status.affection != null ? status.affection : getActiveAffection();
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
        loadingDiv.textContent = 'Shiro sedang melihat gambarmu...';
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
                tambahPesanShiro('Shiro tidak bisa melihat gambar itu...');
            }
        } catch (error) {
            const loading = document.getElementById('loading-indicator');
            if (loading) loading.remove();
            tambahPesanShiro('Gagal mengirim gambar...');
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
    const nama = karakter === 'shiro' ? 'Shiro' : 'Sishin';
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
    console.log('DOM siap, memasang event listener...');

    var sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.addEventListener('click', function(e) {
            e.preventDefault();
            window.sendMessage();
        });
        console.log('Event listener tombol kirim terpasang');
    } else {
        console.warn('tombol kirim (sendBtn) tidak ditemukan di HTML');
    }

    var userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                window.sendMessage();
            }
        });
        console.log('Event listener Enter terpasang');
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

    // ===== TAMBAHAN: CUACA DAN TEMA OTOMATIS =====
    var savedTheme = localStorage.getItem('shiro_theme');
    if (savedTheme) {
        setTheme(savedTheme);
    } else {
        updateThemeByTime();
    }
    fetchWeather();
    setInterval(fetchWeather, 600000); // refresh setiap 10 menit
    // ===== AKHIR TAMBAHAN =====

    refreshStatus();
    console.log('Shiro AI initialized.');
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
            if (data.status) updateStatusBar(data.status);
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
                        if (data.status) updateStatusBar(data.status);
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
            setAffectionScore(data.affection);
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

    if (typeof syncWACallTheme === 'function') syncWACallTheme(theme);
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

// ================================================================
// TAMBAHAN: FUNGSI CUACA DAN TEMA OTOMATIS
// ================================================================

/**
 * Mengambil data cuaca dari backend Flask (/api/weather) dan update tampilan.
 * Mencoba mendapatkan lokasi pengguna via Geolocation API, fallback ke Jakarta.
 */
async function fetchWeather() {
    try {
        let lat = '-6.2088';
        let lon = '106.8456';

        if (navigator.geolocation) {
            try {
                const position = await new Promise((resolve, reject) => {
                    navigator.geolocation.getCurrentPosition(resolve, reject, {
                        timeout: 5000,
                        enableHighAccuracy: false
                    });
                });
                lat = position.coords.latitude.toFixed(4);
                lon = position.coords.longitude.toFixed(4);
            } catch (geoError) {
                console.warn('Geolocation gagal, pakai default Jakarta:', geoError.message);
            }
        }

        const response = await fetch(`/api/weather?lat=${lat}&lon=${lon}`);
        if (!response.ok) throw new Error('HTTP ' + response.status);
        const data = await response.json();

        if (data.error) {
            console.warn('Weather API error:', data.error);
            updateWeatherUI(null);
            return;
        }

        updateWeatherUI(data);

    } catch (error) {
        console.error('Gagal mengambil cuaca:', error);
        updateWeatherUI(null);
    }
}

/**
 * Update elemen HTML yang menampilkan suhu, kondisi, dan ikon cuaca.
 * Jika data null, tampilkan pesan error.
 */
function updateWeatherUI(data) {
    const tempEl = document.getElementById('weather-temp');
    const descEl = document.getElementById('weather-desc');
    const iconEl = document.getElementById('weather-icon');

    if (!tempEl || !descEl) {
        return;
    }

    if (!data || !data.current_weather) {
        tempEl.textContent = '--°C';
        descEl.textContent = 'Tidak tersedia';
        if (iconEl) iconEl.className = 'wi wi-na';
        return;
    }

    const temp = data.current_weather.temperature;
    const weatherCode = data.current_weather.weathercode;

    let desc = 'Cerah';
    let icon = 'wi wi-day-sunny';

    if (weatherCode >= 0 && weatherCode <= 1) {
        desc = 'Cerah';
        icon = 'wi wi-day-sunny';
    } else if (weatherCode === 2) {
        desc = 'Berawan Sebagian';
        icon = 'wi wi-day-cloudy';
    } else if (weatherCode === 3) {
        desc = 'Berawan';
        icon = 'wi wi-cloud';
    } else if (weatherCode >= 45 && weatherCode <= 48) {
        desc = 'Kabut';
        icon = 'wi wi-fog';
    } else if (weatherCode >= 51 && weatherCode <= 55) {
        desc = 'Gerimis';
        icon = 'wi wi-sprinkle';
    } else if (weatherCode >= 61 && weatherCode <= 65) {
        desc = 'Hujan';
        icon = 'wi wi-rain';
    } else if (weatherCode >= 71 && weatherCode <= 75) {
        desc = 'Salju';
        icon = 'wi wi-snow';
    } else if (weatherCode >= 80 && weatherCode <= 82) {
        desc = 'Hujan Deras';
        icon = 'wi wi-showers';
    } else if (weatherCode >= 95 && weatherCode <= 99) {
        desc = 'Badai Petir';
        icon = 'wi wi-thunderstorm';
    } else {
        desc = 'Cuaca Lain';
        icon = 'wi wi-cloudy';
    }

    tempEl.textContent = Math.round(temp) + '°C';
    descEl.textContent = desc;
    if (iconEl) {
        iconEl.className = icon;
    }
}

/**
 * Menentukan tema berdasarkan waktu dan mengaktifkannya.
 * Hanya dipanggil jika tidak ada tema tersimpan di localStorage.
 */
function updateThemeByTime() {
    const hour = new Date().getHours();
    let theme = 'night';

    if (hour >= 5 && hour < 11) {
        theme = 'morning';
    } else if (hour >= 11 && hour < 16) {
        theme = 'afternoon';
    } else if (hour >= 16 && hour < 19) {
        theme = 'evening';
    } else {
        theme = 'night';
    }

    setTheme(theme);
    console.log('Tema otomatis berdasarkan waktu:', theme);
}

// ================================================================
// PERBAIKAN VTUBER MODE - BGM TIDAK TERGANGGU & SOCKET STABIL
// ================================================================

// Simpan referensi socket global
var socket = null;
var vtuberMode = false;
var vtuberRecognition = null;
var vtuberWaitingForServer = false;
var vtuberPttActive = false;
var vtuberPttBound = false;
var VTUBER_SPEECH_LANGS = ['id-ID', 'ja-JP'];

function updateVtuberPttHint() {
    var el = document.getElementById('vtuberPttHint');
    if (!el) return;
    var name = (currentCharacter === 'sishin') ? 'Sishin' : 'Shiro';
    el.innerHTML = 'VTuber <strong>' + name + '</strong> — tahan <kbd>Space</kbd> saat bicara (ID / JP)';
}

function showPttHint(visible) {
    var el = document.getElementById('vtuberPttHint');
    if (el) {
        if (visible && vtuberMode) updateVtuberPttHint();
        el.classList.toggle('visible', !!(visible && vtuberMode && !vtuberWaitingForServer && !document.body.classList.contains('wa-call-active')));
    }
    if (typeof updateWACallPttHint === 'function') {
        updateWACallPttHint(!!(visible && vtuberMode && !vtuberWaitingForServer));
    }
}

function bindVTuberPTT() {
    if (vtuberPttBound) return;
    vtuberPttBound = true;

    document.addEventListener('keydown', function(e) {
        if (!vtuberMode || vtuberWaitingForServer) return;
        if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
        if (e.code === 'Space' && !e.repeat) {
            e.preventDefault();
            beginVTuberPTT();
        }
    });

    document.addEventListener('keyup', function(e) {
        if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
        if (e.code === 'Space' && vtuberPttActive) {
            e.preventDefault();
            endVTuberPTT();
        }
    });

    var btn = document.getElementById('btnVTuber');
    if (btn) {
        btn.addEventListener('mousedown', function(e) {
            if (e.button !== 0 || !vtuberMode) return;
            beginVTuberPTT();
        });
        btn.addEventListener('mouseup', endVTuberPTT);
        btn.addEventListener('mouseleave', endVTuberPTT);
        btn.addEventListener('touchstart', function(e) {
            if (!vtuberMode) return;
            e.preventDefault();
            beginVTuberPTT();
        }, { passive: false });
        btn.addEventListener('touchend', endVTuberPTT);
    }
}

function beginVTuberPTT() {
    if (!vtuberMode || vtuberWaitingForServer || vtuberPttActive) return;
    if (window.waCallMicMuted) return;
    vtuberPttActive = true;
    showPttHint(false);
    startOneShotRecognition();
}

function endVTuberPTT() {
    if (!vtuberPttActive) return;
    vtuberPttActive = false;
    if (vtuberRecognition) {
        try { vtuberRecognition.stop(); } catch (e) {}
    }
    var btn = document.getElementById('btnVTuber');
    if (btn) btn.classList.remove('recording');
    var waMic = document.getElementById('waCallMicBtn');
    if (waMic) waMic.classList.remove('wa-ptt-active');
}

window.endVTuberPTT = endVTuberPTT;

function startOneShotRecognition(langTryIndex) {
    langTryIndex = langTryIndex || 0;
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    if (vtuberRecognition) {
        try { vtuberRecognition.abort(); } catch (e) {}
    }

    vtuberRecognition = new SpeechRecognition();
    vtuberRecognition.lang = VTUBER_SPEECH_LANGS[langTryIndex] || 'id-ID';
    vtuberRecognition.continuous = false;
    vtuberRecognition.interimResults = true;
    vtuberRecognition.maxAlternatives = 1;

    var btn = document.getElementById('btnVTuber');
    if (btn) btn.classList.add('recording');
    var waMic = document.getElementById('waCallMicBtn');
    if (waMic) waMic.classList.add('wa-ptt-active');

    var sent = false;

    function tryNextLang() {
        if (sent || vtuberWaitingForServer) return;
        if (langTryIndex + 1 < VTUBER_SPEECH_LANGS.length) {
            vtuberPttActive = true;
            startOneShotRecognition(langTryIndex + 1);
        } else {
            vtuberPttActive = false;
            showPttHint(true);
        }
    }

    vtuberRecognition.onresult = function(event) {
        if (vtuberWaitingForServer || sent) return;
        var lastIdx = event.results.length - 1;
        var result = event.results[lastIdx];
        if (!result.isFinal) return;

        var text = result[0].transcript.trim();
        if (!text || text.length < 2) return;

        sent = true;
        vtuberWaitingForServer = true;
        vtuberPttActive = false;
        if (btn) btn.classList.remove('recording');
        if (waPtt) waPtt.classList.remove('wa-ptt-active');

        var activeChar = currentCharacter || 'shiro';
        if (socket && socket.connected) {
            socket.emit('voice_text', {
                text: text,
                karakter: activeChar
            });
            console.log('VTuber PTT sent (' + activeChar + '):', text);
        } else {
            sent = false;
            vtuberWaitingForServer = false;
            showPttHint(true);
        }
    };

    vtuberRecognition.onerror = function(event) {
        console.warn('VTuber PTT error:', event.error, VTUBER_SPEECH_LANGS[langTryIndex]);
        if (btn) btn.classList.remove('recording');
        if (waPtt) waPtt.classList.remove('wa-ptt-active');
        if (event.error === 'not-allowed') {
            alert('Akses mikrofon ditolak.');
            vtuberMode = false;
            resetVTuberButton();
            vtuberPttActive = false;
            return;
        }
        if (event.error === 'no-speech' || event.error === 'aborted') {
            tryNextLang();
            return;
        }
        vtuberPttActive = false;
        showPttHint(true);
    };

    vtuberRecognition.onend = function() {
        if (btn) btn.classList.remove('recording');
        if (waPtt) waPtt.classList.remove('wa-ptt-active');
        if (sent || vtuberWaitingForServer) return;
        tryNextLang();
    };

    try {
        vtuberRecognition.start();
    } catch (e) {
        console.warn('PTT start error:', e);
        tryNextLang();
    }
}

function initSocket(socketInstance) {
    socket = socketInstance;
    console.log('Socket connected for VTuber');

    socket.on('transcript', function(data) {
        if (data.text && typeof addMessage === 'function') {
            addMessage(data.text, 'user');
        }
    });

    var streamBubbleEl = null;

    socket.on('stream_start', function(data) {
        if (typeof showTypingIndicator === 'function') hideTypingIndicator();
        var chatBox = document.getElementById('chatBox');
        if (!chatBox) return;
        var kar = data.karakter || currentCharacter || 'shiro';
        var oldLive = document.getElementById('streamBubbleLive');
        if (oldLive) oldLive.remove();
        streamBubbleEl = document.createElement('div');
        streamBubbleEl.className = 'msg msg-' + kar + ' stream-bubble';
        streamBubbleEl.id = 'streamBubbleLive';
        var bubble = document.createElement('div');
        bubble.className = 'msg-bubble';
        bubble.textContent = '...';
        streamBubbleEl.appendChild(bubble);
        chatBox.appendChild(streamBubbleEl);
        chatBox.scrollTop = chatBox.scrollHeight;
    });

    socket.on('stream_token', function(data) {
        if (typeof hideTypingIndicator === 'function') hideTypingIndicator();
        var kar = data.karakter || currentCharacter || 'shiro';
        var live = document.getElementById('streamBubbleLive');
        if (live) live.className = 'msg msg-' + kar + ' stream-bubble';
        var bubble = document.querySelector('#streamBubbleLive .msg-bubble');
        if (bubble && data.text) {
            bubble.textContent = data.text;
        }
        if (data.text && typeof showVTuberSubtitle === 'function') {
            showVTuberSubtitle(data.text);
        }
        var chatBox = document.getElementById('chatBox');
        if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;
    });

    socket.on('stream_end', function(data) {
        if (typeof hideTypingIndicator === 'function') hideTypingIndicator();
        var live = document.getElementById('streamBubbleLive');
        if (live) live.remove();
        streamBubbleEl = null;
    });

    socket.on('response', function(data) {
        console.log('Response received:', data.text, 'karakter:', data.karakter);
        var replyChar = data.karakter || currentCharacter || 'shiro';
        if (data.text && typeof addMessage === 'function') {
            addMessage(data.text, replyChar);
        }
        if (data.text && typeof showVTuberSubtitle === 'function') {
            showVTuberSubtitle(data.text);
        }
        if (data.audio) {
            playVTuberResponseAudio(data.audio, replyChar);
        }
        vtuberWaitingForServer = false;
        showPttHint(true);
    });

    socket.on('error', function(err) {
        console.warn('Socket error:', err.message);
        vtuberWaitingForServer = false;
        var live = document.getElementById('streamBubbleLive');
        if (live) live.remove();
        if (typeof hideTypingIndicator === 'function') hideTypingIndicator();
        showPttHint(true);
    });

    socket.on('audio_ready', function() {
        vtuberWaitingForServer = false;
        showPttHint(true);
    });

    socket.on('connect', function() {
        console.log('Socket reconnected for VTuber');
        if (vtuberMode) {
            vtuberWaitingForServer = false;
            updateVtuberPttHint();
            showPttHint(true);
        }
    });

    socket.on('disconnect', function() {
        console.warn('Socket disconnected for VTuber');
        if (vtuberMode && typeof showNotification === 'function') {
            showNotification(currentCharacter || 'shiro', 'Koneksi terputus, mencoba menyambung kembali...');
        }
    });
}

function playVTuberResponseAudio(base64Audio, karakter) {
    try {
        var byteCharacters = atob(base64Audio);
        var byteNumbers = new Array(byteCharacters.length);
        for (var i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        var byteArray = new Uint8Array(byteNumbers);
        var mimeType = base64Audio.indexOf('UklGR') === 0 ? 'audio/wav' : 'audio/wav';
        var audioBlob = new Blob([byteArray], { type: mimeType });
        var audioUrl = URL.createObjectURL(audioBlob);
        var audio = new Audio(audioUrl);

        var avatar = document.getElementById('homeAvatar');
        if (avatar) {
            avatar.classList.remove('idle');
            avatar.classList.add('speaking');
        }
        var glow = document.getElementById('avatarGlow');
        if (glow) glow.classList.add('active');
        if (typeof startLive2DLipSync === 'function') startLive2DLipSync(audio);
        if (typeof setWACallSpeaking === 'function') setWACallSpeaking(true);

        if (window.waCallSpeakerMuted) {
            audio.volume = 0;
        }

        audio.onended = function() {
            URL.revokeObjectURL(audioUrl);
            if (avatar) {
                avatar.classList.remove('speaking');
                avatar.classList.add('idle');
            }
            if (glow) glow.classList.remove('active');
            if (typeof stopLive2DLipSync === 'function') stopLive2DLipSync();
            if (typeof setWACallSpeaking === 'function') setWACallSpeaking(false);
            if (typeof showVTuberSubtitle === 'function') showVTuberSubtitle('');
        };
        audio.play().catch(function(e) {
            console.warn('Audio play error:', e);
        });
    } catch (e) {
        console.warn('playVTuberResponseAudio error:', e);
    }
}

// VTUBER MODE - toggle
window.toggleVTuberMode = function() {
    var turningOn = !vtuberMode;
    if (turningOn) {
        var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            alert('Browser tidak mendukung Speech Recognition. Gunakan Chrome atau Edge.');
            return;
        }
    }

    vtuberMode = turningOn;
    window.vtuberMode = vtuberMode;
    var btn = document.getElementById('btnVTuber');
    if (!btn) return;

    if (vtuberMode) {
        btn.style.background = '#ff6b8a';
        btn.style.color = '#fff';
        btn.querySelector('span').textContent = 'Berhenti';
        if (typeof openWACallOverlay === 'function') {
            openWACallOverlay();
        }
        if (typeof showNotification === 'function') {
            var charName = (currentCharacter === 'sishin') ? 'Sishin' : 'Shiro';
            showNotification(currentCharacter || 'shiro',
                'Video call VTuber! Tahan Space untuk bicara — ' + charName);
        }
        bindVTuberPTT();
        updateVtuberPttHint();
        startVTuber();
    } else {
        btn.style.background = '';
        btn.style.color = '';
        btn.querySelector('span').textContent = 'VTuber';
        if (typeof closeWACallOverlay === 'function') closeWACallOverlay();
        stopVTuber();
    }
};

function startVTuber() {
    if (!socket || !socket.connected) {
        console.warn('Socket not connected, attempting to reconnect...');
        if (socket && typeof socket.connect === 'function') {
            socket.connect();
        }
        setTimeout(function() {
            if (!socket || !socket.connected) {
                alert('Koneksi WebSocket belum siap. Pastikan server berjalan.');
                vtuberMode = false;
                resetVTuberButton();
                return;
            }
            if (vtuberMode) showPttHint(true);
        }, 1000);
        return;
    }
    showPttHint(true);
}

function resetVTuberButton() {
    var btn = document.getElementById('btnVTuber');
    if (!btn) return;
    btn.style.background = '';
    btn.style.color = '';
    btn.classList.remove('recording');
    btn.querySelector('span').textContent = 'VTuber';
}

function stopVTuber() {
    vtuberWaitingForServer = false;
    vtuberPttActive = false;
    window.vtuberMode = false;
    resetVTuberButton();
    showPttHint(false);
    if (typeof closeWACallOverlay === 'function') closeWACallOverlay();
    if (typeof setWACallSpeaking === 'function') setWACallSpeaking(false);

    if (vtuberRecognition) {
        try { vtuberRecognition.abort(); } catch (e) {}
        vtuberRecognition.onend = null;
        vtuberRecognition.onerror = null;
        vtuberRecognition.onresult = null;
        vtuberRecognition = null;
    }

    console.log('VTuber stopped');
}