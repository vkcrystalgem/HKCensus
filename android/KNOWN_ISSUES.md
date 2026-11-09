# Native visual QA follow-up

## Supporting charts overflow narrow phone cards

Observed on 9 November 2026 in GitHub-built review version 1.0.1 (code 3), source `76e317610a874694cc31eaa86330c460bdbac829`, on the task-owned 1080 × 1920 Android API 28 phone emulator at 420 dpi.

Scroll to the Unemployment cycle section's Recent cycle and Shock snapshots supporting cards. The small chart backgrounds and geometry extend outside their columns; the right-hand chart is clipped at the screen edge. This is a moderate layout defect. The primary interactive charts fit correctly, and the listing's six phone captures show the intact primary views.

`MiniLineChart.tsx` and `MiniBarChart.tsx` use a fixed 240-dp SVG width, while `SectionCard.tsx` lays out supporting cards at 47% width. A follow-up should make the supporting charts respond to their measured card width or stack the cards on narrow screens, then verify both chart types on phone and tablet layouts.

An untouched native QA capture is retained locally at `android/.tooling/store-listing-captures/phone/qa-support-chart-overflow.png`, SHA-256 `fd8295eecc9f675058e440c5c4aec5639d65e5381f5b1c568790e76a2cee8ed5`. It is excluded from the listing packet. This issue was recorded, not fixed, during listing preparation.
