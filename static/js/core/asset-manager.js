/**
 * Asset Manager — outfits/skins & expression path resolution
 * Checks CharacterState + AffectionEngine before resolving images.
 */
(function(global) {
    'use strict';

    var BASE = '/static/images/';
    var catalog = null;
    var catalogPromise = null;
    var selected = { shiro: 'expressions', sishin: 'expressions' };
    var LIVE2D_IDS = {
        shiro: ['live2d', 'live2d_hiyori', 'live2d_haru', 'live2d_custom'],
        sishin: ['live2d_custom', 'live2d_sishin', 'live2d_versi_baru', 'live2d_hiyori', 'live2d_haru', 'live2d']
    };

    function storageKey() {
        var uid = (global.currentAuthUser && global.currentAuthUser.user_id) || 'guest';
        return 'shiro_wardrobe_' + uid;
    }

    function loadSelection() {
        try {
            var raw = localStorage.getItem(storageKey());
            if (raw) {
                var parsed = JSON.parse(raw);
                if (parsed.shiro) {
                    var sh = parsed.shiro;
                    if (sh === 'live2d' || sh === 'live2d_hiyori') sh = 'live2d_haru';
                    selected.shiro = sh;
                }
                if (parsed.sishin) {
                    var s = parsed.sishin;
                    if (s === 'live2d_sishin' || s === 'live2d_versi_baru') s = 'live2d_custom';
                    if (s === 'live2d' || s === 'live2d_haru') s = 'live2d_hiyori';
                    selected.sishin = s;
                }
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

    function isLive2DOutfitId(char, outfitId) {
        char = normalizeChar(char);
        var ids = LIVE2D_IDS[char] || [];
        return ids.indexOf(outfitId) >= 0 || (outfitId && outfitId.indexOf('live2d') === 0);
    }

    function findDefaultOutfit(char) {
        if (!catalog || !catalog[char]) return null;
        var list = catalog[char];
        for (var i = 0; i < list.length; i++) {
            if (list[i].id === 'expressions') return list[i];
        }
        for (var j = 0; j < list.length; j++) {
            if (list[j].mode === 'png') return list[j];
        }
        return list[0] || null;
    }

    function migrateWardrobeIds() {
        if (selected.shiro === 'live2d' || selected.shiro === 'live2d_hiyori') {
            selected.shiro = 'live2d_haru';
        }
        if (selected.sishin === 'live2d_versi_baru' || selected.sishin === 'live2d_sishin') {
            selected.sishin = 'live2d_custom';
        }
        if (selected.sishin === 'live2d' || selected.sishin === 'live2d_haru') {
            selected.sishin = 'live2d_hiyori';
        }
        saveSelection();
    }

    function applyBootMigrations() {
        migrateWardrobeIds();
    }

    function revertLive2DToExpressions(char) {
        char = normalizeChar(char);
        selected[char] = 'expressions';
        saveSelection();
        if (typeof global.deactivateLive2DFromWardrobe === 'function') {
            global.deactivateLive2DFromWardrobe(char);
        } else if (typeof global.applyHomeAvatarExpression === 'function') {
            global.applyHomeAvatarExpression(char, getAffection());
        }
    }

    function isLive2DMode(char) {
        return getOutfitMode(char, getSelectedOutfit(char)) === 'live2d';
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

        if (outfit.mode === 'live2d') {
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
        if (catalogPromise) return catalogPromise;

        catalogPromise = fetch('/api/wardrobe/catalog')
            .then(function(r) { return r.json(); })
            .then(function(data) {
                catalog = data.outfits || null;
                ['shiro', 'sishin'].forEach(function(char) {
                    if (!catalog || !catalog[char]) return;
                    if (char === 'shiro' && (selected.shiro === 'live2d' || selected.shiro === 'live2d_hiyori')) {
                        selected.shiro = 'live2d_haru';
                    }
                    if (char === 'sishin') {
                        if (selected.sishin === 'live2d_sishin' || selected.sishin === 'live2d_versi_baru') {
                            selected.sishin = 'live2d_custom';
                        }
                        if (selected.sishin === 'live2d' || selected.sishin === 'live2d_haru') {
                            selected.sishin = 'live2d_hiyori';
                        }
                    }
                    var valid = catalog[char].some(function(o) { return o.id === selected[char]; });
                    if (!valid) {
                        var fallback = findDefaultOutfit(char);
                        selected[char] = fallback ? fallback.id : catalog[char][0].id;
                        saveSelection();
                    }
                });
                applyBootMigrations();
                return catalog;
            })
            .catch(function() {
                catalog = null;
                catalogPromise = null;
                return null;
            });

        return catalogPromise;
    }

    function ensureCatalog() {
        return catalog ? Promise.resolve(catalog) : fetchCatalog();
    }

    loadSelection();

    global.AssetManager = {
        resolve: resolve,
        fetchCatalog: fetchCatalog,
        ensureCatalog: ensureCatalog,
        getCatalog: getCatalog,
        getSelectedOutfit: getSelectedOutfit,
        setOutfit: setOutfit,
        buildUrl: buildUrl,
        getPreviewUrl: getPreviewUrl,
        getOutfitMode: getOutfitMode,
        isLive2DMode: isLive2DMode,
        applyBootMigrations: applyBootMigrations,
        revertLive2DToExpressions: revertLive2DToExpressions
    };
}(window));
