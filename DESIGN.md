---
name: Modern Observatory
colors:
  surface: '#131410'
  surface-dim: '#131410'
  surface-bright: '#393935'
  surface-container-lowest: '#0e0f0b'
  surface-container-low: '#1b1c18'
  surface-container: '#1f201c'
  surface-container-high: '#2a2a26'
  surface-container-highest: '#353530'
  on-surface: '#e4e2dc'
  on-surface-variant: '#d5c3b5'
  inverse-surface: '#e4e2dc'
  inverse-on-surface: '#30312c'
  outline: '#9d8e81'
  outline-variant: '#50453a'
  surface-tint: '#f6bb7e'
  primary: '#f6bb7e'
  on-primary: '#492900'
  primary-container: '#bb874f'
  on-primary-container: '#412400'
  inverse-primary: '#815522'
  secondary: '#ffb4a6'
  on-secondary: '#5a1b10'
  secondary-container: '#783024'
  on-secondary-container: '#fe9b88'
  tertiary: '#b4c9dc'
  on-tertiary: '#1e3241'
  tertiary-container: '#7f94a6'
  on-tertiary-container: '#182c3b'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdcbc'
  primary-fixed-dim: '#f6bb7e'
  on-primary-fixed: '#2c1700'
  on-primary-fixed-variant: '#653e0b'
  secondary-fixed: '#ffdad4'
  secondary-fixed-dim: '#ffb4a6'
  on-secondary-fixed: '#3d0601'
  on-secondary-fixed-variant: '#783024'
  tertiary-fixed: '#d0e5f9'
  tertiary-fixed-dim: '#b4c9dc'
  on-tertiary-fixed: '#071d2c'
  on-tertiary-fixed-variant: '#354959'
  background: '#131410'
  on-background: '#e4e2dc'
  surface-variant: '#353530'
typography:
  display-lg:
    fontFamily: Newsreader
    fontSize: 48px
    fontWeight: '400'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Newsreader
    fontSize: 32px
    fontWeight: '400'
    lineHeight: 40px
    letterSpacing: -0.01em
  display-md:
    fontFamily: Newsreader
    fontSize: 36px
    fontWeight: '400'
    lineHeight: 44px
    letterSpacing: -0.015em
  headline-lg:
    fontFamily: Newsreader
    fontSize: 28px
    fontWeight: '400'
    lineHeight: 36px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Newsreader
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 30px
    letterSpacing: 0em
  body-lg:
    fontFamily: Public Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: 0.01em
  body-md:
    fontFamily: Public Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0.01em
  body-sm:
    fontFamily: Public Sans
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.02em
  label-data:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.04em
  label-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
    letterSpacing: 0.08em
  label-system:
    fontFamily: Public Sans
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.08em
spacing:
  gutter: 1.5rem
  gutter-mobile: 0.75rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style
The design system embodies the discipline of an orbital research station combined with the cerebral typography of a scientific journal. Designed for astrophysicists, planetary defense researchers, and data engineers, the interface evokes focus, credibility, and absolute observational accuracy.

It rejects modern SaaS tropes: no diffused purple glows, no floating glassmorphism, no playful rounded pills, and no arbitrary decorative motion. Instead, it relies on structural grid architecture, hairline technical rules, clear tabular layouts, and purposeful editorial hierarchy. The emotional experience is one of sitting at a deep-space sensor terminal late at night: calm, quiet, high-density, and uncompromisingly rigorous.

## Colors
The palette is rooted in astronomical observation environments where high-contrast legibility and dark-adaptation are paramount.

- **Primary Background (`#0C131B`)**: Deep void canvas mimicking deep space; minimizes ocular strain during extended telemetry analysis.
- **Surface Elevation (`#141F2B`)**: Deep muted slate for containment panels, sidebars, and analytical viewports.
- **Structural Stroke (`#233746`)**: Hairline borders, divisional axis lines, and crosshair reticles. Never thick; strictly 1px.
- **Editorial Foreground (`#EDEBE4`)**: Warm ivory for primary typography, editorial titles, and high-priority metrics. Replaces harsh pure white with warmth that aids reading endurance.
- **Telemetry Muted Text (`#A8B2BC`)**: Muted bone for technical descriptors, axis numbers, and contextual metadata.
- **Primary Observation Accent (`#BB874F`)**: Restrained warm amber, echoing incandescent telemetry lamps. Used for targeted filters, selection boundaries, active orbital vectors, and primary CTAs.
- **Hazard Indicator (`#BD6656`)**: Muted terrestrial red reserved exclusively for confirmed hazardous classifications, high-uncertainty flags, and trajectory collision probabilities.

## Typography
Typography is divided across three distinct communicative roles:

1. **Newsreader (Editorial Serif)**: Provides intellectual presence, historical continuity, and gravitas. Employed for paper titles, asteroid dossier names, section headers, and analytical summaries.
2. **Public Sans (Technical UI Sans)**: Offers transparent, geometric legibility for navigation, filter controls, table headers, and functional system instructions.
3. **JetBrains Mono (Telemetry Monospace)**: Enforces rigid tabular alignment for astronomical coordinates (Right Ascension/Declination), semi-major axes, eccentricities, absolute magnitudes ($H$), and UTC timestamps. All numerical observations must use `font-variant-numeric: tabular-nums`.

## Layout & Spacing
The layout follows an instrument-panel paradigm structured along a 12-column fixed-gutter modular grid. 

- **Desktop (1280px+)**: Multi-pane layout. Navigation and temporal scrubbers anchor to the left or bottom; primary analytical viewport occupies the central 8-9 columns; secondary dossier metadata and classification parameters occupy the remaining 3-4 columns.
- **Tablet (768px - 1279px)**: Responsive collapse into an 8-column layout. Metric readouts stack directly above the primary orbit visualization.
- **Mobile (< 768px)**: 4-column layout with vertical flow. Coordinates and orbital data convert into linear key-value rows.
- **Rhythm**: Element padding adheres strictly to multiples of `0.25rem` (`space-xs`). Whitespace around long-form text mirrors print periodicals with uncrowded margins, whereas data matrices compress to `0.5rem` (`space-sm`) padding to preserve vertical density.

## Elevation & Depth
Depth in this design system is non-spatial. It avoids physical drop-shadows and blurred glass layers entirely. Depth is communicated strictly via **tonal stacking** and **structural hairline rules**:

- **Ground (Canvas)**: `#0C131B` (Absolute zero point).
- **Sub-panel / Viewport Tier**: `#141F2B`, framed with a continuous `1px solid #233746` stroke.
- **Overlay Dialogues & Flyouts**: `#141F2B`, bordered by `1px solid #BB874F` when focused, or `1px solid #233746` when resting, accompanied by an opaque 2px offset keyline rather than a diffused blur.
- **Ticks & Reticles**: Subtle SVG corner crosshairs (`+`) rendered in `#233746` are placed at the intersections of panels and tables to reinforce the appearance of physical collimation grids.

## Shapes
Shapes are uncompromisingly sharp (`roundedness: 0`). 

No element receives curved border radii. Radii on cards, input boxes, badges, and action buttons are set strictly to `0px`. This geometric severity honors vintage scientific apparatus, early command-line ephemeris compute systems, and high-precision physical plotting boards.

## Components

### Action Buttons
- **Primary**: Solid background `#BB874F`, text `#0C131B` in uppercase `JetBrains Mono` (`label-data`), `0px` radius, hover state dims to `#9E6F3E` with zero transition bounce.
- **Secondary / Scientific**: Background `#141F2B`, border `1px solid #233746`, text `#EDEBE4`. Hover state promotes the border to `1px solid #A8B2BC`.
- **Destructive / Hazard Classify**: Background transparent, border `1px solid #BD6656`, text `#BD6656`.

### Chips & Classification Indicators
- Rendered with monospace labels in all-caps (`label-mono-sm`).
- **Nominal Body**: `1px solid #233746`, background `#0C131B`, text `#A8B2BC`.
- **Potentially Hazardous Asteroid (PHA)**: `1px solid #BD6656`, background `rgba(189, 102, 86, 0.12)`, text `#BD6656`, prefixed with a unicode marker `[!]`.
- **Observation Candidate**: `1px solid #BB874F`, background `rgba(187, 135, 79, 0.12)`, text `#BB874F`.

### Data Matrices & Tables
- Table headers use `Public Sans` uppercase (`label-system`), text `#A8B2BC`, with bottom border `1px solid #233746`.
- Data rows use `JetBrains Mono` (`label-data`), height `36px`, cell padding `0.5rem 1rem`.
- Row dividers are hairline strokes (`rgba(35, 55, 70, 0.5)`).
- Alternate row striping is prohibited; subtle hover highlights (`rgba(35, 55, 70, 0.25)`) indicate row focus.

### Input Fields & Selectors
- Background `#0C131B`, border `1px solid #233746`, text `#EDEBE4`, padding `0.5rem 0.75rem`.
- Focus state: border turns to `1px solid #BB874F` with zero glow.
- Numeric inputs (e.g., perihelion distance, epoch filter) strictly render in monospace.

### Checkboxes & Segmented Switches
- Checkboxes: Square `14px x 14px`, border `1px solid #233746`, interior fills solid `#BB874F` when checked with an inner `2px` black inset border.
- Segmented switches: Contained bar with `1px solid #233746`, inactive segments `#141F2B`, active segment `#233746` with `#EDEBE4` text.

### Observational Dossier Cards
- Background `#141F2B`, continuous `1px solid #233746` boundary.
- Panel headers feature a two-part title: a Newsreader serif title paired with a JetBrains Mono tracking ID (e.g., `(99942) Apophis // MPC-7402`).
- Four-corner reticle marks (`L`-shaped markers, 4px arm length) sit at card boundaries to anchor scientific visualization charts.