/**
 * Live2D VTuber Engine — PixiJS 7 + pixi-live2d-display
 * Breathing, head sway, blink, physics, safe switch, PNG fallback
 */
(function(global) {
    'use strict';

    var MODEL_PATHS = {
        shiro: '/static/live2d/shiro/shiro.model3.json',
        sishin: '/static/live2d/sishin/sishin.model3.json'
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
        return global.Live2DModel || null;
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
        return document.querySelector('.avatar-container');
    }

    function ensureLive2DEngine() {
        var Live2DModel = getLive2DModelClass();
        if (typeof global.PIXI === 'undefined' || !Live2DModel) {
            return Promise.reject(new Error('Live2D SDK not loaded'));
        }

        if (engineReady && live2dApp) {
            return Promise.resolve(live2dApp);
        }

        var container = getContainer();
        if (!container) {
            return Promise.reject(new Error('Live2D container missing'));
        }

        if (Live2DModel.registerTicker && global.PIXI.Ticker) {
            Live2DModel.registerTicker(PIXI.Ticker.shared);
        }

        try {
            if (live2dApp) {
                destroyLive2DModel();
                live2dApp.destroy(true, { children: true, texture: true, baseTexture: true });
                live2dApp = null;
                container.innerHTML = '';
            }

            live2dApp = new PIXI.Application({
                backgroundAlpha: 0,
                antialias: true,
                autoDensity: true,
                resolution: Math.min(global.devicePixelRatio || 1, 2),
                resizeTo: container
            });

            container.appendChild(live2dApp.view);
            live2dApp.view.style.width = '100%';
            live2dApp.view.style.height = '100%';
            live2dApp.view.style.display = 'block';

            if (global.ResizeObserver && !resizeObserver) {
                resizeObserver = new ResizeObserver(function() {
                    layoutModel();
                });
                resizeObserver.observe(container);
            }

            global.addEventListener('resize', layoutModel);
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
        var avatar = document.getElementById('homeAvatar');

        if (container) container.classList.remove('active');
        if (wrap) wrap.classList.remove('live2d-active');

        if (avatar) {
            avatar.style.opacity = '';
            avatar.style.visibility = '';
            avatar.style.pointerEvents = '';
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
        if (container) container.classList.add('active');
        if (wrap) wrap.classList.add('live2d-active');
        live2dReady = true;
    }

    function layoutModel() {
        if (!live2dModel) return;
        var container = getContainer();
        if (!container) return;

        var w = container.clientWidth || 320;
        var h = container.clientHeight || 400;
        var scale = Math.min(w / 520, h / 680) * 0.92;
        scale = Math.max(0.14, Math.min(scale, 0.42));

        live2dModel.anchor.set(0.5, 0.92);
        live2dModel.scale.set(scale);
        live2dModel.x = w * 0.5;
        live2dModel.y = h * 0.96;
    }

    function stopProceduralIdle() {
        if (idleTickerBound && global.PIXI && PIXI.Ticker && PIXI.Ticker.shared) {
            PIXI.Ticker.shared.remove(idleTickerBound);
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
        if (global.PIXI && PIXI.Ticker && PIXI.Ticker.shared) {
            PIXI.Ticker.shared.add(idleTickerBound);
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
        var groups = ['Idle', 'idle', 'TapBody', 'tap'];
        var started = false;

        function tryMotion(name) {
            if (started || !model || typeof model.motion !== 'function') return;
            model.motion(name, undefined, 1).then(function() {
                started = true;
            }).catch(function() {});
        }

        for (var i = 0; i < groups.length; i++) {
            tryMotion(groups[i]);
        }

        try {
            if (model.internalModel && model.internalModel.motionManager) {
                model.internalModel.motionManager.startRandomMotion('Idle', undefined, 3);
                started = true;
            }
        } catch (e) { /* model may lack Idle motions */ }
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
        return fetch(path, { method: 'HEAD', cache: 'no-store' }).then(function(res) {
            if (!res.ok) throw new Error('Model not found: ' + path);
            return path;
        });
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
            for (var i = 0; i < outfits.length; i++) {
                if (outfits[i].id === 'live2d' && outfits[i].modelPath) {
                    path = outfits[i].modelPath;
                    break;
                }
            }
        }

        var token = ++loadToken;

        destroyLive2DModel();

        return ensureLive2DEngine().then(function() {
            if (token !== loadToken) return false;
            return validateModelPath(path);
        }).then(function(validPath) {
            if (!validPath || token !== loadToken) return null;
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
                live2dApp.stage.addChild(model);
                layoutModel();
                startIdleMotion(model);
                startProceduralIdle();
                applyLive2DVisible();
                console.log('[Live2D] VTuber model ready:', karakter);
                return true;
            })
            .catch(function(err) {
                console.warn('[Live2D] fallback PNG —', err && err.message ? err.message : err);
                if (token === loadToken) {
                    destroyLive2DModel();
                    applyPngFallback(karakter);
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
                applyPngFallback(char);
            });
    };

    global.deactivateLive2DFromWardrobe = function(char) {
        char = normalizeChar(char);
        wardrobeLive2DMode = false;
        destroyLive2DModel();
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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', hookCharacterSwitch);
    } else {
        hookCharacterSwitch();
    }
}(window));
