/* Schedule / Planner — perpetual calendar + character voice alarms */
(function() {
    'use strict';

    var MONTHS_ID = [
        'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
        'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ];

    var VOICE_LINES = {
        shiro: {
            alarm: 'Sayang, alarm! Waktunya {title}. Shiro sudah bangun duluan lho~',
            task: 'Sayang, jangan lupa {title} ya. Shiro sayang banget sama Kakak~',
            event: 'Sayang, acara {title} dimulai sekarang!'
        },
        sishin: {
            alarm: 'Kak! Bangun! Alarm {title}! Sishin udah siap!',
            task: 'Kak! Ingat {title} ya! Jangan lupa!',
            event: 'Kak! Waktunya {title}! Ayo ayo!'
        }
    };

    var CHAR_IMAGES = {
        shiro: '/static/images/shiro.png',
        sishin: '/static/images/sishin.png'
    };

    var viewYear, viewMonth, selectedDate;
    var events = [];
    var checkInterval = null;
    var editingId = null;

    function storageKey() {
        var uid = (window.currentAuthUser && window.currentAuthUser.user_id) || 'guest';
        return 'shiro_schedule_' + uid;
    }

    function loadEvents() {
        try {
            var raw = localStorage.getItem(storageKey());
            events = raw ? JSON.parse(raw) : [];
        } catch (e) {
            events = [];
        }
    }

    function saveEvents() {
        localStorage.setItem(storageKey(), JSON.stringify(events));
    }

    function pad(n) {
        return String(n).padStart(2, '0');
    }

    function dateKey(y, m, d) {
        return y + '-' + pad(m + 1) + '-' + pad(d);
    }

    function parseDateKey(key) {
        var p = key.split('-');
        return { y: +p[0], m: +p[1] - 1, d: +p[2] };
    }

    function formatDateLabel(key) {
        var p = parseDateKey(key);
        return p.d + ' ' + MONTHS_ID[p.m] + ' ' + p.y;
    }

    function uuid() {
        return 'ev_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);
    }

    function getActiveCharacter() {
        return window.currentCharacter || 'shiro';
    }

    function buildVoiceText(ev) {
        if (ev.voice_text && ev.voice_text.trim()) return ev.voice_text.trim();
        var char = getActiveCharacter();
        var lines = VOICE_LINES[char] || VOICE_LINES.shiro;
        var tpl = lines[ev.type] || lines.event;
        return tpl.replace('{title}', ev.title || 'pengingat');
    }

    function playReminderVoice(text, karakter) {
        if (typeof putarAudio === 'function') {
            putarAudio(text, karakter);
            return;
        }
        fetch('/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text, karakter: karakter })
        })
        .then(function(r) { return r.blob(); })
        .then(function(blob) {
            var url = URL.createObjectURL(blob);
            var a = new Audio(url);
            a.onended = function() { URL.revokeObjectURL(url); };
            a.play();
        })
        .catch(function() {});
    }

    function showAlarmPopup(ev) {
        var overlay = document.getElementById('scheduleAlarmOverlay');
        if (!overlay) return;
        var char = getActiveCharacter();
        overlay.setAttribute('data-character', char);
        document.getElementById('scheduleAlarmAvatar').src = CHAR_IMAGES[char] || CHAR_IMAGES.shiro;
        document.getElementById('scheduleAlarmChar').textContent = char === 'sishin' ? 'Sishin' : 'Shiro';
        document.getElementById('scheduleAlarmTitle').textContent = ev.title;
        document.getElementById('scheduleAlarmMsg').textContent = buildVoiceText(ev);
        document.getElementById('scheduleAlarmTime').textContent = ev.time;
        overlay.classList.add('active');
        playReminderVoice(buildVoiceText(ev), char);
        if (typeof showNotification === 'function') {
            showNotification(char, buildVoiceText(ev));
        }
    }

    window.dismissScheduleAlarm = function() {
        var overlay = document.getElementById('scheduleAlarmOverlay');
        if (overlay) overlay.classList.remove('active');
    };

    function eventsOnDate(key) {
        return events.filter(function(ev) { return ev.date === key; });
    }

    function datesWithEvents() {
        var set = {};
        events.forEach(function(ev) { set[ev.date] = true; });
        return set;
    }

    function renderCalendar() {
        var grid = document.getElementById('scheduleGrid');
        var title = document.getElementById('scheduleMonthTitle');
        if (!grid || !title) return;

        title.textContent = MONTHS_ID[viewMonth] + ' ' + viewYear;
        grid.innerHTML = '';

        var today = new Date();
        var todayKey = dateKey(today.getFullYear(), today.getMonth(), today.getDate());
        var marked = datesWithEvents();

        var first = new Date(viewYear, viewMonth, 1);
        var startDay = first.getDay();
        var daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
        var prevDays = new Date(viewYear, viewMonth, 0).getDate();

        var cells = [];
        for (var i = startDay - 1; i >= 0; i--) {
            cells.push({ d: prevDays - i, other: true, m: viewMonth - 1, y: viewYear });
        }
        for (var d = 1; d <= daysInMonth; d++) {
            cells.push({ d: d, other: false, m: viewMonth, y: viewYear });
        }
        while (cells.length % 7 !== 0 || cells.length < 42) {
            var n = cells.length - (startDay + daysInMonth) + 1;
            cells.push({ d: n, other: true, m: viewMonth + 1, y: viewYear });
            n++;
        }

        cells.slice(0, 42).forEach(function(cell) {
            var cy = cell.y, cm = cell.m;
            if (cm < 0) { cm = 11; cy--; }
            if (cm > 11) { cm = 0; cy++; }
            var key = dateKey(cy, cm, cell.d);
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'schedule-day';
            btn.textContent = cell.d;
            if (cell.other) btn.classList.add('other-month');
            if (key === todayKey) btn.classList.add('today');
            if (key === selectedDate) btn.classList.add('selected');
            if (marked[key]) btn.classList.add('has-events');
            btn.dataset.date = key;
            btn.addEventListener('click', function() {
                selectedDate = key;
                renderCalendar();
                renderEventList();
                syncFormDate();
            });
            grid.appendChild(btn);
        });
    }

    function renderEventList() {
        var list = document.getElementById('scheduleEventList');
        var label = document.getElementById('scheduleSelectedLabel');
        if (!list) return;
        if (label) {
            label.innerHTML = 'Tanggal: <strong>' + formatDateLabel(selectedDate) + '</strong>';
        }
        var dayEvents = eventsOnDate(selectedDate).sort(function(a, b) {
            return a.time.localeCompare(b.time);
        });
        list.innerHTML = '';
        if (dayEvents.length === 0) {
            list.innerHTML = '<div class="schedule-empty">Belum ada jadwal. Buat di bawah.</div>';
            return;
        }
        dayEvents.forEach(function(ev) {
            var card = document.createElement('div');
            card.className = 'schedule-event-card';
            card.innerHTML =
                '<span class="schedule-event-time">' + ev.time + '</span>' +
                '<div class="schedule-event-info">' +
                '<div class="schedule-event-title">' + escapeHtml(ev.title) + '</div>' +
                '<div class="schedule-event-type">' + typeLabel(ev.type) + '</div>' +
                '</div>' +
                '<div class="schedule-event-actions">' +
                '<button type="button" title="Duplikat" data-dup="' + ev.id + '"><i class="fas fa-copy"></i></button>' +
                '<button type="button" title="Edit" data-edit="' + ev.id + '"><i class="fas fa-pen"></i></button>' +
                '<button type="button" title="Hapus" data-del="' + ev.id + '"><i class="fas fa-trash"></i></button>' +
                '</div>';
            list.appendChild(card);
        });

        list.querySelectorAll('[data-del]').forEach(function(b) {
            b.addEventListener('click', function() {
                deleteEvent(b.getAttribute('data-del'));
            });
        });
        list.querySelectorAll('[data-edit]').forEach(function(b) {
            b.addEventListener('click', function() {
                editEvent(b.getAttribute('data-edit'));
            });
        });
        list.querySelectorAll('[data-dup]').forEach(function(b) {
            b.addEventListener('click', function() {
                duplicateEvent(b.getAttribute('data-dup'));
            });
        });
    }

    function typeLabel(t) {
        if (t === 'alarm') return 'Alarm';
        if (t === 'task') return 'Tugas';
        return 'Acara';
    }

    function escapeHtml(s) {
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function syncFormDate() {
        var inp = document.getElementById('scheduleFormDate');
        if (inp) inp.value = selectedDate;
    }

    function clearForm() {
        editingId = null;
        document.getElementById('scheduleFormTitle').value = '';
        document.getElementById('scheduleFormTime').value = '07:00';
        document.getElementById('scheduleFormType').value = 'alarm';
        document.getElementById('scheduleFormVoice').value = '';
        syncFormDate();
        var btn = document.getElementById('scheduleSaveBtn');
        if (btn) btn.textContent = 'Simpan Jadwal';
    }

    function saveEventFromForm() {
        var title = document.getElementById('scheduleFormTitle').value.trim();
        var time = document.getElementById('scheduleFormTime').value;
        var type = document.getElementById('scheduleFormType').value;
        var date = document.getElementById('scheduleFormDate').value || selectedDate;
        var voice = document.getElementById('scheduleFormVoice').value.trim();

        if (!title) {
            alert('Isi judul jadwal / alarm.');
            return;
        }
        if (!time) {
            alert('Pilih waktu.');
            return;
        }

        if (editingId) {
            var ev = events.find(function(e) { return e.id === editingId; });
            if (ev) {
                ev.title = title;
                ev.time = time;
                ev.type = type;
                ev.date = date;
                ev.voice_text = voice;
                ev.triggered = {};
            }
        } else {
            events.push({
                id: uuid(),
                title: title,
                time: time,
                type: type,
                date: date,
                voice_text: voice,
                triggered: {}
            });
        }
        saveEvents();
        selectedDate = date;
        clearForm();
        renderCalendar();
        renderEventList();
    }

    function deleteEvent(id) {
        if (!confirm('Hapus jadwal ini?')) return;
        events = events.filter(function(e) { return e.id !== id; });
        saveEvents();
        renderCalendar();
        renderEventList();
    }

    function editEvent(id) {
        var ev = events.find(function(e) { return e.id === id; });
        if (!ev) return;
        editingId = id;
        document.getElementById('scheduleFormTitle').value = ev.title;
        document.getElementById('scheduleFormTime').value = ev.time;
        document.getElementById('scheduleFormType').value = ev.type;
        document.getElementById('scheduleFormDate').value = ev.date;
        document.getElementById('scheduleFormVoice').value = ev.voice_text || '';
        selectedDate = ev.date;
        document.getElementById('scheduleSaveBtn').textContent = 'Update Jadwal';
        renderCalendar();
    }

    function duplicateEvent(id) {
        var ev = events.find(function(e) { return e.id === id; });
        if (!ev) return;
        events.push({
            id: uuid(),
            title: ev.title + ' (salin)',
            time: ev.time,
            type: ev.type,
            date: selectedDate,
            voice_text: ev.voice_text || '',
            triggered: {}
        });
        saveEvents();
        renderCalendar();
        renderEventList();
    }

    function checkAlarms() {
        var now = new Date();
        var key = dateKey(now.getFullYear(), now.getMonth(), now.getDate());
        var hm = pad(now.getHours()) + ':' + pad(now.getMinutes());

        events.forEach(function(ev) {
            if (ev.date !== key || ev.time !== hm) return;
            if (!ev.triggered) ev.triggered = {};
            if (ev.triggered[key + '_' + hm]) return;
            ev.triggered[key + '_' + hm] = true;
            saveEvents();
            showAlarmPopup(ev);
        });
    }

    function startAlarmLoop() {
        if (checkInterval) return;
        checkAlarms();
        checkInterval = setInterval(checkAlarms, 15000);
    }

    window.openSchedule = function() {
        loadEvents();
        var now = new Date();
        viewYear = now.getFullYear();
        viewMonth = now.getMonth();
        selectedDate = dateKey(viewYear, viewMonth, now.getDate());
        clearForm();
        renderCalendar();
        renderEventList();
        var modal = document.getElementById('scheduleModal');
        if (modal) modal.classList.add('active');
    };

    window.closeSchedule = function() {
        var modal = document.getElementById('scheduleModal');
        if (modal) modal.classList.remove('active');
    };

    document.addEventListener('DOMContentLoaded', function() {
        loadEvents();
        startAlarmLoop();

        var prev = document.getElementById('schedulePrevMonth');
        var next = document.getElementById('scheduleNextMonth');
        if (prev) {
            prev.addEventListener('click', function() {
                viewMonth--;
                if (viewMonth < 0) { viewMonth = 11; viewYear--; }
                renderCalendar();
            });
        }
        if (next) {
            next.addEventListener('click', function() {
                viewMonth++;
                if (viewMonth > 11) { viewMonth = 0; viewYear++; }
                renderCalendar();
            });
        }

        var saveBtn = document.getElementById('scheduleSaveBtn');
        if (saveBtn) saveBtn.addEventListener('click', saveEventFromForm);
        var clearBtn = document.getElementById('scheduleClearBtn');
        if (clearBtn) clearBtn.addEventListener('click', clearForm);

        document.getElementById('scheduleModal')?.addEventListener('click', function(e) {
            if (e.target === this) closeSchedule();
        });
    });
})();
