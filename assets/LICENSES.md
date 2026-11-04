# Licenses of third-party material in the visuals

The README visuals (`assets/*.svg`, `assets/social-preview.png`,
`media/linkedin-demo.mp4`) are built by `scripts/visuals/` from the files in
`assets/src/`. They embed subsets of two fonts and draw a few brand logos.

## Fonts (SIL Open Font License 1.1)

| Font | Files | Source | License |
|---|---|---|---|
| Instrument Sans | `assets/src/fonts/instrument-sans-latin-{400,600,700}-normal.woff2` | [@fontsource/instrument-sans](https://fontsource.org/fonts/instrument-sans) 5.3.0 | OFL-1.1, `assets/src/fonts/OFL-InstrumentSans.txt` |
| IBM Plex Mono | `assets/src/fonts/IBMPlexMono-{Regular,SemiBold}.ttf` | [google/fonts](https://github.com/google/fonts/tree/main/ofl/ibmplexmono) | OFL-1.1, `assets/src/fonts/OFL-IBMPlexMono.txt` |

The SVGs embed glyph subsets of these fonts (base64 WOFF2), as the OFL allows
for embedding in documents. The full IBM Plex Mono is used because the
smaller "latin" web subset has no box-drawing characters.

## Logos (Simple Icons, CC0 1.0)

`assets/src/icons/*.svg` come from [Simple Icons](https://simpleicons.org)
16.36.0 (npm `simple-icons`), released under CC0 1.0
(`assets/src/icons/LICENSE-simple-icons.md`). They are used on the method
ladder to show which kind of source each rung reads: Shopify, WooCommerce,
WordPress, RSS, JSON, Next.js, Nuxt, HTML5, Python, Google Chrome.

The icon *drawings* are CC0, but the logos are trademarks of their owners.
They appear here only to name the technology a method reads (nominative use);
no endorsement by any of them is implied.

## Everything else

The terminal output inside the SVGs and the MP4 is rendered by scrapeplanner
itself from a committed run under `checks/results/` (MIT, like the rest of the
repository).
