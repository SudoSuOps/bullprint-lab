# art/ — print files, generated from vector

Printful fetches print files from a public URL and wants **300 DPI**. It refuses
below 150. Every raster master we were handed is far under that:

| master | pixels | DPI at 8in | verdict |
|---|---|---|---|
| bull-head-mascot.png | 180 x 180 | 22 | unusable |
| bull-btc-gold.png | 499 x 515 | 62 | unusable |
| pinback-sendit.png | 214 x 231 | 27 | unusable |
| pinback-est2024.png | 244 x 244 | 30 | unusable |

Those files are fine on a web page at 118 px wide. They are not artwork.

The way out is that the marks are **vector**. `svg/` holds them, lifted verbatim
from `design_handoff_bullprint_lab/assets/marks.svg.txt`, and vector rasterises
to any size:

```bash
rsvg-convert -w 2400 -f png -o print/bull-8in.png svg/bull-linecut.svg   # 300 DPI at 8in
```

Verified: 2400 x 2000 RGBA out of a 120 x 100 viewBox — exactly 300 DPI at 8
inches, transparent background, no resampling anywhere.

Text needs the real typefaces installed for fontconfig, not the woff2 the site
serves. Archivo, JetBrains Mono and Saira Stencil One are in `~/.fonts`.

## What this changes about the merch sheet

The sheet marks T-06 and T-07 as the DTG pair and T-01 to T-05 as screen print.
The art inverts that: T-01, T-03, T-04 and T-05 are vector and can be printed at
any size today. T-06 and T-07 are the two whose only masters are the raster
files in the table above, so they are the two that cannot be printed yet.

T-06 is recoverable — its mascot IS the bull, and the bull is vector. T-07 is a
rendered 3D piece with no vector source; it needs a high-resolution export from
wherever it was made.
