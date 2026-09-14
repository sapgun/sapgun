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

### Refresh modes

The profile has three refresh paths:

1. **Near-real-time fallback** — GitHub Actions refreshes at minute `07` and `37` of every hour.
2. **Immediate receiver** — the profile repository accepts a `repository_dispatch` event with type `refresh-profile`.
3. **Manual/config refresh** — `workflow_dispatch` remains available, and changes to the profile generator/config/workflow on `main` trigger a refresh automatically.

Only generated files that actually changed are committed, so frequent checks do not create empty history noise.

### Event-driven sync from flagship repositories

For true push/release-triggered refreshes, a flagship repository can send this event to `sapgun/sapgun` after its own workflow completes:

```yaml
- name: Refresh SAPGUN profile
  env:
    GH_TOKEN: ${{ secrets.PROFILE_SYNC_TOKEN }}
  run: |
    gh api --method POST repos/sapgun/sapgun/dispatches \
      -f event_type='refresh-profile'
```

`PROFILE_SYNC_TOKEN` must be a fine-grained token or GitHub App token that can access the profile repository. Never commit the token itself. Until that credential is configured in source repositories, the 30-minute fallback keeps the profile synchronized without cross-repository secrets.

External README widgets such as GitHub Readme Stats, Streak Stats and the activity graph are fetched by GitHub when the profile renders and follow each provider's own cache policy. They are therefore independent of the generated 30-minute profile signal.

## Adding a new flagship repository

1. Make the repository public only when its public surface is ready.
2. Add its name to `signal_repositories`.
3. If it is research, add it to `research_repositories`.
4. If releases should be surfaced, add it to `release_repositories`.
5. Add a `featured_projects` entry only when it deserves a permanent evidence card.
6. Keep status language factual: `Prototype`, `Published`, `Private Core / Public Surface`, `Design`, or another accurate boundary.
7. Run the workflow and inspect the README in both GitHub light and dark themes.
8. Optionally add the `refresh-profile` dispatch step to the repository's CI/release workflow after `PROFILE_SYNC_TOKEN` is configured.

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
