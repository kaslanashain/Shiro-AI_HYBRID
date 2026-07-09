/**
 * Wow UI — quotes, mood chip, affection sync, companion theme
 */
(function(global) {
    'use strict';

    var QUOTES = {
        shiro: [
            'Hari ini akan indah, seperti senyummu.',
            'Shiro selalu di sini untuk Kakak Shin~',
            'Ehehe~ jangan lupa istirahat ya, Sayang.',
            'Kalau kamu senang, Shiro juga senang.',
            'Peluk virtual dari Shiro~ muach!'
        ],
        sishin: [
            'Kak, main bareng Sishin yuk!',
            'Hehe~ hari ini seru banget!',
            'Sishin kangen ngobrol sama Kak~',
            'Jangan sedih ya, Sishin temenin!',
            'Yay~ Kakak Shin yang terbaik!'
        ]
    };

    var quoteTimer = null;
    var quoteIndex = 0;

    function getChar() {
        if (global.CharacterState) return CharacterState.get();
        return global.currentCharacter || 'shiro';
    }

    function applyCompanionTheme(char) {
        var app = document.getElementById('app');
        if (!app) return;
        app.classList.remove('companion-shiro', 'companion-sishin');
        app.classList.add(char === 'sishin' ? 'companion-sishin' : 'companion-shiro');
    }

    function updateMoodChip(score) {
        var chip = document.getElementById('moodChip');
        if (!chip) return;
        var emoji, text;
        if (score < 20) { emoji = '😠'; text = 'Posesif'; }
        else if (score >= 75) { emoji = '😍'; text = 'Bucin'; }
        else if (score >= 50) { emoji = '😊'; text = 'Bahagia'; }
        else { emoji = '😐'; text = 'Biasa'; }
        chip.innerHTML = '<span class="mood-emoji">' + emoji + '</span><span class="mood-label">' + text + '</span>';
    }

    function updateHpVisual(score, level) {
        var bar = document.getElementById('hpBar');
        var pct = document.getElementById('hpPercent');
        var aff = document.getElementById('affectionDisplay');
        var lvl = document.getElementById('levelDisplay');
        var safe = Math.max(0, Math.min(100, Math.round(score)));
        if (bar) bar.style.width = safe + '%';
        if (pct) pct.textContent = String(safe);
        if (aff) aff.textContent = String(safe);
        if (lvl && typeof level === 'number') lvl.textContent = String(level);
    }

    function setQuote(char, index, animate) {
        var box = document.querySelector('.quote-box');
        var textEl = document.querySelector('.quote-text');
        if (!textEl) return;
        var list = QUOTES[char === 'sishin' ? 'sishin' : 'shiro'] || QUOTES.shiro;
        quoteIndex = ((index % list.length) + list.length) % list.length;

        function applyText() {
            textEl.textContent = list[quoteIndex];
            if (box) box.classList.remove('quote-fade');
        }

        if (animate && box) {
            box.classList.add('quote-fade');
            setTimeout(applyText, 280);
        } else {
            applyText();
        }
    }

    function startQuoteRotation() {
        if (quoteTimer) clearInterval(quoteTimer);
        quoteTimer = setInterval(function() {
            var char = getChar();
            setQuote(char, quoteIndex + 1, true);
        }, 12000);
    }

    function onStatusUpdate(status) {
        if (!status) return;
        var score = status.affection != null ? status.affection : 50;
        var level = status.level || 1;
        updateMoodChip(score);
        updateHpVisual(score, level);
    }

    function onCharacterChange(char) {
        char = char === 'sishin' ? 'sishin' : 'shiro';
        applyCompanionTheme(char);
        setQuote(char, 0, true);
    }

    function initEntrance() {
        var home = document.getElementById('homeScreen');
        if (!home) return;
        requestAnimationFrame(function() {
            home.classList.add('wow-ready');
        });
    }

    function wire() {
        applyCompanionTheme(getChar());
        setQuote(getChar(), 0, false);
        startQuoteRotation();
        initEntrance();

        if (global.CharacterState) {
            CharacterState.onChange(function(char) {
                onCharacterChange(char);
            });
        }

        if (global.AffectionEngine) {
            AffectionEngine.onChange(function(evt) {
                updateMoodChip(evt.score);
                updateHpVisual(evt.score, document.getElementById('levelDisplay') ? parseInt(document.getElementById('levelDisplay').textContent, 10) || 1 : 1);
            });
        }

        document.addEventListener('DOMContentLoaded', function() {
            if (typeof refreshStatus === 'function') refreshStatus();
        });
    }

    global.WowUI = {
        onStatusUpdate: onStatusUpdate,
        onCharacterChange: onCharacterChange,
        setQuote: setQuote
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', wire);
    } else {
        wire();
    }
}(window));
