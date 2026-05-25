# TripFlow AI Web MVP

Vietnamese web MVP for drafting Hue travel itineraries.

## Run locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

## Checks

```bash
npm run lint
npm run typecheck
npm run build
```

## Scope

This MVP is frontend-only. It uses deterministic mock intent extraction, Hue POI data, local timeline generation, add/remove/undo interactions, and `localStorage` saved drafts. It does not include GPS, maps, booking, payment, auth, cloud database, real LLM calls, OR-Tools, or mobile-native active trip mode.
