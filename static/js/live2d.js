/**
 * Live2D VTuber Engine — PixiJS 7 + pixi-live2d-display
 * Breathing, head sway, blink, physics, safe switch, PNG fallback
 */
(function(global) {
    'use strict';

    var MODEL_PATHS = {
        shiro: '/static/live2d/shiro/Haru.model3.json',
        sishin: '/static/live2d/samples/hiyori/Hiyori.model3.json'
    };

    var FALLBACK_PNG = {
        shiro: '/static/images/shiro.png',
        sishin: '/static/images/sishin.png'
    };

    var MOUTH_PARAMS = ['ParamMouthOpenY', 'ParamMouthForm', 'PARAM_MOUTH_OPEN_Y'];
    var EYE_PARAMS = ['ParamEyeLOpen', 'ParamEyeROpen'];
    var SWAY_PARAMS = {
        x: ['ParamAngleX', 'ParamBodyAngleX'],
        y: ['ParamAngleY', 'ParamBodyAngleY'],
        z: ['ParamAngleZ', 'ParamBodyAngleZ'],
        breath: ['ParamBreath', 'ParamBodyAngleX']
    };

    var live2dApp = null;
    var live2dModel = null;
    var lipSyncTimer = null;
    var lipSyncPhase = 0;
    var loadToken = 0;
    var idleTime = 0;
    var isSpeaking = false;
    var blinkState = { nextMs: 0, closing: false, elapsed: 0 };
    var idleTickerBound = null;
    var resizeObserver = null;
    var live2dReady = false;
    var engineReady = false;
    var currentChar = 'shiro';
    var wardrobeLive2DMode = false;

    function getLive2DModelClass() {
        if (global.PIXI && global.PIXI.live2d && global.PIXI.live2d.Live2DModel) {
            return global.PIXI.live2d.Live2DModel;
        }
        if (global.Live2DModel) return global.Live2DModel;
        return null;
    }

    function getActiveCharacter() {
        if (global.CharacterState) return CharacterState.get();
        return global.currentCharacter || 'shiro';
    }

    function normalizeChar(char) {
        return char === 'sishin' ? 'sishin' : 'shiro';
    }

    function getContainer() {
        return document.getElementById('live2dCanvas');
    }

    function getAvatarWrap() {
        return document.querySelector('.avatar-container') ||
            document.querySelector('.desktop-avatar-wrap');
    }

    function getFallbackAvatarEl() {
        return document.getElementById('homeAvatar') ||
            document.getElementById('deskAvatar');
    }

    function getAppTicker() {
        if (live2dApp && live2dApp.ticker && typeof live2dApp.ticker.add === 'function') {
            return live2dApp.ticker;
        }
        if (global.PIXI && global.PIXI.Ticker && global.PIXI.Ticker.shared) {
            return global.PIXI.Ticker.shared;
        }
        return null;
    }

    function registerLive2DTicker(Live2DModel) {
        /* pixi-live2d-display expects the Ticker *class* (uses Ticker.shared.add) */
        if (!Live2DModel || !Live2DModel.registerTicker) return;
        if (global.PIXI && global.PIXI.Ticker) {
            Live2DModel.registerTicker(global.PIXI.Ticker);
        }
    }

    function prepLive2DLayout() {
        var container = getContainer();
        var wrap = getAvatarWrap();
        var avatar = getFallbackAvatarEl();
        if (wrap) wrap.classList.add('live2d-active');
        if (container) container.classList.add('active');
        if (avatar) {
            avatar.style.opacity = '0';
            avatar.style.visibility = 'hidden';
            avatar.style.pointerEvents = 'none';
            avatar.classList.add('hidden');
        }
    }

    function resetLive2DStatus() {
        var sub = document.getElementById('homeCharSub');
        if (!sub) return;
        var char = normalizeChar(getActiveCharacter());
        sub.textContent = char === 'sishin' ? 'Adik kecil yang imut' : 'Onee-san yang manja';
        sub.style.color = '';
        delete sub.dataset.live2dPrev;
    }

    function showLive2DStatus(message, isError) {
        var sub = document.getElementById('homeCharSub');
        if (!sub || !message) return;
        if (!sub.dataset.live2dPrev) sub.dataset.live2dPrev = sub.textContent;
        sub.textContent = message;
        sub.style.color = isError ? '#ff8a9b' : 'rgba(255,255,255,0.45)';
        if (isError) {
            setTimeout(function() {
                resetLive2DStatus();
            }, 4200);
            return;
        }
        setTimeout(function() {
            resetLive2DStatus();
        }, 3200);
    }

    function ensureLive2DEngine() {
        var Live2DModel = getLive2DModelClass();
        if (typeof global.PIXI === 'undefined' || !Live2DModel) {
            var missing = typeof global.PIXI === 'undefined' ? 'PixiJS' : 'Live2DModel';
            showLive2DStatus('Live2D tidak tersedia (' + missing + '). Pakai ekspresi PNG.', true);
            if (global.AssetManager && AssetManager.revertLive2DToExpressions) {
                AssetManager.revertLive2DToExpressions(getActiveCharacter());
            }
            return Promise.reject(new Error('Live2D SDK not loaded (' + missing + ')'));
        }

        if (engineReady && live2dApp && live2dApp.stage) {
            registerLive2DTicker(Live2DModel);
            return Promise.resolve(live2dApp);
        }

        var container = getContainer();
        if (!container) {
            return Promise.reject(new Error('Live2D container missing'));
        }

        try {
            if (live2dApp) {
                destroyLive2DModel();
                live2dApp.destroy(true, { children: true, texture: true, baseTexture: true });
                live2dApp = null;
                engineReady = false;
                container.innerHTML = '';
            }

            var cw = container.clientWidth || 320;
            var ch = container.clientHeight || 400;

            live2dApp = new PIXI.Application({
                width: Math.max(200, cw),
                height: Math.max(260, ch),
                backgroundAlpha: 0,
                antialias: true,
                autoDensity: true,
                resolution: Math.min(global.devicePixelRatio || 1, 2),
                autoStart: true,
                sharedTicker: true
            });

            registerLive2DTicker(Live2DModel);

            container.appendChild(live2dApp.view);
            live2dApp.view.style.width = '100%';
            live2dApp.view.style.height = '100%';
            live2dApp.view.style.display = 'block';

            if (!live2dApp.stage) {
                return Promise.reject(new Error('Pixi stage not ready'));
            }

            if (global.ResizeObserver && !resizeObserver) {
                resizeObserver = new ResizeObserver(function() {
                    resizeLive2DCanvas();
                });
                resizeObserver.observe(container);
            }

            global.addEventListener('resize', resizeLive2DCanvas);
            engineReady = true;
            return Promise.resolve(live2dApp);
        } catch (e) {
            return Promise.reject(e);
        }
    }

    function isWardrobeLive2DEnabled(char) {
        if (global.AssetManager && typeof AssetManager.isLive2DMode === 'function') {
            return AssetManager.isLive2DMode(char || getActiveCharacter());
        }
        return wardrobeLive2DMode;
    }

    function setParam(id, value) {
        if (!live2dModel || !live2dModel.internalModel) return false;
        try {
            live2dModel.internalModel.coreModel.setParameterValueById(id, value);
            return true;
        } catch (e) {
            return false;
        }
    }

    function setParamFirst(ids, value) {
        for (var i = 0; i < ids.length; i++) {
            if (setParam(ids[i], value)) return true;
        }
        return false;
    }

    function setMouthOpen(value) {
        setParamFirst(MOUTH_PARAMS, value);
    }

    function rand(min, max) {
        return min + Math.random() * (max - min);
    }

    function scheduleBlink() {
        blinkState.nextMs = performance.now() + rand(2200, 5500);
        blinkState.closing = false;
        blinkState.elapsed = 0;
    }

    function applyPngFallback(char) {
        char = normalizeChar(char);
        var container = getContainer();
        var wrap = getAvatarWrap();
        var avatar = getFallbackAvatarEl();

        if (container) container.classList.remove('active');
        if (wrap) wrap.classList.remove('live2d-active');

        if (avatar) {
            avatar.style.opacity = '';
            avatar.style.visibility = '';
            avatar.style.pointerEvents = '';
            avatar.classList.remove('hidden');
            if (typeof global.applyHomeAvatarExpression === 'function') {
                global.applyHomeAvatarExpression(char);
            } else {
                avatar.src = FALLBACK_PNG[char] || FALLBACK_PNG.shiro;
            }
        }
        live2dReady = false;
    }

    function applyLive2DVisible() {
        var container = getContainer();
        var wrap = getAvatarWrap();
        var avatar = getFallbackAvatarEl();
        if (container) container.classList.add('active');
        if (wrap) wrap.classList.add('live2d-active');
        if (avatar) {
            avatar.style.opacity = '0';
            avatar.style.visibility = 'hidden';
            avatar.style.pointerEvents = 'none';
            avatar.classList.add('hidden');
        }
        live2dReady = true;
        requestAnimationFrame(function() {
            layoutModel();
        });
    }

    /* Per-character bust crop: fraction of model height visible (head → waist) */
    var BUST_LAYOUT = {
        shiro: { visibleTopRatio: 0.44, topPad: 0.05, maxScale: 0.52 },
        sishin: { visibleTopRatio: 0.48, topPad: 0.04, maxScale: 0.48 }
    };

    function measureModelHeight(model) {
        if (!model) return 1400;
        try {
            model.scale.set(1);
            model.anchor.set(0.5, 0);
            var h = model.height;
            if (h && h > 10) return h;
            var bounds = model.getLocalBounds();
            if (bounds && bounds.height > 10) return bounds.height;
        } catch (e) { /* ignore */ }
        return 1400;
    }

    function layoutModel() {
        if (!live2dModel) return;
        var container = getContainer();
        if (!container) return;

        var w = container.clientWidth || 320;
        var h = container.clientHeight || 400;
        var cfg = BUST_LAYOUT[currentChar] || BUST_LAYOUT.sishin;

        var rawH = measureModelHeight(live2dModel);
        var scale = (h * 0.94) / (rawH * cfg.visibleTopRatio);
        scale = Math.max(0.14, Math.min(scale, cfg.maxScale));

        live2dModel.anchor.set(0.5, 0);
        live2dModel.scale.set(scale);
        live2dModel.x = w * 0.5;
        live2dModel.y = h * cfg.topPad;
    }

    function resizeLive2DCanvas() {
        var container = getContainer();
        if (!container || !live2dApp || !live2dApp.renderer) return;
        var w = Math.max(200, container.clientWidth || 320);
        var h = Math.max(260, container.clientHeight || 400);
        live2dApp.renderer.resize(w, h);
        layoutModel();
    }

    function stopProceduralIdle() {
        var ticker = getAppTicker();
        if (idleTickerBound && ticker && typeof ticker.remove === 'function') {
            ticker.remove(idleTickerBound);
        }
        idleTickerBound = null;
    }

    function updateBlink(deltaSec) {
        if (!live2dModel) return;
        var now = performance.now();

        if (!blinkState.closing && now >= blinkState.nextMs) {
            blinkState.closing = true;
            blinkState.elapsed = 0;
        }

        if (blinkState.closing) {
            blinkState.elapsed += deltaSec;
            var t = blinkState.elapsed;
            var eyeOpen;
            if (t < 0.06) {
                eyeOpen = 1 - (t / 0.06);
            } else if (t < 0.12) {
                eyeOpen = (t - 0.06) / 0.06;
            } else {
                eyeOpen = 1;
                blinkState.closing = false;
                scheduleBlink();
            }
            for (var i = 0; i < EYE_PARAMS.length; i++) {
                setParam(EYE_PARAMS[i], eyeOpen);
            }
        }
    }

    function updateProceduralIdle(deltaSec) {
        if (!live2dModel || isSpeaking) return;

        idleTime += deltaSec;
        var breath = Math.sin(idleTime * 1.35) * 0.5 + 0.5;
        var swayX = Math.sin(idleTime * 0.42) * 4.5 + Math.sin(idleTime * 0.17) * 1.5;
        var swayY = Math.sin(idleTime * 0.31 + 0.8) * 3.2;
        var swayZ = Math.sin(idleTime * 0.23) * 1.8;

        setParamFirst(SWAY_PARAMS.breath, breath);
        setParamFirst(SWAY_PARAMS.x, swayX);
        setParamFirst(SWAY_PARAMS.y, swayY);
        setParamFirst(SWAY_PARAMS.z, swayZ);
    }

    function idleTicker(delta) {
        if (!live2dModel) return;
        var deltaSec = (delta || 1) / 60;
        updateProceduralIdle(deltaSec);
        updateBlink(deltaSec);
    }

    function startProceduralIdle() {
        stopProceduralIdle();
        idleTime = 0;
        scheduleBlink();
        idleTickerBound = idleTicker;
        var ticker = getAppTicker();
        if (ticker && typeof ticker.add === 'function') {
            ticker.add(idleTickerBound);
        }
    }

    function enablePhysics(model) {
        try {
            var im = model.internalModel;
            if (!im) return;
            if (im.physics && typeof im.physics.reset === 'function') {
                im.physics.reset();
            }
            if (im.physicsController) {
                im.physicsController.enabled = true;
            }
        } catch (e) {
            console.debug('[Live2D] physics hook:', e);
        }
    }

    function startIdleMotion(model) {
        if (!model || typeof model.motion !== 'function') return;
        model.motion('Idle', 0, 2).catch(function() {
            model.motion('idle', 0, 2).catch(function() {});
        });
    }

    function destroyLive2DModel() {
        stopProceduralIdle();
        stopLive2DLipSyncInternal(false);

        if (live2dModel && live2dApp) {
            try {
                live2dApp.stage.removeChild(live2dModel);
            } catch (e) { /* ignore */ }
            try {
                if (typeof live2dModel.destroy === 'function') {
                    live2dModel.destroy({ children: true, texture: true, baseTexture: true });
                }
            } catch (e) {
                console.debug('[Live2D] destroy:', e);
            }
        }
        live2dModel = null;
    }

    function validateModelPath(path) {
        /* Skip HEAD — some hosts block it; Live2DModel.from handles missing files */
        return Promise.resolve(path);
    }

    function loadLive2DModel(karakter) {
        var Live2DModel = getLive2DModelClass();
        if (!Live2DModel) {
            applyPngFallback(karakter);
            return Promise.resolve(false);
        }

        karakter = normalizeChar(karakter);
        currentChar = karakter;
        var path = MODEL_PATHS[karakter] || MODEL_PATHS.shiro;

        if (global.AssetManager) {
            var outfits = AssetManager.getCatalog(karakter);
            var selId = typeof AssetManager.getSelectedOutfit === 'function'
                ? AssetManager.getSelectedOutfit(karakter) : null;
            var chosen = null;

            /* Prefer the outfit the user actually selected in the wardrobe */
            for (var i = 0; i < outfits.length; i++) {
                if (outfits[i].id === selId && outfits[i].mode === 'live2d' && outfits[i].modelPath) {
                    chosen = outfits[i].modelPath;
                    break;
                }
            }

            /* Fallback: first available Live2D outfit with a model path */
            if (!chosen) {
                for (var j = 0; j < outfits.length; j++) {
                    if (outfits[j].mode === 'live2d' && outfits[j].modelPath) {
                        chosen = outfits[j].modelPath;
                        break;
                    }
                }
            }

            if (chosen) path = chosen;
        }

        var token = ++loadToken;

        destroyLive2DModel();

        return ensureLive2DEngine().then(function() {
            if (token !== loadToken) return false;
            return validateModelPath(path);
        }).then(function(validPath) {
            if (!validPath || token !== loadToken) return null;
            registerLive2DTicker(Live2DModel);
            return Live2DModel.from(validPath, {
                autoInteract: false,
                idleMotionGroup: 'Idle'
            });
        })
            .then(function(model) {
                if (!model || token !== loadToken) {
                    if (model && typeof model.destroy === 'function') model.destroy();
                    return false;
                }

                live2dModel = model;
                enablePhysics(model);

                if (!live2dApp || !live2dApp.stage) {
                    throw new Error('Pixi stage missing');
                }

                live2dApp.stage.addChild(model);
                layoutModel();
                try { startIdleMotion(model); } catch (e) { console.debug('[Live2D] idle motion:', e); }
                try { startProceduralIdle(); } catch (e) { console.debug('[Live2D] procedural idle:', e); }
                applyLive2DVisible();
                showLive2DStatus('Live2D VTuber aktif', false);
                console.log('[Live2D] VTuber model ready:', karakter);
                return true;
            })
            .catch(function(err) {
                console.error('[Live2D] load failed —', err && err.message ? err.message : err);
                showLive2DStatus('Live2D gagal dimuat — pakai ekspresi PNG.', true);
                if (token === loadToken) {
                    destroyLive2DModel();
                    if (global.AssetManager && AssetManager.revertLive2DToExpressions) {
                        AssetManager.revertLive2DToExpressions(karakter);
                    } else {
                        resetLive2DStatus();
                        applyPngFallback(karakter);
                    }
                }
                return false;
            });
    }

    function stopLive2DLipSyncInternal(restartIdle) {
        if (lipSyncTimer) {
            clearInterval(lipSyncTimer);
            lipSyncTimer = null;
        }
        setMouthOpen(0);
        isSpeaking = false;
        if (restartIdle !== false && live2dModel) {
            startIdleMotion(live2dModel);
        }
    }

    global.startLive2DLipSync = function(audioElement) {
        stopLive2DLipSyncInternal(false);
        if (!live2dModel) return;

        isSpeaking = true;
        try {
            if (typeof live2dModel.motion === 'function') {
                live2dModel.motion('talk').catch(function() {
                    live2dModel.motion('Talk').catch(function() {});
                });
            }
        } catch (e) { /* optional talk motion */ }

        if (audioElement && global.AudioContext) {
            try {
                var ctx = new (global.AudioContext || global.webkitAudioContext)();
                var source = ctx.createMediaElementSource(audioElement);
                var analyser = ctx.createAnalyser();
                analyser.fftSize = 256;
                source.connect(analyser);
                analyser.connect(ctx.destination);
                var data = new Uint8Array(analyser.frequencyBinCount);

                lipSyncTimer = setInterval(function() {
                    analyser.getByteFrequencyData(data);
                    var sum = 0;
                    for (var j = 0; j < data.length; j++) sum += data[j];
                    var avg = sum / data.length / 255;
                    setMouthOpen(Math.min(1, avg * 2.4 + 0.04));
                }, 50);
                return;
            } catch (e) {
                console.debug('[Live2D] analyser fallback:', e);
            }
        }

        lipSyncPhase = 0;
        lipSyncTimer = setInterval(function() {
            lipSyncPhase += 0.18;
            setMouthOpen(Math.abs(Math.sin(lipSyncPhase * 8)) * 0.72 + 0.06);
        }, 50);
    };

    global.stopLive2DLipSync = function() {
        stopLive2DLipSyncInternal(true);
    };

    global.setLive2DMotion = function(motion) {
        if (live2dModel && typeof live2dModel.motion === 'function') {
            live2dModel.motion(motion || 'idle').catch(function() {});
        }
    };

    global.switchLive2DCharacter = function(karakter) {
        karakter = normalizeChar(karakter);
        if (!isWardrobeLive2DEnabled(karakter)) return Promise.resolve(false);
        if (karakter === currentChar && live2dReady && live2dModel) return Promise.resolve(true);
        stopLive2DLipSyncInternal(true);
        return ensureLive2DEngine().then(function() {
            return loadLive2DModel(karakter);
        });
    };

    global.activateLive2DFromWardrobe = function(char) {
        char = normalizeChar(char);
        wardrobeLive2DMode = true;
        console.log('[Live2D] Wardrobe activated Live2D for', char);
        return ensureLive2DEngine()
            .then(function() {
                return loadLive2DModel(char);
            })
            .catch(function(err) {
                console.warn('[Live2D] Wardrobe activation failed:', err);
                wardrobeLive2DMode = false;
                if (global.AssetManager && AssetManager.revertLive2DToExpressions) {
                    AssetManager.revertLive2DToExpressions(char);
                } else {
                    resetLive2DStatus();
                    applyPngFallback(char);
                }
                return false;
            });
    };

    global.deactivateLive2DFromWardrobe = function(char) {
        char = normalizeChar(char);
        wardrobeLive2DMode = false;
        destroyLive2DModel();
        resetLive2DStatus();
        applyPngFallback(char);
    };

    global.initLive2D = function() {
        var char = getActiveCharacter();

        if (!isWardrobeLive2DEnabled(char)) {
            applyPngFallback(char);
            return;
        }

        global.activateLive2DFromWardrobe(char);
    };

    global.isLive2DActive = function() {
        return live2dReady && !!live2dModel && isWardrobeLive2DEnabled();
    };

    function hookCharacterSwitch() {
        if (global.CharacterState) {
            CharacterState.onChange(function(char) {
                char = normalizeChar(char);
                if (isWardrobeLive2DEnabled(char)) {
                    global.activateLive2DFromWardrobe(char);
                } else {
                    global.deactivateLive2DFromWardrobe(char);
                }
            });
            return;
        }

        var origSwitch = global.switchCharacter;
        if (typeof origSwitch === 'function' && !origSwitch.__live2dHooked) {
            global.switchCharacter = function(char) {
                origSwitch(char);
                char = normalizeChar(char);
                if (isWardrobeLive2DEnabled(char)) {
                    global.activateLive2DFromWardrobe(char);
                } else {
                    global.deactivateLive2DFromWardrobe(char);
                }
            };
            global.switchCharacter.__live2dHooked = true;
        }
    }

    var beatDanceTimer = null;
    var beatAnalyser = null;
    var beatAudioCtx = null;
    var beatBaseY = 0;

    function stopBeatDanceInternal() {
        if (beatDanceTimer) {
            clearInterval(beatDanceTimer);
            beatDanceTimer = null;
        }
        if (beatAnalyser && beatAudioCtx) {
            try { beatAudioCtx.close(); } catch (e) { /* ignore */ }
        }
        beatAnalyser = null;
        beatAudioCtx = null;
        if (live2dModel) {
            live2dModel.y = beatBaseY;
            live2dModel.angle = 0;
        }
    }

    global.startLive2DBeatDance = function(audioElement) {
        stopBeatDanceInternal();
        if (!live2dModel || !audioElement) return;
        beatBaseY = live2dModel.y || 0;
        var data = null;
        var analyser = null;
        if (global.AudioContext) {
            try {
                beatAudioCtx = new (global.AudioContext || global.webkitAudioContext)();
                var source = beatAudioCtx.createMediaElementSource(audioElement);
                analyser = beatAudioCtx.createAnalyser();
                analyser.fftSize = 512;
                source.connect(analyser);
                analyser.connect(beatAudioCtx.destination);
                beatAnalyser = analyser;
                data = new Uint8Array(analyser.frequencyBinCount);
            } catch (e) {
                console.debug('[Live2D] beat dance analyser fallback:', e);
            }
        }
        var phase = 0;
        var lastMotion = 0;
        beatDanceTimer = setInterval(function() {
            if (!live2dModel) return;
            var bass = 0.25;
            if (analyser && data) {
                analyser.getByteFrequencyData(data);
                var sum = 0;
                var count = Math.min(12, data.length);
                for (var i = 0; i < count; i++) sum += data[i];
                bass = sum / count / 255;
            } else {
                phase += 0.08;
                bass = Math.abs(Math.sin(phase)) * 0.55 + 0.15;
            }
            live2dModel.y = beatBaseY - bass * 14;
            live2dModel.angle = (bass - 0.3) * 0.12;
            if (bass > 0.55 && Date.now() - lastMotion > 2400) {
                lastMotion = Date.now();
                if (typeof live2dModel.motion === 'function') {
                    live2dModel.motion('tap').catch(function() {
                        live2dModel.motion('Tap').catch(function() {
                            live2dModel.motion('idle').catch(function() {});
                        });
                    });
                }
            }
        }, 90);
    };

    global.stopLive2DBeatDance = function() {
        stopBeatDanceInternal();
        if (live2dModel) startIdleMotion(live2dModel);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', hookCharacterSwitch);
    } else {
        hookCharacterSwitch();
    }
}(window));
