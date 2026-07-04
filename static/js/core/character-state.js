/**
 * Module 2 — Character State (System Awareness)
 * Single source of truth for the active companion: shiro | sishin
 */
(function(global) {
    'use strict';

    var current = 'shiro';
    var listeners = [];

    function normalize(char) {
        return char === 'sishin' ? 'sishin' : 'shiro';
    }

    function get() {
        return current;
    }

    function set(char) {
        char = normalize(char);
        if (char === current) return false;
        var prev = current;
        current = char;
        listeners.forEach(function(fn) {
            try { fn(char, prev); } catch (e) { console.warn('[CharacterState]', e); }
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

    var CharacterState = {
        normalize: normalize,
        get: get,
        set: set,
        onChange: onChange
    };

    global.CharacterState = CharacterState;

    /* Legacy compatibility for schedule.js, story.js, wa-call.js, etc. */
    Object.defineProperty(global, 'currentCharacter', {
        get: get,
        set: set,
        configurable: true
    });
}(window));
