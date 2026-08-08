# Mercury — Style Reference
> Alpine banking at blue hour

**Theme:** dark

Mercury operates in an alpine banking aesthetic: a near-black canvas (#171721) sets a cinematic, observatory-like atmosphere where content surfaces float as subtly lighter graphite cards. The interface is overwhelmingly monochromatic — ivory text on onyx, with a single vivid cobalt (#5266eb) acting as the only chromatic punctuation, reserved exclusively for the primary action. Typography carries the weight of expression: a custom display face at intermediate weight 480 (neither bold nor light) paired with a refined body face at weight 400, creating a voice that is confident but never loud. Components are flat and borderless, relying on the 12px-radius graphite card lift and pill-shaped controls to define structure rather than shadows.

Source: https://styles.refero.design/style/3172cd4d-118a-4a16-a259-6b634d32322e (mercury.com)

## Tokens — Colors

| Name | Value | Token | Role |
|------|-------|-------|------|
| Onyx Canvas | `#171721` | `--color-onyx-canvas` | Dominant page background |
| Graphite Card | `#1e1e2a` | `--color-graphite-card` | Elevated card surfaces — one step lighter than canvas |
| Obsidian Button | `#272735` | `--color-obsidian-button` | Secondary button fills, inline form backgrounds |
| Slate Border | `#70707d` | `--color-slate-border` | Medium-weight dividers and structural borders |
| Mist Border | `#e2e3ed` | `--color-mist-border` | Light hairline borders, ghost-button outlines, input edges |
| Ash Text | `#c3c3cc` | `--color-ash-text` | Muted body copy, helper text, secondary labels |
| Ivory Text | `#ededf3` | `--color-ivory-text` | Primary text, icons, nav items |
| Cobalt | `#5266eb` | `--color-cobalt` | The single chromatic action color |
| Pure White | `#ffffff` | `--color-pure-white` | Text/icon fill on cobalt buttons only |

Adapted for this project: since we're a dense data/technical tool (not a marketing site), we
additionally use small semantic accents *within* the technical panel only — muted green/amber/red
for pass/warn/fail badges (grounding score, guardrail flags, circuit breaker state) — Mercury's
"one accent only" rule is relaxed there because the panel's whole job is to communicate status at
a glance. The chat surface itself stays true to the single-cobalt-accent rule.

## Typography

- Body/UI: Inter (Mercury's `arcadia` substitute), weights 400/500/600
- Display/headings: Inter with `font-optical-sizing`, weight ~500-600 standing in for `arcadiaDisplay` 480
  (no license for the real faces, so we approximate the "intermediate weight, never bold" voice with Inter 500/600 and tight tracking)
- Monospace (technical panel only — token counts, costs, latencies, model ids): `ui-monospace, "JetBrains Mono", "SF Mono", monospace`
- Body: 16px / 1.5 line-height
- Headings: 480-weight equivalent (Inter 550), tight line-height 1.15, positive letter-spacing 0.01–0.02em

## Spacing & Shape

- Base unit: 4px
- Card radius: 12px · Button/input radius: 32px (pill) · Small tag radius: 40px (pill) · Structural default: 4px
- Card padding: 32px (24px in dense technical panel context) · Section gap: 72px (desktop), collapses on smaller viewports

## Do / Don't (carried over from source, adapted)

- Cobalt is the only chromatic accent on the chat surface — no other bright colors there.
- No drop shadows — separation via value contrast (#1e1e2a card on #171721 canvas) and hairline borders only.
- Pill radius non-negotiable on buttons/inputs/nav/tags; sharp corners reserved for structural containers (tables, code blocks).
- No pure white body text — always Ivory `#ededf3`.
- Headings never bold (700+) — cap around Inter 600.
