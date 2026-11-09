# HK Census store artwork sources

The icon and feature graphic are original geometric artwork created for this repository. No stock imagery, downloaded illustrations, generative raster imagery, government emblems, building photographs, or third-party logos were used.

## Files for Play Console

| Asset | Upload file | Pixel dimensions | Colour |
| --- | --- | --- | --- |
| App icon | `graphics/app-icon-512.png` | 512 × 512 | 32-bit RGBA PNG, all alpha 255, embedded sRGB |
| Feature graphic | `graphics/feature-graphic-1024x500.png` | 1024 × 500 | Opaque 24-bit RGB PNG, embedded sRGB |

An additional Android launcher asset, `graphics/adaptive-icon-foreground.png`, is a 1024 × 1024 RGBA PNG with transparent padding. It is regenerated directly from the same skyline and trend geometry, not derived from either PNG. Use it over adaptive background `#0F766E`. Every nontransparent pixel lies within a circle centred on the canvas with diameter 66% of the image, leaving space for Android's mask and motion treatment. Its editable SVG companion is included. This foreground is an app build input, not a Play Console listing upload.

The icon is a full-bleed square with no baked-in rounded corners, mask, shadow, badge, or lettering. Google Play applies its own icon treatment. The main mark has generous inset margins and is intended to remain recognizable at small sizes.

The format follows Google's current [Play icon design specifications](https://developer.android.com/distribute/google-play/resources/icon-design-specifications) and [Play Console preview asset requirements](https://support.google.com/googleplay/android-developer/answer/9866151), checked 9 November 2026: a 512 × 512, 32-bit PNG with alpha, sRGB, at most 1024 KB. The alpha channel is present and fully opaque, preserving the full teal square background.

The feature graphic uses only the app name and the line “Explore the long view.” All essential artwork and text is inset by at least 24 pixels. The skyline and lines are decorative brand geometry, not screenshots, exact statistical values, representations of a financial return, or a claim of government affiliation.

## Design

The palette follows the app’s warm paper, dark ink and teal interface: paper `#F2ECDF`, cream `#FFF8EE`, ink `#1D1D1B`, teal `#0F766E`, and gold `#A16207`. Deep teal `#0B625C`, pale gold `#E7BD78`, and muted supporting tones extend the palette for contrast and hierarchy.

The abstract skyline combines stepped low-rise shapes, an angular tower and a narrow high-rise. A rising, irregular signal line connects the city motif with the app’s historical charts. This is original stylization inspired by Hong Kong’s urban character, without tracing a particular image or using an official insignia.

Feature typography uses Microsoft Segoe UI Semibold and Segoe UI Regular installed with Windows. Font files are not bundled or redistributed. The PNG contains rasterized lettering. The editable SVG references `Segoe UI, sans-serif`; another machine may substitute its own font if Segoe UI is unavailable.

## Reproduction and verification

Editable sources are the adjacent `.svg` files. `graphics/render_graphics.py` renders both SVG and PNG from the same explicit geometry, using Pillow and the Windows Segoe UI fonts. It renders at four times the target resolution and downsamples with Lanczos. The store icon is fully opaque RGBA, the feature graphic is opaque RGB, and the adaptive foreground is RGBA with transparent padding. Each has an embedded sRGB profile. ICC creation metadata is fixed to keep output reproducible with the same Pillow and font versions.

From the repository root:

```powershell
python store-listing/graphics/render_graphics.py
```

The script writes `graphics/graphics-validation.json`, checks exact dimensions, RGB/RGBA colour mode, icon alpha opacity, embedded colour profile and file-size ceilings (1 MiB icon; 15 MiB feature graphic), and records each PNG’s size and SHA-256 hash. The final PNGs were also visually inspected at native dimensions, with the icon checked at 48 and 96 pixels.

The graphic renderer also checks the adaptive foreground's dimensions, transparency and central safe circle. `graphics/qa/` contains inspection previews only; do not upload those previews to the listing.

Creating these assets alone does not update an installed app or publish a listing. The app configuration now references the store icon and adaptive foreground, so the next app build will use this identity. Listing uploads and app distribution remain separate actions.
