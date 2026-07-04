/* Interactive Story Mode — Dungeon Master */
(function() {
    'use strict';

    var storySessionId = null;
    var storyTheme = 'fantasy';

    window.openStoryMode = function() {
        var screen = document.getElementById('storyScreen');
        var picker = document.getElementById('storyPickerModal');
        if (picker) picker.classList.add('active');
    };

    window.closeStoryPicker = function() {
        var picker = document.getElementById('storyPickerModal');
        if (picker) picker.classList.remove('active');
    };

    window.startStoryAdventure = function(theme) {
        storyTheme = theme || 'fantasy';
        closeStoryPicker();
        var karakter = window.currentCharacter || 'shiro';

        if (typeof showTypingIndicator === 'function') showTypingIndicator();

        apiFetch('/api/story/start', {
            method: 'POST',
            body: { karakter: karakter, theme: storyTheme }
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (typeof hideTypingIndicator === 'function') hideTypingIndicator();
            if (data.error) {
                alert(data.error);
                return;
            }
            storySessionId = data.session_id;
            showStoryScreen(data);
        })
        .catch(function() {
            if (typeof hideTypingIndicator === 'function') hideTypingIndicator();
            alert('Gagal memulai petualangan');
        });
    };

    function showStoryScreen(data) {
        var home = document.getElementById('homeScreen');
        var chat = document.getElementById('chatScreen');
        var story = document.getElementById('storyScreen');
        if (home) home.style.display = 'none';
        if (chat) chat.style.display = 'none';
        if (story) {
            story.classList.add('active');
            renderStory(data);
        }
    }

    window.closeStoryMode = function() {
        var story = document.getElementById('storyScreen');
        var home = document.getElementById('homeScreen');
        if (story) story.classList.remove('active');
        if (home) home.style.display = 'flex';
        storySessionId = null;
    };

    function renderStory(data) {
        var sceneEl = document.getElementById('storyScene');
        var choicesEl = document.getElementById('storyChoices');
        var hpEl = document.getElementById('storyHp');
        var locEl = document.getElementById('storyLocation');
        var titleEl = document.getElementById('storyTitle');

        if (titleEl) titleEl.textContent = data.title || 'Petualangan';
        if (hpEl) hpEl.textContent = 'HP: ' + (data.hp != null ? data.hp : 100);
        if (locEl) locEl.textContent = data.location || '???';

        if (sceneEl) {
            var html = (data.narration || '').replace(/\n/g, '<br>');
            if (data.companion_line) {
                html += '<div class="story-companion-line"><strong>' +
                    (data.companion_name || 'Companion') + ':</strong> ' +
                    data.companion_line + '</div>';
            }
            sceneEl.innerHTML = html;
        }

        if (choicesEl && data.choices) {
            choicesEl.innerHTML = '';
            data.choices.forEach(function(choice) {
                var btn = document.createElement('button');
                btn.className = 'story-choice-btn';
                btn.textContent = choice;
                btn.onclick = function() { storyAction(choice); };
                choicesEl.appendChild(btn);
            });
        }

        if (data.game_over) {
            var over = document.createElement('p');
            over.style.color = '#ff6b8a';
            over.style.marginTop = '12px';
            over.textContent = 'Game Over! Mulai petualangan baru?';
            if (choicesEl) choicesEl.appendChild(over);
        }

        if (data.companion_line && typeof putarAudio === 'function') {
            putarAudio(data.companion_line, data.karakter || window.currentCharacter);
        }
    }

    window.storyAction = function(action) {
        if (!storySessionId || !action) return;
        var sceneEl = document.getElementById('storyScene');
        if (sceneEl) sceneEl.style.opacity = '0.5';

        apiFetch('/api/story/action', {
            method: 'POST',
            body: { session_id: storySessionId, action: action }
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (sceneEl) sceneEl.style.opacity = '1';
            if (data.error) {
                alert(data.error);
                return;
            }
            renderStory(data);
        })
        .catch(function() {
            if (sceneEl) sceneEl.style.opacity = '1';
        });
    };

    window.storyCustomAction = function() {
        var input = document.getElementById('storyCustomAction');
        if (!input || !input.value.trim()) return;
        storyAction(input.value.trim());
        input.value = '';
    };
})();
