/**
 * Shiro AI — Desktop pet companion (overlay window)
 * Chat + TTS + Live2D + voice via existing backend (/chat, /tts, Socket.IO)
 */
(function(global) {
    'use strict';

    var currentChar = 'shiro';
    var socket = null;
    var audioPlayer = null;
    var recognition = null;
    var pttActive = false;
    var waitingServer = false;
    var live2dOn = false;

    var CHAR_NAMES = { shiro: 'Shiro', sishin: 'Sishin' };
    var CHAR_PNG = {
        shiro: '/static/images/shiro.png',
        sishin: '/static/images/sishin.png'
    };

    var DESKTOP_GREETINGS = {
        shiro: {
            morning: 'Selamat pagi, Sayang~ Shiro udah nunggu kamu di desktop...',
            afternoon: 'Sayang~ Shiro ada di sini ya. Kangen deh...',
            evening: 'Selamat sore, Sayang. Shiro temenin kamu malam ini~',
            night: 'Malam-malam masih begadang? Shiro khawatir lho...'
        },
        sishin: {
            morning: 'Kak! Selamat pagi~ Sishin udah bangun! Ayo semangat ya!',
            afternoon: 'Kak! Sishin nemenin di desktop nih~ main yuk!',
            evening: 'Kak Shin~ sore-sore gini Sishin temenin ya!',
            night: 'Kak... jangan begadang terus. Sishin khawatir nih~'
        }
    };

    var DESKTOP_GREETINGS_EXTRA = {
        shiro: [
            'Sayang~ Shiro ada di desktop kamu sekarang...',
            'Ehehe~ Kakak buka laptop? Shiro seneng banget~'
        ],
        sishin: [
            'Kak! Sishin nemenin di desktop ya~',
            'Hehe~ Kakak online? Sishin kangen banget!',
            'Kak Shin! Sishin di sini kok~ chat yuk!',
            'Yay! Akhirnya Kakak buka laptop~ Sishin seneng!'
        ]
    };

    function getTimeSlot() {
        var h = new Date().getHours();
        if (h >= 5 && h < 11) return 'morning';
        if (h >= 11 && h < 17) return 'afternoon';
        if (h >= 17 && h < 21) return 'evening';
        return 'night';
    }

    function pickDesktopGreeting(char) {
        char = char === 'sishin' ? 'sishin' : 'shiro';
        var slot = getTimeSlot();
        var primary = (DESKTOP_GREETINGS[char] && DESKTOP_GREETINGS[char][slot]) || '';
        var extras = DESKTOP_GREETINGS_EXTRA[char] || [];
        if (Math.random() < 0.55 && primary) return primary;
        if (extras.length) return extras[Math.floor(Math.random() * extras.length)];
        return primary || 'Halo~';
    }

    function $(id) { return document.getElementById(id); }

    function setChar(char, options) {
        options = options || {};
        char = char === 'sishin' ? 'sishin' : 'shiro';
        var changed = char !== currentChar;
        currentChar = char;
        if (global.CharacterState) CharacterState.set(char);

        var pet = $('desktopPet');
        if (pet) pet.classList.toggle('sishin-theme', char === 'sishin');

        var nameEl = $('desktopCharName');
        if (nameEl) nameEl.textContent = CHAR_NAMES[char];

        $('btnDeskShiro').classList.toggle('active', char === 'shiro');
        $('btnDeskSishin').classList.toggle('active', char === 'sishin');

        var input = $('deskInput');
        if (input) input.placeholder = 'Ketik ke ' + CHAR_NAMES[char] + '...';

        var avatar = $('deskAvatar');
        if (avatar) {
            avatar.src = CHAR_PNG[char];
            avatar.className = 'desk-avatar ' + (char === 'sishin' ? 'sishin-mode' : 'shiro-mode');
        }

        initLive2DForChar(char);

        if (!options.silent && (changed || options.greet)) {
            var greet = pickDesktopGreeting(char);
            showBubble(greet);
            playTTS(greet, char);
        }
    }

    function showBubble(text) {
        var bubble = $('deskBubble');
        var textEl = $('deskBubbleText');
        if (!bubble || !textEl) return;
        textEl.textContent = text;
        bubble.classList.remove('hidden');
    }

    function showTyping(on) {
        var el = $('deskTyping');
        if (el) el.classList.toggle('hidden', !on);
    }

    async function playTTS(text, char) {
        if (!text) return;
        try {
            var res = await fetch('/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text, karakter: char || currentChar })
            });
            if (!res.ok) return;
            var blob = await res.blob();
            var url = URL.createObjectURL(blob);
            if (audioPlayer) {
                audioPlayer.pause();
                audioPlayer.src = '';
            }
            audioPlayer = new Audio(url);
            if (typeof global.startLive2DLipSync === 'function') {
                global.startLive2DLipSync(audioPlayer);
            }
            audioPlayer.onended = function() {
                URL.revokeObjectURL(url);
                if (typeof global.stopLive2DLipSync === 'function') global.stopLive2DLipSync();
            };
            await audioPlayer.play();
        } catch (e) {
            console.warn('[Desktop] TTS:', e);
        }
    }

    function playSocketAudio(base64Audio, char) {
        try {
            var bytes = atob(base64Audio);
            var arr = new Uint8Array(bytes.length);
            for (var i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
            var blob = new Blob([arr], { type: 'audio/wav' });
            var url = URL.createObjectURL(blob);
            audioPlayer = new Audio(url);
            if (typeof global.startLive2DLipSync === 'function') {
                global.startLive2DLipSync(audioPlayer);
            }
            audioPlayer.onended = function() {
                URL.revokeObjectURL(url);
                if (typeof global.stopLive2DLipSync === 'function') global.stopLive2DLipSync();
            };
            audioPlayer.play();
        } catch (e) {
            console.warn('[Desktop] socket audio:', e);
        }
    }

    async function sendChat() {
        var input = $('deskInput');
        if (!input || waitingServer) return;
        var msg = input.value.trim();
        if (!msg) return;

        input.value = '';
        waitingServer = true;
        $('deskSendBtn').disabled = true;
        showTyping(true);

        try {
            var res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg, karakter: currentChar })
            });
            var data = await res.json();
            showTyping(false);
            if (data.reply) {
                showBubble(data.reply);
                await playTTS(data.suara || data.reply, data.karakter || currentChar);
            }
        } catch (e) {
            showTyping(false);
            showBubble(currentChar === 'sishin'
                ? 'Kak... koneksinya bermasalah. Coba lagi ya~'
                : 'Maaf Sayang, koneksi bermasalah...');
        } finally {
            waitingServer = false;
            $('deskSendBtn').disabled = false;
        }
    }

    function initSpeech() {
        var SR = global.SpeechRecognition || global.webkitSpeechRecognition;
        if (!SR) return;
        recognition = new SR();
        recognition.lang = 'id-ID';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = function(ev) {
            var text = ev.results[0][0].transcript.trim();
            if (!text || waitingServer) return;
            waitingServer = true;
            showTyping(true);
            if (socket && socket.connected) {
                socket.emit('voice_text', { text: text, karakter: currentChar, voice_commands: false });
            } else {
                $('deskInput').value = text;
                waitingServer = false;
                sendChat();
            }
        };

        recognition.onerror = function() {
            stopPTT();
            waitingServer = false;
            showTyping(false);
        };

        recognition.onend = function() {
            var mic = $('deskMicBtn');
            if (mic) mic.classList.remove('recording');
            pttActive = false;
        };
    }

    function startPTT() {
        if (!recognition || pttActive || waitingServer) return;
        pttActive = true;
        $('deskMicBtn').classList.add('recording');
        try { recognition.start(); } catch (e) { /* ignore */ }
    }

    function stopPTT() {
        if (!recognition) return;
        $('deskMicBtn').classList.remove('recording');
        pttActive = false;
        try { recognition.stop(); } catch (e) { /* ignore */ }
    }

    function initSocket() {
        socket = io(global.location.origin, { transports: ['websocket', 'polling'], reconnection: true });

        socket.on('response', function(data) {
            waitingServer = false;
            showTyping(false);
            var reply = data.text || data.reply;
            var char = data.karakter || currentChar;
            if (reply) {
                showBubble(reply);
                if (data.audio) playSocketAudio(data.audio, char);
                else playTTS(data.suara || reply, char);
            }
        });

        socket.on('error', function(err) {
            waitingServer = false;
            showTyping(false);
            if (err && err.message) showBubble(err.message);
        });

        socket.on('app_shutdown', function() {
            if (audioPlayer) {
                try {
                    audioPlayer.pause();
                    audioPlayer.src = '';
                } catch (e) { /* ignore */ }
                audioPlayer = null;
            }
            if (global.stopLive2DLipSync) global.stopLive2DLipSync();
            try {
                localStorage.setItem('shiro_ai_stop_audio', String(Date.now()));
            } catch (e) { /* ignore */ }
        });
    }

    function initLive2DForChar(char) {
        /* Desktop mode: selalu coba Live2D (tanpa buka browser / lemari manual) */
        if (typeof global.activateLive2DFromWardrobe === 'function') {
            global.activateLive2DFromWardrobe(char).then(function(ok) {
                live2dOn = !!ok;
                var av = $('deskAvatar');
                if (av) av.classList.toggle('hidden', live2dOn);
                if (!ok) {
                    console.warn('[Desktop] Live2D gagal — pakai PNG. Cek internet lalu refresh.');
                }
            });
            return;
        }
        if (!global.AssetManager) return;
        AssetManager.fetchCatalog().then(function() {
            var outfit = AssetManager.getOutfit(char, 'live2d');
            if (outfit && outfit.mode === 'live2d') {
                AssetManager.setOutfit(char, 'live2d');
                live2dOn = true;
                var av = $('deskAvatar');
                if (av) av.classList.add('hidden');
            }
        });
    }

    function bindUI() {
        $('deskSendBtn').addEventListener('click', sendChat);
        $('deskInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') sendChat();
        });

        var mic = $('deskMicBtn');
        mic.addEventListener('mousedown', function(e) { e.preventDefault(); startPTT(); });
        mic.addEventListener('mouseup', stopPTT);
        mic.addEventListener('mouseleave', stopPTT);

        document.addEventListener('keydown', function(e) {
            if (e.code === 'Space' && document.activeElement !== $('deskInput')) {
                e.preventDefault();
                startPTT();
            }
        });
        document.addEventListener('keyup', function(e) {
            if (e.code === 'Space') stopPTT();
        });

        $('btnDeskShiro').addEventListener('click', function() { setChar('shiro'); });
        $('btnDeskSishin').addEventListener('click', function() { setChar('sishin'); });

        $('btnDeskOpenApp').addEventListener('click', function() {
            global.open('http://127.0.0.1:5000/', '_blank');
        });

        $('btnDeskHide').addEventListener('click', function() {
            if (global.pywebview && global.pywebview.api && global.pywebview.api.hide_window) {
                global.pywebview.api.hide_window();
            } else {
                document.body.style.opacity = '0.3';
            }
        });

        var cmpLink = $('deskCompanionToggle');
        if (cmpLink) {
            cmpLink.addEventListener('click', function(e) {
                e.preventDefault();
                if (global.CompanionMode && typeof CompanionMode.toggle === 'function') {
                    CompanionMode.toggle();
                }
            });
        }
    }

    function init() {
        console.log('[Desktop] Companion mode — http://127.0.0.1:5000/desktop');
        bindUI();
        initSpeech();
        initSocket();
        var saved = global.CharacterState ? CharacterState.get() : 'shiro';
        setChar(saved, { greet: true });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}(window));
