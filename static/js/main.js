// ==========================================
// SHIRO AI - MAIN APPLICATION
// ==========================================

// ==========================================
// SHIRO AI - MAIN APPLICATION
// ==========================================

// ----- VARIABLES -----
var currentCharacter = 'shiro';
var bgmIndex = 0;
var bgmList = ['bgm_1.mp3', 'bgm_2.mp3', 'bgm_3.mp3', 'bgm_4.mp3', 'bgm_5.mp3'];
var bgmNames = ['Lagu Santai', 'Lagu Ceria', 'Lagu Romantis', 'Lagu Semangat', 'Lagu Malam'];
var mediaRecorder = null;
var audioChunks = [];
var isRecording = false;

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
// THEME MANAGEMENT
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

    for (var key in effects) {
        if (effects[key]) effects[key].classList.remove('active');
    }

    switch (theme) {
        case 'morning': if (effects.sunRay) effects.sunRay.classList.add('active'); break;
        case 'afternoon': if (effects.glint) effects.glint.classList.add('active'); break;
        case 'evening': if (effects.sunsetGlow) effects.sunsetGlow.classList.add('active'); break;
        case 'spring': if (effects.sakura) effects.sakura.classList.add('active'); break;
        case 'summer': if (effects.heatHaze) effects.heatHaze.classList.add('active'); break;
        case 'autumn': if (effects.leaf) effects.leaf.classList.add('active'); break;
        case 'winter': if (effects.snow) effects.snow.classList.add('active'); break;
        case 'rain': if (effects.rain) { effects.rain.classList.add('active'); createRain(); } break;
        default: break;
    }
}

// ==========================================
// PLAYLIST FUNCTIONS
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

// ==========================================
// BGM CONTROL
// ==========================================

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
// SWITCH CHARACTER  (sudah diperbaiki, hanya satu fungsi)
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
}

// ==========================================
// STATUS UPDATE
// ==========================================

async function updateStatus() {
    try {
        var response = await fetch('/status');
        var data = await response.json();
        var affection = data.affection || 50;
        var level = data.level || 1;

        document.getElementById('affectionDisplay').textContent = affection;
        document.getElementById('levelDisplay').textContent = level;
        document.getElementById('hpBar').style.width = affection + '%';
        document.getElementById('hpPercent').textContent = affection;
        document.getElementById('chatCharStatus').textContent = 'Afeksi ' + affection + '%';

        var quotes = [
            'Hari ini akan indah, seperti senyummu.',
            'Kamu adalah alasan aku tersenyum.',
            'Aku nunggu kamu, Sayang.',
            'Jangan lupa makan siang.',
            'Kamu hari ini tambah ganteng dan cantik.'
        ];
        document.querySelector('.quote-text').textContent = quotes[Math.floor(Math.random() * quotes.length)];
    } catch (error) {
        console.log('Status update error:', error);
    }
}
updateStatus();
setInterval(updateStatus, 15000);

// ==========================================
// NAVIGATION
// ==========================================

function openChat() {
    document.getElementById('homeScreen').style.display = 'none';
    document.getElementById('chatScreen').style.display = 'flex';
    var fab = document.getElementById('fabChat');
    if (fab) fab.style.display = 'none';
    var chatName = document.getElementById('chatCharName');
    if (chatName) {
        chatName.textContent = currentCharacter === 'shiro' ? 'Shiro' : 'Sishin';
    }
    var chatBox = document.getElementById('chatBox');
    if (chatBox && chatBox.children.length === 0) {
        addMessage(
            currentCharacter === 'shiro'
                ? 'Halo Sayang! Yuk ngobrol~'
                : 'Kak! Sishin siap main bareng!',
            currentCharacter
        );
    }
    document.getElementById('userInput').focus();
}

function closeChat() {
    document.getElementById('homeScreen').style.display = 'flex';
    document.getElementById('chatScreen').style.display = 'none';
    var fab = document.getElementById('fabChat');
    if (fab) fab.style.display = 'flex';
    updateStatus();
}

// ==========================================
// CHAT
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

async function sendMessage() {
    var input = document.getElementById('userInput');
    var button = document.getElementById('sendBtn');
    if (!input) return;

    var message = input.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    input.value = '';
    input.disabled = true;
    button.disabled = true;

    var karakter = currentCharacter;

    var avatar = document.getElementById('homeAvatar');
    var glow = document.getElementById('avatarGlow');
    if (avatar) avatar.classList.add('speaking');
    if (glow) glow.classList.add('active');

    try {
        var response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, karakter: karakter })
        });

        var data = await response.json();
        var reply = data.reply || 'Maaf, aku sedang sibuk.';
        var detectedChar = data.karakter || karakter;

        addMessage(reply, detectedChar);

        var ttsResponse = await fetch('/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: data.suara || reply, karakter: detectedChar })
        });

        if (ttsResponse.ok) {
            var audioBlob = await ttsResponse.blob();
            var audioUrl = URL.createObjectURL(audioBlob);
            var audio = new Audio(audioUrl);
            audio.play();

            audio.onended = function() {
                if (avatar) avatar.classList.remove('speaking');
                if (glow) glow.classList.remove('active');
                URL.revokeObjectURL(audioUrl);
            };
        } else {
            if (avatar) avatar.classList.remove('speaking');
            if (glow) glow.classList.remove('active');
        }
    } catch (error) {
        addMessage('Maaf, ada masalah koneksi.', 'shiro');
        if (avatar) avatar.classList.remove('speaking');
        if (glow) glow.classList.remove('active');
        console.error('Send message error:', error);
    }

    input.disabled = false;
    button.disabled = false;
    input.focus();
}

// ==========================================
// CAMERA
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
// VOICE
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
// CHARACTER INTERACTION
// ==========================================

document.getElementById('homeAvatar')?.addEventListener('click', function() {
    openChat();
});

// ==========================================
// EVENT LISTENERS
// ==========================================

document.getElementById('sendBtn')?.addEventListener('click', sendMessage);
document.getElementById('userInput')?.addEventListener('keypress', function(event) {
    if (event.key === 'Enter') sendMessage();
});

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
});

console.log('Shiro AI initialized.');
// Override sendMessage untuk menambahkan konteks antar karakter
(function() {
    // Simpan referensi ke fungsi sendMessage yang sudah ada (yang sudah di-override sebelumnya)
    // Karena kita sudah override sebelumnya, kita ambil dari window.sendMessage
    // Tapi kita akan buat fungsi baru yang sepenuhnya menggantikan.
    // Kita akan copy paste dari script sebelumnya, lalu kita modifikasi.

    // Sebenarnya lebih mudah: kita override lagi dengan fungsi baru yang memanggil fungsi lama,
    // tapi fungsi lama sudah menampilkan pesan dan mengirim. Kita tidak bisa memanggilnya karena
    // akan mengirim pesan asli. Jadi kita harus membuat ulang dari awal, dengan modifikasi.

    // Kita akan ambil kode sendMessage dari script sebelumnya dan kita modifikasi.

    var originalAddMessage = window.addMessage;
    var chatHistory = window.chatHistory || { shiro: [], sishin: [] };

    // Fungsi untuk mendapatkan 2 pesan terakhir dari karakter tertentu (hanya dari AI, bukan user)
    function getLastMessagesFromCharacter(char, count) {
        var history = chatHistory[char] || [];
        var messages = history.filter(function(msg) {
            return msg.sender === char;
        });
        return messages.slice(-count);
    }

    // Fungsi untuk membangun konteks
    function buildContext(char) {
        // Ambil karakter lain
        var otherChar = (char === 'shiro') ? 'sishin' : 'shiro';
        var lastMessages = getLastMessagesFromCharacter(otherChar, 2);
        if (lastMessages.length === 0) return null;

        var contextText = '';
        var name = otherChar === 'shiro' ? 'Shiro' : 'Sishin';
        // Buat kalimat konteks
        var messagesStr = lastMessages.map(function(msg) {
            return '"' + msg.text + '"';
        }).join(', ');
        contextText = 'Oh iya, sebelumnya ' + name + ' pernah bilang: ' + messagesStr + '.';
        return contextText;
    }

    // Override sendMessage
    window.sendMessage = function() {
        var input = document.getElementById('userInput');
        if (!input) return;
        var message = input.value.trim();
        if (!message) return;

        // Ambil karakter aktif
        var char = window.currentCharacter || 'shiro';

        // Tentukan apakah tambahkan konteks (30% kemungkinan)
        var shouldAddContext = (Math.random() < 0.3);
        var modifiedMessage = message;

        if (shouldAddContext) {
            var context = buildContext(char);
            if (context) {
                modifiedMessage = message + ' ' + context;
                console.log('Menambahkan konteks:', context);
            }
        }

        // Tampilkan pesan asli di chat
        chatHistory[char].push({ text: message, sender: 'user' });
        originalAddMessage(message, 'user');

        // Kosongkan input
        input.value = '';

        // Kirim ke server dengan pesan yang mungkin sudah dimodifikasi
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

            // Tambahkan balasan ke riwayat dan tampilkan
            chatHistory[detectedChar].push({ text: reply, sender: detectedChar });
            originalAddMessage(reply, detectedChar);

            // TTS
            return fetch('/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: data.suara || reply, karakter: detectedChar })
            });
        })
        .then(function(ttsResponse) {
            if (ttsResponse && ttsResponse.ok) {
                return ttsResponse.blob();
            }
            return null;
        })
        .then(function(blob) {
            if (blob) {
                var audioUrl = URL.createObjectURL(blob);
                var audio = new Audio(audioUrl);
                audio.play();
                audio.onended = function() {
                    var avatar = document.getElementById('homeAvatar');
                    var glow = document.getElementById('avatarGlow');
                    if (avatar) avatar.classList.remove('speaking');
                    if (glow) glow.classList.remove('active');
                    URL.revokeObjectURL(audioUrl);
                };
            } else {
                var avatar = document.getElementById('homeAvatar');
                var glow = document.getElementById('avatarGlow');
                if (avatar) avatar.classList.remove('speaking');
                if (glow) glow.classList.remove('active');
            }
        })
        .catch(function(error) {
            console.error('Send message error:', error);
            originalAddMessage('Maaf, ada masalah koneksi.', 'shiro');
            var avatar = document.getElementById('homeAvatar');
            var glow = document.getElementById('avatarGlow');
            if (avatar) avatar.classList.remove('speaking');
            if (glow) glow.classList.remove('active');
        })
        .finally(function() {
            input.disabled = false;
            if (button) button.disabled = false;
            input.focus();
        });
    };

    console.log('Fitur konteks antar karakter diaktifkan (30% kemungkinan).');
})();