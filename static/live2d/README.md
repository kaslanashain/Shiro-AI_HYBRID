# Live2D Cubism 3/4 — VTuber Home Screen



## Folder structure



```

static/live2d/

  shiro/

    shiro.model3.json

    shiro.moc3

    shiro.physics3.json    ← hair & nekomimi bounce (recommended)

    shiro.cdi3.json

    textures/

      *.png

  sishin/

    sishin.model3.json

    ...

```



## Model paths (used by `static/js/live2d.js`)



| Character | Model |

|-----------|--------|

| Shiro | `static/live2d/shiro/shiro.model3.json` |

| Sishin | `static/live2d/sishin/sishin.model3.json` |



## Features (engine)



- PixiJS 7 + pixi-live2d-display (CDN in `index.html`)

- Procedural idle: breathing, head sway, random blink

- Cubism **physics** enabled when `*.physics3.json` is bundled with model

- Lip-sync hooks for TTS (`startLive2DLipSync` / `stopLive2DLipSync`)

- Safe destroy on character switch (no canvas overlap / leaks)

- **PNG fallback** if model missing:

  - Shiro → `static/images/shiro.png`

  - Sishin → `static/images/sishin.png`



## Get sample models



1. [Live2D Sample Data](https://www.live2d.com/en/download/sample-data/)

2. Export from Cubism Editor 3/4

3. Place files in folders above



## CDN (already in index.html)



- Cubism Core

- PixiJS 7

- pixi-live2d-display 0.5.0



## Init



`initLive2D()` runs on DOM ready (~600ms after load). Character switches via `CharacterState` reload the model automatically.

