# SAPGUN Dynamic Developer Profile System

The profile is intentionally split into three layers.

## 1. Brand / information architecture

Static SVG assets define identity and reading order:

- `assets/hero.svg`
- `assets/capability-map.svg`
- `assets/quadrant.svg`
- `assets/stack.svg`
- `assets/sections/*.svg`

These should change only when positioning or visual design changes.

## 2. Career-signal configuration

`data/profile.json` is the source of truth for what the dynamic layer is allowed to promote.

Key fields:

- `signal_repositories` — repositories allowed into the live engineering signal
- `research_repositories` — repositories allowed to become the latest research signal
- `release_repositories` — repositories checked for tagged releases
- `featured_projects` — project-card order, status boundary and editorial summary

This prevents unrelated utility or legacy repositories from taking over the profile merely because they were updated recently.

A repository listed in configuration but not public yet is ignored by the generator. This is deliberate: future labs can be wired before they are published without falsely presenting them as completed work.

## 3. Dynamic evidence

`scripts/update_profile.py` reads public GitHub metadata and generates:

- `assets/dynamic/project-deck.svg`
- `assets/dynamic/output-feed.svg`
- `assets/dynamic/public-signal.svg`
- the `OUTPUT-FEED` block in `README.md`
- the `PUBLIC-ACTIVITY` block in `README.md`

The workflow runs daily, can be dispatched manually, and also runs when the generator or profile configuration changes.

## Adding a new flagship repository

1. Make the repository public only when its public surface is ready.
2. Add its name to `signal_repositories`.
3. If it is research, add it to `research_repositories`.
4. If releases should be surfaced, add it to `release_repositories`.
5. Add a `featured_projects` entry only when it deserves a permanent evidence card.
6. Keep status language factual: `Prototype`, `Published`, `Private Core / Public Surface`, `Design`, or another accurate boundary.
7. Run the workflow and inspect the README in both GitHub light and dark themes.

## Planned public surfaces

The current profile is ready to ingest these names when they exist:

- `defi-protocol-design-lab`
- `onchain-protocol-research`
- `vespera-spec`

Until they are public, they remain planning signals in the README rather than generated evidence.

## Design rule

The profile should optimize for this sequence:

**Positioning → evidence → research depth → live activity**

Decoration is secondary. Generated metrics should support the career narrative, not replace it.
