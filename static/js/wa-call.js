/* WhatsApp-style VTuber call overlay */
(function() {
    'use strict';

    function getActiveCharacter() {
        if (window.CharacterState) return CharacterState.get();
        return window.currentCharacter || 'shiro';
    }

    var CHAR_EXPRESSIONS = {
        shiro: '/static/images/expressions/shiro_blush.png',
        sishin: '/static/images/expressions/sishin_blush.png'
    };

    var CHAR_FALLBACK = {
        shiro: '/static/images/shiro.png',
        sishin: '/static/images/sishin.png'
    };

    var CHAR_NAMES = {
        shiro: 'Shiro',
        sishin: 'Sishin'
    };

    var THEME_WA = {
        morning:  { tint: 'rgba(255, 180, 190, 0.22)', accent: '#ff8a9b', glass: 'rgba(0, 0, 0, 0.32)' },
        afternoon:{ tint: 'rgba(100, 160, 230, 0.24)', accent: '#89CFF0', glass: 'rgba(0, 0, 0, 0.34)' },
        evening:  { tint: 'rgba(255, 120, 80, 0.24)', accent: '#ff7e5f', glass: 'rgba(0, 0, 0, 0.36)' },
        night:    { tint: 'rgba(80, 70, 140, 0.28)', accent: '#a78bfa', glass: 'rgba(0, 0, 0, 0.4)' },
        spring:   { tint: 'rgba(220, 160, 220, 0.24)', accent: '#e879f9', glass: 'rgba(0, 0, 0, 0.34)' },
        summer:   { tint: 'rgba(255, 190, 60, 0.2)', accent: '#fbbf24', glass: 'rgba(0, 0, 0, 0.32)' },
        autumn:   { tint: 'rgba(245, 120, 40, 0.24)', accent: '#fb923c', glass: 'rgba(0, 0, 0, 0.36)' },
        winter:   { tint: 'rgba(180, 210, 255, 0.2)', accent: '#93c5fd', glass: 'rgba(0, 0, 0, 0.34)' },
        rain:     { tint: 'rgba(60, 120, 180, 0.26)', accent: '#60a5fa', glass: 'rgba(0, 0, 0, 0.38)' }
    };

    var overlayEl = null;
    var timerInterval = null;
    var callStartTime = null;
    var currentTheme = 'night';

    var callState = {
        speakerOn: true,
        micOn: true,
        moreOpen: false
    };

    window.waCallMicMuted = false;
    window.waCallSpeakerMuted = false;

    function getOverlay() {
        if (!overlayEl) overlayEl = document.getElementById('waCallOverlay');
        return overlayEl;
    }

    function getCurrentTheme() {
        var bg = document.getElementById('bgLayer');
        if (!bg || !bg.className) return currentTheme;
        var m = bg.className.match(/\b(morning|afternoon|evening|night|spring|summer|autumn|winter|rain)\b/);
        return m ? m[1] : (localStorage.getItem('shiro_theme') || 'night');
    }

    function hexToRgb(hex) {
        var h = hex.replace('#', '');
        if (h.length === 3) {
            h = h.split('').map(function(c) { return c + c; }).join('');
        }
        var n = parseInt(h, 16);
        return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
    }

    function applyThemeVars(theme) {
        var el = getOverlay();
        if (!el) return;
        currentTheme = theme || getCurrentTheme();
        var t = THEME_WA[currentTheme] || THEME_WA.night;
        el.setAttribute('data-theme', currentTheme);
        el.style.setProperty('--wa-theme-tint', t.tint);
        el.style.setProperty('--wa-theme-accent', t.accent);
        el.style.setProperty('--wa-glass-bg', t.glass);

        var char = el.getAttribute('data-character') || 'shiro';
        var charAccent = char === 'sishin' ? '#4ade80' : '#ff6b8a';
        var themeRgb = hexToRgb(t.accent);
        var charRgb = hexToRgb(charAccent);

        el.style.setProperty('--wa-border', 'rgba(' + charRgb.r + ',' + charRgb.g + ',' + charRgb.b + ', 0.28)');
        el.style.setProperty('--wa-accent-glow', 'rgba(' + themeRgb.r + ',' + themeRgb.g + ',' + themeRgb.b + ', 0.38)');
        el.style.setProperty('--wa-accent-soft', 'rgba(' + themeRgb.r + ',' + themeRgb.g + ',' + themeRgb.b + ', 0.2)');
    }

    function setAvatarImage(char) {
        var img = document.getElementById('waCallAvatar');
        if (!img) return;
        char = char || getActiveCharacter() || 'shiro';

        var expressionSrc, fallbackSrc;
        if (window.AssetManager) {
            var resolved = AssetManager.resolve({ character: char, context: 'call' });
            expressionSrc = resolved.url;
            fallbackSrc = resolved.fallback;
        } else {
            expressionSrc = CHAR_EXPRESSIONS[char] || CHAR_EXPRESSIONS.shiro;
            fallbackSrc = CHAR_FALLBACK[char] || CHAR_FALLBACK.shiro;
        }

        img.onerror = function() {
            img.onerror = null;
            img.src = fallbackSrc;
        };
        img.src = expressionSrc;
        img.alt = CHAR_NAMES[char] || 'Shiro';
    }

    function applyCharacter(char) {
        var el = getOverlay();
        if (!el) return;
        char = char || getActiveCharacter() || 'shiro';
        if (char !== 'shiro' && char !== 'sishin') char = 'shiro';
        el.setAttribute('data-character', char);
        setAvatarImage(char);

        var nameEl = document.getElementById('waCallName');
        if (nameEl) nameEl.textContent = CHAR_NAMES[char] || 'Shiro';

        applyThemeVars(currentTheme);
    }

    function updateDockIcons() {
        var speakerBtn = document.getElementById('waCallSpeakerBtn');
        var micBtn = document.getElementById('waCallMicBtn');

        if (speakerBtn) {
            speakerBtn.classList.toggle('muted', !callState.speakerOn);
            speakerBtn.innerHTML = callState.speakerOn
                ? '<i class="fas fa-volume-up"></i>'
                : '<i class="fas fa-volume-mute"></i>';
        }

        if (micBtn) {
            micBtn.classList.toggle('muted', !callState.micOn);
            micBtn.innerHTML = callState.micOn
                ? '<i class="fas fa-microphone"></i>'
                : '<i class="fas fa-microphone-slash"></i>';
        }

        window.waCallMicMuted = !callState.micOn;
        window.waCallSpeakerMuted = !callState.speakerOn;
    }

    function closeMoreMenu() {
        callState.moreOpen = false;
        var menu = document.getElementById('waCallMoreMenu');
        var btn = document.getElementById('waCallMoreBtn');
        if (menu) {
            menu.classList.remove('open');
            menu.hidden = true;
        }
        if (btn) btn.classList.remove('active');
    }

    function formatTimer(sec) {
        var m = Math.floor(sec / 60);
        var s = sec % 60;
        return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    }

    function startTimer() {
        stopTimer();
        callStartTime = Date.now();
        var timerEl = document.getElementById('waCallTimer');
        if (timerEl) timerEl.textContent = '00:00';
        timerInterval = setInterval(function() {
            if (!timerEl || !callStartTime) return;
            var elapsed = Math.floor((Date.now() - callStartTime) / 1000);
            timerEl.textContent = formatTimer(elapsed);
        }, 1000);
    }

    function stopTimer() {
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
        callStartTime = null;
    }

    function resetCallState() {
        callState.speakerOn = true;
        callState.micOn = true;
        callState.moreOpen = false;
        window.waCallMicMuted = false;
        window.waCallSpeakerMuted = false;
        closeMoreMenu();
        updateDockIcons();
    }

    window.openWACallOverlay = function() {
        var el = getOverlay();
        if (!el) return;
        resetCallState();
        applyCharacter(getActiveCharacter());
        applyThemeVars(getCurrentTheme());
        el.classList.add('active');
        el.setAttribute('aria-hidden', 'false');
        document.body.classList.add('wa-call-active');
        startTimer();
        updateWACallPttHint(true);
    };

    window.closeWACallOverlay = function() {
        var el = getOverlay();
        if (!el) return;
        el.classList.remove('active', 'speaking');
        el.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('wa-call-active');
        stopTimer();
        closeMoreMenu();
        setWACallSubtitle('');
        updateWACallPttHint(false);
        resetCallState();
    };

    window.syncWACallTheme = function(theme) {
        applyThemeVars(theme || getCurrentTheme());
    };

    window.updateWACallCharacter = function(char) {
        applyCharacter(char);
    };

    window.setWACallSubtitle = function(text) {
        var el = document.getElementById('waCallSubtitle');
        if (!el) return;
        el.textContent = text || '';
        el.classList.toggle('visible', !!text);
        var ov = getOverlay();
        if (typeof window.showVTuberSubtitle === 'function' && (!ov || !ov.classList.contains('active'))) {
            window.showVTuberSubtitle(text);
        }
    };

    window.updateWACallPttHint = function(visible) {
        var el = document.getElementById('waCallPttHint');
        if (!el) return;
        var char = getActiveCharacter();
        var name = CHAR_NAMES[char] || 'Shiro';
        el.innerHTML = 'Tahan <kbd>Space</kbd> bicara dengan <strong>' + name + '</strong>';
        el.classList.toggle('visible', !!(visible && getOverlay() && getOverlay().classList.contains('active') && callState.micOn));
    };

    window.setWACallSpeaking = function(active) {
        var el = getOverlay();
        if (el) el.classList.toggle('speaking', !!active);
    };

    window.endWACall = function() {
        if (typeof window.toggleVTuberMode === 'function' && window.vtuberMode) {
            window.toggleVTuberMode();
        } else {
            closeWACallOverlay();
            if (typeof stopVTuber === 'function') stopVTuber();
        }
    };

    window.waCallToggle = function(action) {
        switch (action) {
            case 'more':
                callState.moreOpen = !callState.moreOpen;
                var menu = document.getElementById('waCallMoreMenu');
                var btn = document.getElementById('waCallMoreBtn');
                if (menu) {
                    menu.hidden = !callState.moreOpen;
                    menu.classList.toggle('open', callState.moreOpen);
                }
                if (btn) btn.classList.toggle('active', callState.moreOpen);
                break;
            case 'speaker':
                callState.speakerOn = !callState.speakerOn;
                updateDockIcons();
                break;
            case 'mic':
                callState.micOn = !callState.micOn;
                updateDockIcons();
                updateWACallPttHint(true);
                if (!callState.micOn && typeof window.endVTuberPTT === 'function') {
                    window.endVTuberPTT();
                }
                break;
            default:
                break;
        }
    };

    document.addEventListener('DOMContentLoaded', function() {
        var orig = window.showVTuberSubtitle;
        window.showVTuberSubtitle = function(text) {
            var ov = getOverlay();
            if (ov && ov.classList.contains('active')) {
                setWACallSubtitle(text);
            } else if (typeof orig === 'function') {
                orig(text);
            }
        };

        document.addEventListener('click', function(e) {
            if (!callState.moreOpen) return;
            var menu = document.getElementById('waCallMoreMenu');
            var btn = document.getElementById('waCallMoreBtn');
            if (menu && btn && !menu.contains(e.target) && !btn.contains(e.target)) {
                closeMoreMenu();
            }
        });
    });
})();
