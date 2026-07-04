/**
 * Asset Manager — outfits/skins & expression path resolution
 * Checks CharacterState + AffectionEngine before resolving images.
 */
(function(global) {
    'use strict';

    var BASE = '/static/images/';
    var catalog = null;
    var selected = { shiro: 'expressions', sishin: 'expressions' };

    function storageKey() {
        var uid = (global.currentAuthUser && global.currentAuthUser.user_id) || 'guest';
        return 'shiro_wardrobe_' + uid;
    }

    function loadSelection() {
        try {
            var raw = localStorage.getItem(storageKey());
            if (raw) {
                var parsed = JSON.parse(raw);
                if (parsed.shiro) selected.shiro = parsed.shiro;
                if (parsed.sishin) selected.sishin = parsed.sishin;
            }
        } catch (e) { /* keep defaults */ }
    }

    function saveSelection() {
        localStorage.setItem(storageKey(), JSON.stringify(selected));
    }

    function normalizeChar(char) {
        if (global.CharacterState) return CharacterState.normalize(char);
        return char === 'sishin' ? 'sishin' : 'shiro';
    }

    function getAffection(value) {
        if (typeof value === 'number') return value;
        if (global.AffectionEngine) return AffectionEngine.getScore();
        return typeof global.currentAffection === 'number' ? global.currentAffection : 50;
    }

    function getTier(affection) {
        if (global.AffectionEngine) return AffectionEngine.getTier(affection);
        return (affection != null ? affection : 50) < 40 ? 'sad' : 'happy';
    }

    function buildUrl(folder, filename) {
        if (!filename) return null;
        if (filename.indexOf('http://') === 0 || filename.indexOf('https://') === 0) return filename;
        if (filename.indexOf('/static/') === 0) return filename;

        if (filename.indexOf('expressions/') === 0) {
            return BASE + filename;
        }
        if (filename.indexOf('live2d/') === 0) {
            return '/static/' + filename;
        }

        /* Root portraits live directly under /static/images/ */
        if (!folder || folder === 'root' || folder === 'images' || folder === '.') {
            return BASE + filename;
        }

        if (folder === 'expressions') {
            return BASE + 'expressions/' + filename;
        }

        return BASE + folder + '/' + filename;
    }

    function getPreviewUrl(char, outfit) {
        if (!outfit) return BASE + (char === 'sishin' ? 'sishin.png' : 'shiro.png');
        if (outfit.preview) return outfit.preview;

        var files = outfit.files || {};
        var previewFile = files.preview || files.happy || files.fallback;
        if (previewFile) return buildUrl(outfit.folder, previewFile);

        return BASE + (char === 'sishin' ? 'sishin.png' : 'shiro.png');
    }

    function getOutfitMode(char, outfitId) {
        var outfit = getOutfit(char, outfitId);
        return (outfit && outfit.mode) || 'png';
    }

    function isLive2DMode(char) {
        var id = getSelectedOutfit(char);
        if (id === 'live2d') return true;
        return getOutfitMode(char, id) === 'live2d';
    }

    function getOutfit(char, outfitId) {
        char = normalizeChar(char);
        outfitId = outfitId || selected[char] || 'expressions';
        if (!catalog || !catalog[char]) return null;
        for (var i = 0; i < catalog[char].length; i++) {
            if (catalog[char][i].id === outfitId) return catalog[char][i];
        }
        return catalog[char][0] || null;
    }

    function resolve(options) {
        options = options || {};
        var char = normalizeChar(options.character || (global.CharacterState && CharacterState.get()));
        var context = options.context || 'home';
        var affection = getAffection(options.affection);
        var tier = options.tier || getTier(affection);
        var outfit = getOutfit(char, options.outfitId);

        if (!outfit) {
            return fallbackLegacy(char, tier);
        }

        var files = outfit.files || {};
        var fileKey = tier;
        if (context === 'call') fileKey = 'blush';
        if (!files[fileKey]) fileKey = tier === 'sad' ? 'sad' : 'happy';

        var filename = files[fileKey] || files.happy || files.fallback;
        var url = buildUrl(outfit.folder, filename);
        var fallbackUrl = buildUrl(
            outfit.folder,
            files.fallback || (char === 'sishin' ? 'sishin.png' : 'shiro.png')
        );

        return {
            url: url,
            fallback: fallbackUrl,
            tier: tier,
            outfitId: outfit.id,
            character: char,
            context: context
        };
    }

    function fallbackLegacy(char, tier) {
        var paths = {
            shiro: {
                sad: BASE + 'expressions/shiro_sad.png',
                happy: BASE + 'expressions/shiro_happy.png',
                fallback: BASE + 'shiro.png',
                blush: BASE + 'expressions/shiro_blush.png'
            },
            sishin: {
                sad: BASE + 'expressions/sishin_sad.png',
                happy: BASE + 'expressions/sishin_normal.png',
                fallback: BASE + 'sishin.png',
                blush: BASE + 'expressions/sishin_blush.png'
            }
        };
        var p = paths[char] || paths.shiro;
        return {
            url: tier === 'sad' ? p.sad : p.happy,
            fallback: p.fallback,
            tier: tier,
            outfitId: 'legacy',
            character: char,
            context: 'home'
        };
    }

    function getSelectedOutfit(char) {
        return selected[normalizeChar(char)];
    }

    function setOutfit(char, outfitId) {
        char = normalizeChar(char);
        selected[char] = outfitId;
        saveSelection();

        var outfit = getOutfit(char, outfitId);
        var mode = (outfit && outfit.mode) || 'png';

        if (mode === 'live2d') {
            if (typeof global.activateLive2DFromWardrobe === 'function') {
                global.activateLive2DFromWardrobe(char);
            }
        } else {
            if (typeof global.deactivateLive2DFromWardrobe === 'function') {
                global.deactivateLive2DFromWardrobe(char);
            }
            if (typeof global.applyHomeAvatarExpression === 'function') {
                global.applyHomeAvatarExpression(char, getAffection());
            }
        }

        if (global.SystemAwareness && SystemAwareness.canApplyCallOverlay() &&
            typeof global.updateWACallCharacter === 'function') {
            global.updateWACallCharacter(char);
        }
    }

    function getCatalog(char) {
        if (!catalog) return [];
        char = normalizeChar(char);
        return catalog[char] ? catalog[char].slice() : [];
    }

    function fetchCatalog() {
        return fetch('/api/wardrobe/catalog')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                catalog = data.outfits || null;
                return catalog;
            })
            .catch(function() {
                catalog = null;
                return null;
            });
    }

    loadSelection();

    global.AssetManager = {
        resolve: resolve,
        fetchCatalog: fetchCatalog,
        getCatalog: getCatalog,
        getSelectedOutfit: getSelectedOutfit,
        setOutfit: setOutfit,
        buildUrl: buildUrl,
        getPreviewUrl: getPreviewUrl,
        getOutfitMode: getOutfitMode,
        isLive2DMode: isLive2DMode
    };
}(window));
