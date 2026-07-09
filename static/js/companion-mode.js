/**
 * Laplace-style Companion+ mode:
 * - Presence Vision (periodic webcam glance + comment)
 * - Music reactions & sing-along
 * - Live2D beat dance on BGM
 * - Duplex voice (continuous listen + barge-in)
 */
(function(global) {
    'use strict';

    var STORAGE_KEY = 'shiro_companion_plus';
    var enabled = false;
    var presenceTimer = null;
    var musicOpinionTimer = null;
    var musicSingTimer = null;
    var presenceStream = null;
    var presenceBusy = false;
    var duplexRecognition = null;
    var duplexListening = false;
    var lastMusicTrack = '';

    function $(id) { return document.getElementById(id); }

    function readEnabled() {
        try { return localStorage.getItem(STORAGE_KEY) === '1'; } catch (e) { return false; }
    }

    function writeEnabled(on) {
        try { localStorage.setItem(STORAGE_KEY, on ? '1' : '0'); } catch (e) { /* ignore */ }
    }

    function getChar() {
        if (global.CharacterState) return CharacterState.get();
        return global.currentCharacter || 'shiro';
    }

    function showPresenceChip(text) {
        var sub = $('homeCharSub');
        if (!sub || !text) return;
        if (!sub.dataset.cmPrev) sub.dataset.cmPrev = sub.textContent;
        sub.textContent = text;
        sub.classList.add('companion-presence-active');
        setTimeout(function() {
            if (sub.dataset.cmPrev) sub.textContent = sub.dataset.cmPrev;
            sub.classList.remove('companion-presence-active');
        }, 6000);
    }

    function interruptSpeech() {
        if (global.audioPlayer) {
            try {
                global.audioPlayer.pause();
                global.audioPlayer.currentTime = 0;
            } catch (e) { /* ignore */ }
        }
        if (typeof global.stopLive2DLipSync === 'function') stopLive2DLipSync();
        if (typeof global.stopLive2DBeatDance === 'function') stopLive2DBeatDance();
    }

    global.interruptCompanionSpeech = interruptSpeech;

    function speakReply(reply, karakter) {
        if (!reply) return;
        if (typeof global.addMessage === 'function') {
            try { global.addMessage(reply, karakter); } catch (e) { /* ignore */ }
        }
        showPresenceChip(reply);
        if (typeof global.putarAudio === 'function') {
            global.putarAudio(reply, karakter);
        }
    }

    function capturePresenceFrame() {
        var video = $('companionPresenceVideo');
        var canvas = $('companionPresenceCanvas');
        if (!video || !canvas || video.readyState < 2) return null;
        var w = video.videoWidth || 640;
        var h = video.videoHeight || 480;
        if (!w || !h) return null;
        canvas.width = Math.min(w, 640);
        canvas.height = Math.min(h, 480);
        var ctx = canvas.getContext('2d');
        if (!ctx) return null;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        try {
            return canvas.toDataURL('image/jpeg', 0.72);
        } catch (e) {
            return null;
        }
    }

    function runPresenceGlance() {
        if (!enabled || presenceBusy || document.hidden) return;
        var frame = capturePresenceFrame();
        if (!frame) return;
        presenceBusy = true;
        var karakter = getChar();
        fetch('/api/companion/presence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_base64: frame,
                karakter: karakter,
                character_name: karakter
            })
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!enabled || !data.reply) return;
                speakReply(data.reply, data.karakter || karakter);
            })
            .catch(function(err) { console.warn('[Companion+]', err); })
            .finally(function() { presenceBusy = false; });
    }

    function startPresenceCamera() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) return Promise.reject();
        return navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
            audio: false
        }).then(function(stream) {
            presenceStream = stream;
            var video = $('companionPresenceVideo');
            if (video) {
                video.srcObject = stream;
                return video.play();
            }
        });
    }

    function stopPresenceCamera() {
        if (presenceStream) {
            presenceStream.getTracks().forEach(function(t) { t.stop(); });
            presenceStream = null;
        }
        var video = $('companionPresenceVideo');
        if (video) video.srcObject = null;
    }

    function startPresenceLoop() {
        stopPresenceLoop();
        startPresenceCamera()
            .then(function() {
                setTimeout(runPresenceGlance, 8000);
                presenceTimer = setInterval(runPresenceGlance, 50000);
            })
            .catch(function() {
                console.warn('[Companion+] Kamera ditolak — presence vision nonaktif');
            });
    }

    function stopPresenceLoop() {
        if (presenceTimer) {
            clearInterval(presenceTimer);
            presenceTimer = null;
        }
        stopPresenceCamera();
    }

    function getCurrentTrackName() {
        var audio = $('bgmAudio');
        if (!audio || audio.paused || !audio.src) return '';
        var idx = typeof global.bgmIndex === 'number' ? global.bgmIndex : 0;
        if (global.bgmNames && global.bgmNames[idx]) return global.bgmNames[idx];
        if (global.bgmList && global.bgmList[idx]) return global.bgmList[idx];
        return 'lagu ini';
    }

    function requestMusicReaction(mode) {
        if (!enabled) return;
        var track = getCurrentTrackName();
        if (!track) return;
        var karakter = getChar();
        fetch('/api/companion/music', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ karakter: karakter, track: track, mode: mode || 'opinion' })
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (!enabled || !data.reply) return;
                speakReply(data.reply, data.karakter || karakter);
            })
            .catch(function(err) { console.warn('[Companion+] music', err); });
    }

    function onBgmPlay(audioEl) {
        if (!enabled) return;
        var track = getCurrentTrackName();
        if (track && track !== lastMusicTrack) {
            lastMusicTrack = track;
            setTimeout(function() { requestMusicReaction('opinion'); }, 12000);
        }
        if (typeof global.startLive2DBeatDance === 'function') {
            global.startLive2DBeatDance(audioEl || $('bgmAudio'));
        }
        if (musicOpinionTimer) clearInterval(musicOpinionTimer);
        musicOpinionTimer = setInterval(function() {
            var a = $('bgmAudio');
            if (!a || a.paused) return;
            requestMusicReaction('opinion');
        }, 110000);
        if (musicSingTimer) clearInterval(musicSingTimer);
        musicSingTimer = setInterval(function() {
            var a = $('bgmAudio');
            if (!a || a.paused) return;
            requestMusicReaction('sing');
        }, 200000);
    }

    function onBgmPause() {
        if (musicOpinionTimer) { clearInterval(musicOpinionTimer); musicOpinionTimer = null; }
        if (musicSingTimer) { clearInterval(musicSingTimer); musicSingTimer = null; }
        if (typeof global.stopLive2DBeatDance === 'function') stopLive2DBeatDance();
    }

    function bindMusicHooks() {
        document.addEventListener('play', function(ev) {
            if (!enabled) return;
            if (ev.target && ev.target.id === 'bgmAudio') onBgmPlay(ev.target);
        }, true);
        document.addEventListener('pause', function(ev) {
            if (ev.target && ev.target.id === 'bgmAudio') onBgmPause();
        }, true);
        document.addEventListener('ended', function(ev) {
            if (ev.target && ev.target.id === 'bgmAudio') onBgmPause();
        }, true);
    }

    function dispatchDuplexText(text) {
        if (!text || text.length < 2) return;
        interruptSpeech();
        var karakter = getChar();
        var payload = { text: text, karakter: karakter, voice_commands: true };
        if (global.socket && global.socket.connected) {
            global.socket.emit('voice_text', payload);
            return;
        }
        fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text, karakter: karakter, voice_commands: true })
        })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.reply) speakReply(data.reply, data.karakter || karakter);
            });
    }

    function startDuplexVoice() {
        var SR = global.SpeechRecognition || global.webkitSpeechRecognition;
        if (!SR || duplexListening) return;
        duplexRecognition = new SR();
        duplexRecognition.lang = 'id-ID';
        duplexRecognition.continuous = true;
        duplexRecognition.interimResults = false;
        duplexRecognition.onresult = function(event) {
            var last = event.results.length - 1;
            if (!event.results[last].isFinal) return;
            dispatchDuplexText(event.results[last][0].transcript.trim());
        };
        duplexRecognition.onerror = function(ev) {
            if (ev.error === 'not-allowed') stopDuplexVoice();
        };
        duplexRecognition.onend = function() {
            duplexListening = false;
            if (enabled) setTimeout(startDuplexVoice, 800);
        };
        try {
            duplexRecognition.start();
            duplexListening = true;
        } catch (e) { console.warn('[Companion+] duplex start', e); }
    }

    function stopDuplexVoice() {
        duplexListening = false;
        if (duplexRecognition) {
            try { duplexRecognition.stop(); } catch (e) { /* ignore */ }
            duplexRecognition = null;
        }
    }

    function updateToggleButton() {
        var btn = $('btnCompanionPlus');
        if (!btn) return;
        btn.classList.toggle('active', enabled);
        var label = btn.querySelector('span');
        if (label) label.textContent = enabled ? 'Companion+' : 'Companion';
        btn.title = enabled
            ? 'Companion+ ON — lihat, musik, nyanyi, obrol suara bebas'
            : 'Companion+ OFF — mode Laplace-style';
    }

    function enable() {
        enabled = true;
        writeEnabled(true);
        updateToggleButton();
        startPresenceLoop();
        startDuplexVoice();
        var bgm = $('bgmAudio');
        if (bgm && !bgm.paused) onBgmPlay(bgm);
        showPresenceChip('Companion+ aktif — aku bisa lihat, denger musik, dan ngobrol terus~');
    }

    function disable() {
        enabled = false;
        writeEnabled(false);
        updateToggleButton();
        stopPresenceLoop();
        stopDuplexVoice();
        onBgmPause();
    }

    function toggle() {
        if (enabled) disable();
        else enable();
    }

    function init() {
        bindMusicHooks();
        updateToggleButton();
        if (readEnabled()) enable();
    }

    global.CompanionMode = {
        enable: enable,
        disable: disable,
        toggle: toggle,
        isEnabled: function() { return enabled; },
        runPresenceGlance: runPresenceGlance
    };
    global.toggleCompanionPlus = toggle;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}(window));
