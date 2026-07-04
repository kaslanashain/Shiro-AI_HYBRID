/* Auth — login/register multi-user */
(function() {
    'use strict';

    window.currentAuthUser = null;

    window.apiFetch = function(url, options) {
        options = options || {};
        options.credentials = 'include';
        if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
            options.headers = options.headers || {};
            if (!options.headers['Content-Type']) {
                options.headers['Content-Type'] = 'application/json';
            }
            options.body = JSON.stringify(options.body);
        }
        return fetch(url, options);
    };

    function updateAuthUI(user) {
        window.currentAuthUser = user;
        var chip = document.getElementById('authUserChip');
        var nameEl = document.querySelector('.user-name');
        if (!chip) return;

        if (user && !user.guest) {
            chip.innerHTML = '<i class="fas fa-user"></i> ' + (user.display_name || user.username);
            chip.title = 'Klik untuk logout';
            if (nameEl) nameEl.textContent = user.display_name || user.username;
        } else {
            chip.innerHTML = '<i class="fas fa-sign-in-alt"></i> Masuk';
            chip.title = 'Login / Register';
            if (nameEl) nameEl.textContent = 'Kakak Shin';
        }
    }

    window.openAuthModal = function() {
        if (window.currentAuthUser && !window.currentAuthUser.guest) {
            if (confirm('Logout dari akun ' + window.currentAuthUser.display_name + '?')) {
                apiFetch('/api/auth/logout', { method: 'POST' })
                    .then(function() {
                        updateAuthUI({ guest: true });
                        if (typeof showNotification === 'function') {
                            showNotification('shiro', 'Logout berhasil. Mode tamu aktif.');
                        }
                    });
            }
            return;
        }
        var modal = document.getElementById('authModal');
        if (modal) modal.classList.add('active');
    };

    window.closeAuthModal = function() {
        var modal = document.getElementById('authModal');
        if (modal) modal.classList.remove('active');
    };

    window.submitAuth = function(mode) {
        var user = document.getElementById('authUsername').value.trim();
        var pass = document.getElementById('authPassword').value;
        var display = document.getElementById('authDisplayName').value.trim();
        var errEl = document.getElementById('authError');
        if (errEl) errEl.textContent = '';

        var url = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
        var body = { username: user, password: pass };
        if (mode === 'register') body.display_name = display || user;

        apiFetch(url, { method: 'POST', body: body })
            .then(function(r) { return r.json().then(function(d) { return { ok: r.ok, data: d }; }); })
            .then(function(res) {
                if (!res.ok) {
                    if (errEl) errEl.textContent = res.data.error || 'Gagal';
                    return;
                }
                updateAuthUI(res.data.user || { guest: false, display_name: display });
                closeAuthModal();
                if (typeof showNotification === 'function') {
                    showNotification('shiro', mode === 'register' ? 'Akun dibuat! Memori pribadi aktif.' : 'Selamat datang kembali!');
                }
                if (typeof loadChatHistory === 'function') {
                    loadChatHistory(window.currentCharacter || 'shiro');
                }
            })
            .catch(function() {
                if (errEl) errEl.textContent = 'Koneksi gagal';
            });
    };

    window.initAuth = function() {
        apiFetch('/api/auth/me')
            .then(function(r) { return r.json(); })
            .then(updateAuthUI)
            .catch(function() { updateAuthUI({ guest: true }); });
    };

    document.addEventListener('DOMContentLoaded', function() {
        initAuth();
    });
})();
