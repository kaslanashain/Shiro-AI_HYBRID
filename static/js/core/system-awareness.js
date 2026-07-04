/**
 * Module 2 — System Awareness (facade)
 * Unified read API for character + affection before triggering UI systems
 */
(function(global) {
    'use strict';

    function requireModules() {
        return global.CharacterState && global.AffectionEngine;
    }

    function snapshot() {
        if (!requireModules()) {
            return {
                character: global.currentCharacter || 'shiro',
                affection: typeof global.currentAffection === 'number' ? global.currentAffection : 50,
                tier: 'happy',
                isLowAffection: false
            };
        }
        return {
            character: CharacterState.get(),
            affection: AffectionEngine.getScore(),
            tier: AffectionEngine.getTier(),
            isLowAffection: AffectionEngine.isLowAffection()
        };
    }

    function isActiveCharacter(char) {
        if (!requireModules()) {
            return (global.currentCharacter || 'shiro') === (char === 'sishin' ? 'sishin' : 'shiro');
        }
        return CharacterState.get() === CharacterState.normalize(char);
    }

    function hasMinimumAffection(minScore) {
        if (!requireModules()) return true;
        return AffectionEngine.getScore() >= minScore;
    }

    function canApplyHomeExpression() {
        return !!document.getElementById('homeAvatar');
    }

    function canApplyCallOverlay() {
        var overlay = document.getElementById('waCallOverlay');
        return overlay && overlay.classList.contains('active');
    }

    global.SystemAwareness = {
        snapshot: snapshot,
        isActiveCharacter: isActiveCharacter,
        hasMinimumAffection: hasMinimumAffection,
        canApplyHomeExpression: canApplyHomeExpression,
        canApplyCallOverlay: canApplyCallOverlay
    };
}(window));
