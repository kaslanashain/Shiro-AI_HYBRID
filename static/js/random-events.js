/**
 * Random Events Scheduler — proactive greetings & check-ins
 * Uses SystemAwareness (character + affection) before triggering.
 */
(function(global) {
    'use strict';

    var lastActivity = Date.now();
    var lastFiredAt = 0;
    var pollTimer = null;
    var idleTimer = null;
    var MIN_GAP_MS = 120000;

    function getActiveCharacter() {
        if (global.SystemAwareness) return SystemAwareness.snapshot().character;
        if (global.CharacterState) return CharacterState.get();
        return global.currentCharacter || 'shiro';
    }

    function getIdleMinutes() {
        return (Date.now() - lastActivity) / 60000;
    }

    function bumpActivity() {
        lastActivity = Date.now();
    }

    function canFire() {
        if (Date.now() - lastFiredAt < MIN_GAP_MS) return false;
        if (global.vtuberMode && global.vtuberPttActive) return false;
        var chat = document.getElementById('chatScreen');
        if (chat && chat.style.display === 'flex') return false;
        return true;
    }

    function deliverProactive(data, source) {
        if (!data || !data.pesan) return;
        lastFiredAt = Date.now();
        var karakter = data.karakter || getActiveCharacter();
        if (global.SystemAwareness && !SystemAwareness.isActiveCharacter(karakter)) {
            karakter = getActiveCharacter();
        }
        console.log('[RandomEvents]', source, karakter, data.pesan.slice(0, 40));
        if (typeof global.showNotification === 'function') {
            global.showNotification(karakter, data.pesan);
        }
        if (typeof global.addMessage === 'function') {
            global.addMessage(data.pesan, karakter);
        }
        if (typeof global.putarAudio === 'function') {
            global.putarAudio(data.pesan, karakter);
        }
    }

    function fetchJson(url) {
        var fn = global.apiFetch || fetch;
        return fn(url).then(function(r) { return r.json(); });
    }

    function pollInitiative() {
        if (!canFire()) return;
        fetchJson('/initiative')
            .then(function(data) {
                if (data && data.pesan) deliverProactive(data, 'initiative');
            })
            .catch(function() {});
    }

    function pollScheduledEvents() {
        if (!canFire()) return;
        fetchJson('/event')
            .then(function(data) {
                if (data && data.pesan) deliverProactive(data, 'event');
            })
            .catch(function() {});
    }

    function pollRandomCheckin() {
        if (!canFire()) return;
        var char = getActiveCharacter();
        var idle = Math.round(getIdleMinutes() * 10) / 10;
        if (idle < 2) return;
        var url = '/api/random-checkin?karakter=' + encodeURIComponent(char) +
            '&idle_minutes=' + encodeURIComponent(idle);
        fetchJson(url)
            .then(function(data) {
                if (data && data.pesan) deliverProactive(data, 'random_checkin');
            })
            .catch(function() {});
    }

    function tickIdleCheckin() {
        pollRandomCheckin();
    }

    function start() {
        bumpActivity();
        ['mousedown', 'keydown', 'touchstart', 'scroll', 'click'].forEach(function(ev) {
            document.addEventListener(ev, bumpActivity, { passive: true });
        });

        setTimeout(pollInitiative, 8000);
        setTimeout(pollScheduledEvents, 12000);
        setTimeout(pollRandomCheckin, 180000);

        pollTimer = setInterval(function() {
            pollInitiative();
            pollScheduledEvents();
        }, 300000);

        idleTimer = setInterval(tickIdleCheckin, 90000);
    }

    global.RandomEvents = {
        start: start,
        bumpActivity: bumpActivity,
        getIdleMinutes: getIdleMinutes,
        pollRandomCheckin: pollRandomCheckin
    };

    document.addEventListener('DOMContentLoaded', start);
}(window));
