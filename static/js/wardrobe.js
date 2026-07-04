/**
 * Wardrobe — outfit selection, thumbnails, Live2D activation
 */
(function(global) {
    'use strict';

    var PNG_FALLBACK = {
        shiro: '/static/images/shiro.png',
        sishin: '/static/images/sishin.png'
    };

    function getActiveCharacter() {
        if (global.CharacterState) return CharacterState.get();
        return global.currentCharacter || 'shiro';
    }

    function normalizeChar(char) {
        return char === 'sishin' ? 'sishin' : 'shiro';
    }

    function getPreviewUrl(char, outfit) {
        if (global.AssetManager && AssetManager.getPreviewUrl) {
            return AssetManager.getPreviewUrl(char, outfit);
        }
        var files = outfit.files || {};
        var name = files.happy || files.fallback || (char === 'sishin' ? 'sishin.png' : 'shiro.png');
        if (name.indexOf('/') >= 0) return '/static/images/' + name.replace(/^\/+/, '');
        if (outfit.folder === 'expressions') return '/static/images/expressions/' + name;
        return PNG_FALLBACK[normalizeChar(char)];
    }

    function createWardrobeCard(char, outfit, isSelected) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'wardrobe-card' + (isSelected ? ' active' : '');
        if (outfit.mode === 'live2d') btn.classList.add('wardrobe-card-live2d');

        var previewUrl = getPreviewUrl(char, outfit);
        var fallbackUrl = PNG_FALLBACK[normalizeChar(char)];

        var img = document.createElement('img');
        img.className = 'wardrobe-preview';
        img.alt = outfit.label || '';
        img.draggable = false;
        img.src = previewUrl;
        img.onerror = function() {
            img.onerror = null;
            img.src = fallbackUrl;
        };

        var label = document.createElement('span');
        label.className = 'wardrobe-label';
        label.textContent = outfit.label || outfit.id;

        if (outfit.mode === 'live2d') {
            var badge = document.createElement('span');
            badge.className = 'wardrobe-badge-live2d';
            badge.textContent = 'Live2D';
            btn.appendChild(badge);
        }

        btn.appendChild(img);
        btn.appendChild(label);

        btn.onclick = function() {
            if (!global.AssetManager) return;
            AssetManager.setOutfit(char, outfit.id);
            renderGrid(char);
            if (outfit.mode === 'live2d') {
                closeWardrobe();
            }
        };

        return btn;
    }

    function renderGrid(char) {
        var grid = document.getElementById('wardrobeGrid');
        if (!grid || !global.AssetManager) return;

        char = normalizeChar(char);
        var outfits = AssetManager.getCatalog(char);
        var selected = AssetManager.getSelectedOutfit(char);

        grid.innerHTML = '';
        if (!outfits.length) {
            grid.innerHTML = '<p class="wardrobe-empty">Memuat wardrobe...</p>';
            return;
        }

        outfits.forEach(function(outfit) {
            grid.appendChild(createWardrobeCard(char, outfit, outfit.id === selected));
        });
    }

    function openWardrobe() {
        var modal = document.getElementById('wardrobeModal');
        if (!modal) return;
        modal.classList.add('active');

        var char = normalizeChar(getActiveCharacter());
        var label = document.getElementById('wardrobeCharLabel');
        if (label) label.textContent = char === 'sishin' ? 'Sishin' : 'Shiro';

        if (global.AssetManager) {
            AssetManager.fetchCatalog().then(function() {
                renderGrid(char);
            });
        }
    }

    function closeWardrobe() {
        var modal = document.getElementById('wardrobeModal');
        if (modal) modal.classList.remove('active');
    }

    function switchWardrobeTab(char) {
        char = normalizeChar(char);
        var tabs = document.querySelectorAll('.wardrobe-tab');
        tabs.forEach(function(t) {
            t.classList.toggle('active', t.getAttribute('data-char') === char);
        });
        var label = document.getElementById('wardrobeCharLabel');
        if (label) label.textContent = char === 'sishin' ? 'Sishin' : 'Shiro';
        renderGrid(char);
    }

    global.openWardrobe = openWardrobe;
    global.closeWardrobe = closeWardrobe;
    global.switchWardrobeTab = switchWardrobeTab;

    document.addEventListener('DOMContentLoaded', function() {
        if (global.AssetManager) AssetManager.fetchCatalog();
        if (global.CharacterState) {
            CharacterState.onChange(function(char) {
                var modal = document.getElementById('wardrobeModal');
                if (modal && modal.classList.contains('active')) {
                    renderGrid(normalizeChar(char));
                }
            });
        }
    });
}(window));
