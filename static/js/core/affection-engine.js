/**
 * Module 2 — Affection Engine (System Awareness)
 * Tracks affection score (0–100) and mood tier (sad | happy)
 */
(function(global) {
    'use strict';

    var SAD_THRESHOLD = 40;
    var score = 50;
    var listeners = [];

    function clamp(value) {
        return Math.max(0, Math.min(100, Math.round(value)));
    }

    function getScore() {
        return score;
    }

    function getTier(value) {
        var s = typeof value === 'number' ? value : score;
        return s < SAD_THRESHOLD ? 'sad' : 'happy';
    }

    function isLowAffection(value) {
        return getTier(value) === 'sad';
    }

    function setScore(value, options) {
        options = options || {};
        if (typeof value !== 'number' || isNaN(value)) return false;

        var next = clamp(value);
        var prev = score;
        var tierChanged = getTier(prev) !== getTier(next);

        if (next === prev && !tierChanged && !options.force) return false;

        score = next;
        var payload = {
            score: score,
            prev: prev,
            tier: getTier(),
            tierChanged: tierChanged
        };

        listeners.forEach(function(fn) {
            try { fn(payload); } catch (e) { console.warn('[AffectionEngine]', e); }
        });
        return true;
    }

    function onChange(fn) {
        if (typeof fn === 'function') listeners.push(fn);
        return function unsubscribe() {
            var i = listeners.indexOf(fn);
            if (i >= 0) listeners.splice(i, 1);
        };
    }

    var AffectionEngine = {
        SAD_THRESHOLD: SAD_THRESHOLD,
        getScore: getScore,
        getTier: getTier,
        isLowAffection: isLowAffection,
        setScore: setScore,
        onChange: onChange
    };

    global.AffectionEngine = AffectionEngine;

    Object.defineProperty(global, 'currentAffection', {
        get: getScore,
        configurable: true
    });
}(window));
