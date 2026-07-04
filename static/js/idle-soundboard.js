/**
 * Idle Soundboard — random natural voice snippets when user is idle
 * Respects character, affection tier, and avoids overlap with speech.
 */
(function(global) {
    'use strict';

    var IDLE_MS = 90000;
    var CHECK_MS = 45000;
    var COOLDOWN_MS = 120000;
    var lastActivity = Date.now();
    var lastPlayedAt = 0;
    var playing = false;
    var timer = null;

    var SNIPPETS = {
        shiro: {
            happy: ['Ehehe~', 'Fufu~', 'Hmm... senangnya~', 'Sayang~', '*giggles* Hehe~'],
            sad: ['Huff...', 'Sayang...', '*sigh* ...', 'Hmm...'],
            normal: ['Hmm~', 'Ehe...', '*yawn* ... maaf, ngantuk~', 'Fufu~']
        },
        sishin: {
            happy: ['Hehe~', 'Yay~!', 'Ehehe!', 'Kak~!', '*giggles*'],
            sad: ['Huft...', 'Kak...', '*sigh* ...', 'Hmm...'],
            normal: ['Hmm?', 'Ehe~', '*yawn* Ngantuk...', 'La la~']
        }
    };

    function bumpActivity() {
        lastActivity = Date.now();
        if (global.RandomEvents && RandomEvents.bumpActivity) RandomEvents.bumpActivity();
    }

    function getSnapshot() {
        if (global.SystemAwareness) return SystemAwareness.snapshot();
        return {
            character: global.currentCharacter || 'shiro',
            tier: (global.AffectionEngine && AffectionEngine.getTier()) || 'happy',
            isLowAffection: global.AffectionEngine && AffectionEngine.isLowAffection()
        };
    }

    function isBlocked() {
        if (playing) return true;
        if (Date.now() - lastPlayedAt < COOLDOWN_MS) return true;
        if (global.vtuberMode) return true;
        if (Date.now() - lastActivity < IDLE_MS) return true;
        var chat = document.getElementById('chatScreen');
        if (chat && chat.style.display === 'flex') return true;
        var avatar = document.getElementById('homeAvatar');
        if (avatar && avatar.classList.contains('speaking')) return true;
        return false;
    }

    function pickSnippet(char, tier) {
        var pools = SNIPPETS[char] || SNIPPETS.shiro;
        var pool = pools[tier] || pools.normal || pools.happy;
        return pool[Math.floor(Math.random() * pool.length)];
    }

    function playIdleSnippet() {
        if (isBlocked()) return;
        if (Math.random() > 0.55) return;

        var snap = getSnapshot();
        var text = pickSnippet(snap.character, snap.tier === 'sad' ? 'sad' : (snap.tier === 'happy' ? 'happy' : 'normal'));
        if (!text || typeof global.putarAudio !== 'function') return;

        playing = true;
        lastPlayedAt = Date.now();
        console.log('[IdleSoundboard]', snap.character, text);

        var avatar = document.getElementById('homeAvatar');
        if (avatar) avatar.classList.add('speaking');

        global.putarAudio(text, snap.character);

        setTimeout(function() {
            playing = false;
        }, 4000);
    }

    function start() {
        ['mousedown', 'keydown', 'touchstart', 'scroll'].forEach(function(ev) {
            document.addEventListener(ev, bumpActivity, { passive: true });
        });
        timer = setInterval(playIdleSnippet, CHECK_MS);
    }

    global.IdleSoundboard = {
        start: start,
        bumpActivity: bumpActivity
    };

    document.addEventListener('DOMContentLoaded', start);
}(window));
