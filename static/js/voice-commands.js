/**
 * Voice Command Assistant — wake-word listener + app launch (Shiro & Sishin)
 *
 * Backend: app/voice_commands.py
 * Toggle: tombol "Voice Cmd" atau VoiceCommands.toggle()
 */
(function(global) {
    'use strict';

    var STORAGE_KEY = 'shiro_voice_commands_enabled';

    var WAKE_WORDS = {
        shiro: ['shiro', 'siro', 'hey shiro', 'hei shiro', 'hai shiro'],
        sishin: ['sishin', 'sisin', 'sashin', 'hey sishin', 'hei sishin']
    };

    var OPEN_HINTS = /\b(buka|bukain|jalankan|nyalakan|open|launch|start|run)\b/i;

    var recognition = null;
    var listening = false;
    var commandMode = false;
    var commandModeTimer = null;
    var restartTimer = null;

    function getSpeechRecognition() {
        return global.SpeechRecognition || global.webkitSpeechRecognition || null;
    }

    function getActiveCharacter() {
        if (global.CharacterState) return CharacterState.get();
        return global.currentCharacter || 'shiro';
    }

    function readStoredEnabled() {
        try {
            var v = localStorage.getItem(STORAGE_KEY);
            if (v === null) {
                /* migrate legacy wake-word flag */
                if (localStorage.getItem('shiro_wake_word') === '1') return true;
                return true;
            }
            return v === '1';
        } catch (e) {
            return true;
        }
    }

    function writeStoredEnabled(on) {
        try {
            localStorage.setItem(STORAGE_KEY, on ? '1' : '0');
            if (!on) localStorage.removeItem('shiro_wake_word');
        } catch (e) { /* ignore */ }
    }

    function isFeatureEnabled() {
        return readStoredEnabled();
    }

    function isWakeListening() {
        return isFeatureEnabled() && listening;
    }

    function updateToggleButton() {
        var btn = document.getElementById('btnVoiceCommands');
        if (!btn) return;
        var on = isFeatureEnabled();
        btn.classList.toggle('active', on);
        btn.setAttribute('aria-pressed', on ? 'true' : 'false');
        var label = btn.querySelector('span');
        if (label) label.textContent = on ? 'Voice ON' : 'Voice OFF';
        btn.title = on
            ? 'Voice Command aktif (Shiro & Sishin bisa buka app)'
            : 'Voice Command nonaktif — klik untuk nyalakan';
    }

    function dispatchCommand(text, karakter) {
        karakter = karakter || getActiveCharacter();
        var payload = {
            text: text,
            karakter: karakter,
            voice_commands: isFeatureEnabled()
        };

        if (global.socket && global.socket.connected) {
            global.socket.emit('voice_text', payload);
            console.log('[VoiceCommands] sent (' + karakter + '):', text);
            return true;
        }

        if (typeof global.sendMessageWithText === 'function') {
            global.sendMessageWithText(text, { voice_commands: isFeatureEnabled() });
            return true;
        }

        if (global.inputPesan) {
            global.inputPesan.value = text;
            if (typeof global.sendMessage === 'function') {
                global.sendMessage();
                return true;
            }
        }
        return false;
    }

    function containsWakeWord(text) {
        var lower = (text || '').toLowerCase().trim();
        var all = WAKE_WORDS.shiro.concat(WAKE_WORDS.sishin);
        for (var i = 0; i < all.length; i++) {
            if (lower.indexOf(all[i]) === 0 || lower.indexOf(' ' + all[i]) >= 0) {
                return true;
            }
        }
        return false;
    }

    function resolveSpeakerChar(text) {
        var lower = (text || '').toLowerCase();
        if (WAKE_WORDS.sishin.some(function(w) { return lower.indexOf(w) === 0; })) {
            return 'sishin';
        }
        if (WAKE_WORDS.shiro.some(function(w) { return lower.indexOf(w) === 0; })) {
            return 'shiro';
        }
        return getActiveCharacter();
    }

    function handleTranscript(text) {
        if (!isFeatureEnabled() || !text || text.length < 2) return;

        var karakter = resolveSpeakerChar(text);

        if (commandMode || OPEN_HINTS.test(text) || containsWakeWord(text)) {
            commandMode = false;
            if (commandModeTimer) {
                clearTimeout(commandModeTimer);
                commandModeTimer = null;
            }
            dispatchCommand(text, karakter);
            return;
        }

        if (containsWakeWord(text)) {
            commandMode = true;
            var name = karakter === 'sishin' ? 'Sishin' : 'Shiro';
            showHint(name + ' siap — sebut perintah (contoh: buka chrome)');
            commandModeTimer = setTimeout(function() { commandMode = false; }, 8000);
        }
    }

    function showHint(msg) {
        var sub = document.getElementById('homeCharSub');
        if (!sub || !msg) return;
        if (!sub.dataset.vcPrev) sub.dataset.vcPrev = sub.textContent;
        sub.textContent = msg;
        sub.style.color = 'rgba(255, 200, 120, 0.85)';
        setTimeout(function() {
            if (sub.textContent === msg && sub.dataset.vcPrev) {
                sub.textContent = sub.dataset.vcPrev;
                sub.style.color = '';
            }
        }, 4500);
    }

    function stopListening() {
        listening = false;
        if (restartTimer) {
            clearTimeout(restartTimer);
            restartTimer = null;
        }
        if (recognition) {
            try { recognition.stop(); } catch (e) { /* ignore */ }
            recognition = null;
        }
    }

    function startListening() {
        var SR = getSpeechRecognition();
        if (!SR || !isFeatureEnabled() || listening) return;

        recognition = new SR();
        recognition.lang = 'id-ID';
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onresult = function(event) {
            var last = event.results.length - 1;
            if (!event.results[last].isFinal) return;
            handleTranscript(event.results[last][0].transcript.trim());
        };

        recognition.onerror = function(event) {
            if (event.error === 'not-allowed') {
                console.warn('[VoiceCommands] mic denied');
                stopListening();
                return;
            }
            if (event.error === 'no-speech' || event.error === 'aborted') return;
            console.warn('[VoiceCommands]', event.error);
        };

        recognition.onend = function() {
            listening = false;
            if (isFeatureEnabled()) {
                restartTimer = setTimeout(startListening, 600);
            }
        };

        try {
            recognition.start();
            listening = true;
            console.log('[VoiceCommands] hands-free listener ON');
        } catch (e) {
            console.warn('[VoiceCommands] start failed:', e);
        }
    }

    function enable() {
        writeStoredEnabled(true);
        updateToggleButton();
        startListening();
        var char = getActiveCharacter();
        var name = char === 'sishin' ? 'Sishin' : 'Shiro';
        showHint('Voice Command ON — ' + name + ' & saudaranya bisa buka aplikasi');
    }

    function disable() {
        writeStoredEnabled(false);
        stopListening();
        updateToggleButton();
        showHint('Voice Command OFF — perintah buka app dinonaktifkan');
    }

    function toggle() {
        if (isFeatureEnabled()) disable();
        else enable();
    }

    function init() {
        updateToggleButton();
        if (!getSpeechRecognition()) {
            console.info('[VoiceCommands] Web Speech API tidak tersedia');
            return;
        }
        if (isFeatureEnabled()) {
            setTimeout(startListening, 1500);
        }
    }

    global.VoiceCommands = {
        enable: enable,
        disable: disable,
        toggle: toggle,
        isEnabled: isFeatureEnabled,
        isWakeListening: isWakeListening,
        updateToggleButton: updateToggleButton,
        dispatchCommand: dispatchCommand,
        parseLocally: function(text) { return OPEN_HINTS.test(text || ''); }
    };

    global.toggleVoiceCommands = toggle;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}(window));
