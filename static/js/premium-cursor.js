/**
 * Premium Cursor — theme + character aware luxury pointer FX
 */
(function(global) {
    'use strict';

    var THEMES = ['morning', 'afternoon', 'evening', 'night', 'spring', 'summer', 'autumn', 'winter', 'rain'];
    var root = null;
    var core = null;
    var ring = null;
    var glow = null;
    var mouseX = -200;
    var mouseY = -200;
    var curX = -200;
    var curY = -200;
    var lastSpark = 0;
    var currentTheme = 'night';
    var enabled = true;

    function ensureLayers() {
        if (root) return;
        root = document.createElement('div');
        root.id = 'premiumCursor';
        root.className = 'premium-cursor';
        root.setAttribute('aria-hidden', 'true');

        glow = document.createElement('div');
        glow.className = 'pc-layer pc-glow';
        ring = document.createElement('div');
        ring.className = 'pc-layer pc-ring';
        core = document.createElement('div');
        core.className = 'pc-layer pc-core';

        root.appendChild(glow);
        root.appendChild(ring);
        root.appendChild(core);
        document.body.appendChild(root);
        document.body.classList.add('premium-cursor-on');
    }

    function setTheme(theme) {
        currentTheme = theme || 'night';
        var body = document.body;
        THEMES.forEach(function(t) {
            body.classList.remove('cursor-theme-' + t);
        });
        body.classList.add('cursor-theme-' + currentTheme);
    }

    function setCharacter(char) {
        var body = document.body;
        body.classList.remove('cursor-char-shiro', 'cursor-char-sishin');
        body.classList.add(char === 'sishin' ? 'cursor-char-sishin' : 'cursor-char-shiro');
    }

    function spawnTrail(x, y) {
        var dot = document.createElement('div');
        dot.className = 'pc-trail-dot';
        var size = 3 + Math.random() * 4;
        dot.style.width = size + 'px';
        dot.style.height = size + 'px';
        dot.style.left = x + 'px';
        dot.style.top = y + 'px';
        dot.style.background = 'var(--pc-primary, rgba(255,107,138,0.6))';
        document.body.appendChild(dot);
        setTimeout(function() { if (dot.parentNode) dot.remove(); }, 600);
    }

    function spawnSpark(x, y) {
        var spark = document.createElement('div');
        spark.className = 'pc-spark';
        var size = 2 + Math.random() * 5;
        spark.style.width = size + 'px';
        spark.style.height = size + 'px';
        spark.style.left = x + 'px';
        spark.style.top = y + 'px';
        spark.style.background = 'var(--pc-core, #fff)';
        spark.style.boxShadow = '0 0 8px var(--pc-primary)';
        document.body.appendChild(spark);
        setTimeout(function() { if (spark.parentNode) spark.remove(); }, 700);
    }

    function clickBurst(x, y) {
        if (!enabled || !root) return;
        var count = 8;
        for (var i = 0; i < count; i++) {
            var p = document.createElement('div');
            p.className = 'pc-click-burst';
            p.style.left = x + 'px';
            p.style.top = y + 'px';
            var angle = (Math.PI * 2 * i) / count;
            var dist = 24 + Math.random() * 20;
            p.style.setProperty('--bx', Math.cos(angle) * dist + 'px');
            p.style.setProperty('--by', Math.sin(angle) * dist + 'px');
            document.body.appendChild(p);
            setTimeout(function(el) {
                return function() { if (el.parentNode) el.remove(); };
            }(p), 700);
        }
        root.classList.add('is-click');
        setTimeout(function() { if (root) root.classList.remove('is-click'); }, 180);
    }

    function tick() {
        if (!enabled || !core) {
            requestAnimationFrame(tick);
            return;
        }
        curX += (mouseX - curX) * 0.22;
        curY += (mouseY - curY) * 0.22;
        var transform = 'translate3d(' + curX + 'px,' + curY + 'px,0)';
        core.style.transform = transform;
        ring.style.transform = transform;
        glow.style.transform = transform;

        var now = performance.now();
        if (now - lastSpark > 70 && (Math.abs(mouseX - curX) > 2 || Math.abs(mouseY - curY) > 2)) {
            lastSpark = now;
            if (Math.random() > 0.55) spawnTrail(curX, curY);
            if (Math.random() > 0.82) spawnSpark(curX, curY);
        }
        requestAnimationFrame(tick);
    }

    function bindInteractive() {
        var selector = 'button, input, textarea, a, .action-btn, .switch-btn, .avatar, .fab-chat, .wardrobe-card, .theme-option';
        document.addEventListener('mouseover', function(e) {
            if (!root) return;
            var t = e.target;
            if (t && t.closest && t.closest(selector)) {
                root.classList.add('is-hover');
            }
        }, true);
        document.addEventListener('mouseout', function(e) {
            if (!root) return;
            var t = e.target;
            if (t && t.closest && t.closest(selector)) {
                root.classList.remove('is-hover');
            }
        }, true);
    }

    function init() {
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            enabled = false;
            return;
        }
        if ('ontouchstart' in window && window.innerWidth < 1024) {
            enabled = false;
            return;
        }

        ensureLayers();
        setTheme(localStorage.getItem('shiro_theme') || 'night');

        if (global.CharacterState) {
            setCharacter(CharacterState.get());
            CharacterState.onChange(function(char) { setCharacter(char); });
        }

        document.addEventListener('mousemove', function(e) {
            mouseX = e.clientX;
            mouseY = e.clientY;
        });

        document.addEventListener('mousedown', function(e) {
            clickBurst(e.clientX, e.clientY);
        });

        document.addEventListener('mouseleave', function() {
            if (root) root.style.opacity = '0';
        });
        document.addEventListener('mouseenter', function() {
            if (root) root.style.opacity = '1';
        });

        bindInteractive();
        requestAnimationFrame(tick);
    }

    global.PremiumCursor = {
        setTheme: setTheme,
        setCharacter: setCharacter,
        init: init
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}(window));
