# Live2D Cubism 3/4 — VTuber Home Screen

## Status (installed)

| Character | Placeholder model | Path |
|-----------|-------------------|------|
| Shiro | Haru (Live2D official sample) | `static/live2d/shiro/Haru.model3.json` |
| Sishin | Hiyori (Live2D official sample) | `static/live2d/sishin/Hiyori.model3.json` |

These are **temporary placeholders** so Live2D works immediately. Replace with custom Shiro/Sishin models when ready.

## Install / re-download samples

```bash
python scripts/install_live2d_samples.py
```

License: see [LICENSE-SAMPLES.md](./LICENSE-SAMPLES.md)

## Custom Shiro / Sishin models

Export from Cubism Editor 3/4, then either:

1. **Replace in place** — put files in `shiro/` or `sishin/` and update `modelPath` in `app/routes.py` + `static/js/live2d.js`, or  
2. **Keep filenames** — name entry file `shiro.model3.json` / `sishin.model3.json` and update paths accordingly.

Expected structure:

```
static/live2d/
  shiro/
    *.model3.json
    *.moc3
    *.physics3.json   (optional, hair/ears bounce)
    textures/
  sishin/
    ...
```

## Features (engine)

- PixiJS 7 + pixi-live2d-display (CDN in `index.html`)
- Procedural idle: breathing, head sway, random blink
- Cubism **physics** when `*.physics3.json` is bundled
- Lip-sync hooks for TTS (`startLive2DLipSync` / `stopLive2DLipSync`)
- Safe destroy on character switch
- **SVG/PNG fallback** if model missing

## How to use in app

1. Start app (`start.bat` or `python main.py`)
2. Open **Wardrobe** (Lemari)
3. Select **Live2D VTuber**
4. Avatar animates on home screen; mouth moves during TTS

## CDN (index.html)

- Cubism Core — `cubism.live2d.com`
- **PixiJS 6.5.10** (v7 tidak kompatibel dengan plugin Live2D)
- **pixi-live2d-display 0.4.0** — `dist/cubism4.min.js`
