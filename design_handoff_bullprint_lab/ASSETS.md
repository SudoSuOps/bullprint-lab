# BullPrint Lab — Brand Asset Kit

Source of truth is **assets/vector/** — everything else is an export.

## Vectors (assets/vector/)

| file | use | notes |
|---|---|---|
| bull-modelled.svg | hero, seals, >=40px | gradient fill, no text — rasterizes anywhere |
| bull-linecut-gold.svg | <=32px, favicon, emboss, dark blanks | single stroke #E8B23A |
| bull-linecut-black.svg | light blanks, 1-color print | single stroke #141414 |
| seal-genesis.svg | THE seal, >=280px / >=40mm | genesis hash ring + name ring + line bull |
| seal-small.svg | <=120px stamp | ring + bull only, no text by design |
| bullish-lockup-gold.svg | slide engraving, T-02 tee, drops | Saira B + bar pairs 2.0x5.0 through the bowls |

**Rasterizer rules:**
- textPaths carry BOTH `xlink:href` and `href` — rsvg-convert ignores bare `href`.
- Install fonts before rasterizing text-bearing vectors: **JetBrains Mono** (500, 700), **Saira Stencil One** (400). No font = empty rings.
- Letter-spacing is baked in px (hash ring 4.464px at 7.2px = the .62em ring closure — do not retune).
- assets/print/ PNGs have all text baked — use those when the pipeline can't guarantee fonts.

## Print PNGs (assets/print/)

Transparent, baked from the vectors in a font-loaded browser.

| file | px | covers |
|---|---|---|
| seal-genesis-2400.png | 2400 sq | 9in seal at 267 DPI, 8in at 300 |
| bull-modelled-1920.png | 1920 w | 8in at 240 DPI |
| bull-linecut-gold-1920.png | 1920 w | 11in back print at 175 DPI |
| bull-linecut-black-1920.png | 1920 w | same, light blanks |
| bullish-lockup-gold-2560.png | 2560 w | 10.5in chest at 244 DPI |
| seal-small-1280.png | 1280 sq | stickers, 3in at 300+ |

## Raster masters — audit (supplied art, NOT print-ready)

| file | px | at print size | action |
|---|---|---|---|
| bull-head-mascot.png | 180 | 22 DPI @8in | regenerate >=1200px, ideally 2400 |
| bull-btc-gold-render.png | 499 | 50 DPI @10in | regenerate >=1500px, ideally 3000 |
| coin-best-in-bull.png | ~1100 | 146 DPI @9in | regenerate >=2700px |
| pinback-sendit.png | 214 | 30 DPI @2.25in | regenerate >=675px |
| pinback-est2024.png | 244 | 34 DPI @2.25in | regenerate >=675px |

These are AI renders — regenerate at source resolution; upscaling adds no detail. Web use is fine as-is.
