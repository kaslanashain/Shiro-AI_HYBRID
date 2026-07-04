/**
 * Daily Diary — save notes; character reacts by affection mood
 */
(function(global) {
    'use strict';

    function storageKey() {
        var uid = (global.currentAuthUser && global.currentAuthUser.user_id) || 'guest';
        return 'shiro_diary_' + uid;
    }

    function todayKey() {
        var d = new Date();
        return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' +
            String(d.getDate()).padStart(2, '0');
    }

    function loadEntries() {
        try {
            var raw = localStorage.getItem(storageKey());
            return raw ? JSON.parse(raw) : {};
        } catch (e) {
            return {};
        }
    }

    function saveEntries(entries) {
        localStorage.setItem(storageKey(), JSON.stringify(entries));
    }

    function getActiveCharacter() {
        if (global.CharacterState) return CharacterState.get();
        return global.currentCharacter || 'shiro';
    }

    function renderHistory() {
        var list = document.getElementById('diaryHistory');
        if (!list) return;
        var entries = loadEntries();
        var keys = Object.keys(entries).sort().reverse();
        list.innerHTML = '';
        if (!keys.length) {
            list.innerHTML = '<p class="diary-empty">Belum ada catatan. Tulis diary hari ini!</p>';
            return;
        }
        keys.slice(0, 14).forEach(function(key) {
            var item = document.createElement('div');
            item.className = 'diary-history-item';
            item.innerHTML = '<span class="diary-date">' + key + '</span>' +
                '<p>' + escapeHtml(entries[key].note || '') + '</p>' +
                (entries[key].reply
                    ? '<blockquote class="diary-reply-preview">' + escapeHtml(entries[key].reply) + '</blockquote>'
                    : '');
            list.appendChild(item);
        });
    }

    function escapeHtml(text) {
        var d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }

    function openDiary() {
        var modal = document.getElementById('diaryModal');
        if (!modal) return;
        modal.classList.add('active');
        var entries = loadEntries();
        var today = todayKey();
        var input = document.getElementById('diaryNoteInput');
        var reaction = document.getElementById('diaryReaction');
        if (input) input.value = (entries[today] && entries[today].note) || '';
        if (reaction) reaction.textContent = (entries[today] && entries[today].reply) || '';
        renderHistory();
    }

    function closeDiary() {
        var modal = document.getElementById('diaryModal');
        if (modal) modal.classList.remove('active');
    }

    function saveDiary() {
        var input = document.getElementById('diaryNoteInput');
        var reactionEl = document.getElementById('diaryReaction');
        var saveBtn = document.getElementById('diarySaveBtn');
        if (!input) return;
        var note = input.value.trim();
        if (!note) {
            alert('Tulis catatan dulu ya!');
            return;
        }

        var char = getActiveCharacter();
        var today = todayKey();
        var entries = loadEntries();

        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.textContent = 'Menyimpan...';
        }

        fetch('/api/diary/react', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ note: note, karakter: char, use_llm: false })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.error) throw new Error(data.error);
            entries[today] = {
                note: note,
                reply: data.reply || '',
                mood: data.mood || 'normal',
                affection: data.affection,
                karakter: data.karakter || char,
                savedAt: new Date().toISOString()
            };
            saveEntries(entries);
            if (reactionEl) {
                reactionEl.textContent = data.reply || '';
                reactionEl.setAttribute('data-mood', data.mood || 'normal');
            }
            renderHistory();
            if (typeof global.addMessage === 'function' && data.reply) {
                global.addMessage('[Diary] ' + data.reply, data.karakter || char);
            }
            if (typeof global.putarAudio === 'function' && data.reply) {
                global.putarAudio(data.reply, data.karakter || char);
            }
            if (typeof global.showNotification === 'function' && data.reply) {
                global.showNotification(data.karakter || char, data.reply);
            }
        })
        .catch(function(err) {
            alert('Gagal menyimpan diary: ' + (err.message || 'error'));
        })
        .finally(function() {
            if (saveBtn) {
                saveBtn.disabled = false;
                saveBtn.textContent = 'Simpan & Kirim ke Karakter';
            }
        });
    }

    global.openDiary = openDiary;
    global.closeDiary = closeDiary;
    global.saveDiary = saveDiary;
}(window));
