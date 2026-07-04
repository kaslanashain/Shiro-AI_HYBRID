/* Premium features — VTuber subtitle (random events moved to random-events.js) */
(function() {
    'use strict';

    function showSubtitle(text) {
        var el = document.getElementById('vtuberSubtitle');
        if (!el) return;
        el.textContent = text || '';
        el.classList.toggle('visible', !!text);
    }

    window.showVTuberSubtitle = showSubtitle;
})();
