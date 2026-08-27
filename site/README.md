# AWAKENED: ZERO RANK Observer

The production observer is a read-only window into Ren Takahashi's deterministic simulation. It renders authenticated static artifacts and never exposes controls that can alter Ren, the world, or simulation time.

The completed observer surface presents current needs and intent, decision outcomes and reasons, hunter progression, equipment, finances, story history, relationships, current whereabouts, a collapsible read-only Tokyo atlas, portal investigations, and key memories from the same authenticated snapshot.

## Requirements

- Node.js 22.13 or newer
- Observer artifacts in `public/data/`

## Local development

```powershell
npm install
npm run dev
```

Use `npm run lint` for source checks and `npm test` for the production build plus rendered observer tests.

## Trusted data boundary

The page downloads `observer-contract.json` and `observer-snapshot.json` together with cache reuse disabled. Browser-side runtime guards validate every rendered field before canonical SHA-256 verification. An invalid first load fails closed; a transient refresh failure keeps the last verified chronicle visible.

Publish a new pair from the repository root:

```powershell
awakened-zero-rank --publish-observer-site-data saves/ren.json site/public/data
awakened-zero-rank --verify-observer-site-data site/public/data
```

Publication is atomic and non-overwriting. Prepare a fresh destination when replacing a deployed pair.

## Product constraints

- The site remains observer-only.
- No pause, speed, seed, reset, save, or action controls belong in this surface.
- Simulation and story rules stay in the Python package.
- Presentation code consumes the versioned observer contract instead of duplicating simulator rules.
- Reduced-motion preferences and keyboard navigation must remain supported.
- Responsive phone, tablet, desktop, print, and increased-contrast layouts are part of the production surface.
- Live artifact responses must remain non-cacheable and every response retains the observer security headers.

## Project map

- `app/page.tsx`: verified refresh lifecycle and observer presentation
- `app/observer-data.ts`: runtime guards, canonical JSON, and artifact verification
- `app/layout.tsx`: production metadata and document shell
- `public/data/`: checked-in deterministic demonstration artifacts
- `tests/rendered-html.test.mjs`: production-render and trust-boundary regression tests
- `.openai/hosting.json`: private Sites project binding

## Deployment

The observer is built with vinext for the managed Sites runtime. Deploy only a clean, tested commit whose packaged `dist/` output and source revision match. Production access remains private unless the owner explicitly approves a different access policy.

The managed Sites version history is the rollback boundary. If a deployment fails verification, keep the last authenticated deployment live and publish a new tested version rather than editing production in place.
