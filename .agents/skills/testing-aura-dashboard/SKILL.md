---
name: testing-aura-dashboard
description: How to run and UI-test the AURA-MAS Next.js dashboard locally (scenarios, alerts, acknowledge/dismiss actions, responsive layout measurement).
---

# Testing the AURA-MAS dashboard

No credentials are needed; everything runs locally.

## Bring the app up
```bash
docker compose up -d          # from repo root: Redis + Mosquitto
cd frontend && npm install && npm run dev   # http://localhost:3000
curl -s localhost:3000/api/status           # expect {"mqtt":...,"redis":true}
```
- Default scenario comes from `AURA_SCENARIO` or `combined_audio_video_01`
  (`frontend/src/app/page.tsx`, `frontend/src/app/api/scenario/route.ts`);
  manifests live in `<repo>/scenarios/`, media/evidence/alerts in `<repo>/data/`.
- `/api/alerts` GET reads the Redis stream first and falls back to
  `data/alerts_*.jsonl`, so incidents appear even without Redis. The POST path
  (acknowledge / dismiss) needs Redis for the audit write and status overlay —
  without Redis it can 503, so start docker compose before testing those buttons.
- MQTT live streaming is not exercised by simply starting the broker (no replay
  publisher runs), so treat live-event tests as untested unless you start one.

## UI test hints
- Incidents rail (right column) → click a row to populate IncidentDetail; the
  Acknowledge / Dismiss buttons only enable while `status === "OPEN"`.
  Successful acknowledge flips the header tag and rail row to `ACKNOWLEDGED`,
  disables both buttons, and decrements `OPEN ALERTS` in the StatusBar.
- Alert statuses persist in Redis, so already-acknowledged rows stay
  acknowledged across reloads — pick a fresh `OPEN` row for each action test.

## Measuring responsive layout objectively
Resize the real Chrome window with `wmctrl -r :ACTIVE: -b add,maximized_vert,maximized_horz`
(or explicit `wmctrl -r :ACTIVE: -e 0,0,0,W,H`) for desktop widths, and use
DevTools device toolbar (F12 then Ctrl+Shift+M) for 768px / 390px. Then read
geometry with a read-only console snippet, e.g.:
```js
const t = document.querySelector('.corner-frame').getBoundingClientRect();
const ack = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Acknowledge');
```
Useful checks: camera tile `bottom <= detail.top` (no overlap), tile
`height/width ≈ 0.5625` on stacked views but larger on `lg` (tile fills its grid
row), `document.elementFromPoint(ackCenter)` returns the button (not covered),
detail body `scrollHeight > clientHeight` with footer rect y unchanged after a
wheel scroll, and `scrollingElement.scrollWidth <= viewportWidth` for no
horizontal overflow.

To prove a layout regression is really fixed, check out the parent of the fix
commit for just the changed files, let `next dev` hot-reload, screenshot the
broken state, then `git checkout HEAD -- <files>` to restore.

## Devin Secrets Needed
None.
