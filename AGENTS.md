# ScamShield — shared implementation state
Updated 2026-11-21. One existing project; no duplicate copies. Preserve approved UI, animations, V1 model, Flask endpoints and security behavior.

## Architecture
- app.py: Flask HTML, POST /api/analyze, GET /api/health; JSON/body validation and security headers.
- ml/inference.py: lazily cached joblib V1 pipeline; spam score plus three-verdict policy. No inference-time training.
- ml/urls.py and ml/rules.py: offline URL hostname inspection, e-Challan references and Indian scam-pattern signals. No fetching submitted URLs. Standalone URL verdicts do not rely on SMS scores.
- templates/index.html, public/static/{app,experience,preferences}.js and style.css: real XMLHttpRequest, fictional editable examples, replayable intro, saved themes/native circular reveal, accessible inline errors, status lights, expandable details and reset. Supplied Lottie playback preserved.
- training/: offline training/evaluation; tests/: backend and minimal-DOM interaction regressions. No database, login, stored messages or external AI inference.

## Models and limitations
V1 active: UCI only, 5,159 unique records, 4,127/1,032 train/test, seed42. TF-IDF word1–2grams max18,000; balanced LR C=4. Accuracy98.4496%, precision93.0769%, recall94.5313%, F1 93.7984%; confusion [[895,9],[7,121]]. Artifact296,455bytes; SHA256 8139dc19c4e79d62013fdedeb14565a915b152cb4c1e80de09f252c8240cf7ad.
V2 experimental: UCI+Indian Telecom+6,000 Enron sample; retained12,569; train10,027/test2,542; artifact816,552bytes. Common holdout2,518: accuracy97.86%,precision97.64%,recall95.38%,F1 96.50%. Rejected because a genuine transaction scores0.9269 with no rules firing. No promotion or retraining authorized. Hindi/Hinglish accuracy and edge deployment unvalidated; scores uncalibrated; spam is not fraud.

## Production and rollback
Canonical https://scamshield-himanshurajkhowa.vercel.app. Existing project unchanged. Runtime source7253c2a; release documentation ebaa6b8. READY production dpl_513bU36Hr8RhvG2qR2yBk8ku5bwd redeployed from verified preview after promote endpoint422. Production public, preview SSO enabled. Browser SMS, fake/official URL-only and health checks passed. Keep rollback dpl_3JcbGPTV2DsdrMcpiTzyVRjxPA1d; do not delete deployments.

## Verification and efficiency
28backend tests and Node interactions pass; all JS syntax checks pass. Tests cover real prediction, URL regressions, first-click examples, replay, reset, themes, reduced motion/failure fallback. Owner verified desktop/mobile main journey. Full screen-reader/mobile theme-motion confirmation remains outstanding. Local Flask first POST758.66ms, warm100 median0.46ms/p950.54ms; warm analysis mean0.35ms. Excludes network/platform startup; hosted latency unbenchmarked.

## GitHub publication and current workflow
Public repository: https://github.com/himanshurajkhowa/scamshield. Owner manually published clean commit b14a4cb921c5bc68ebe907e6b32fa86af749ac6c; remote main verified at this SHA on 2026-11-21. Owner confirms gh CLI authentication now works. Do not retry connector writes. Publication/authentication blockers recorded in older local history are obsolete.

Owner reports submission completed. Do not submit again.

Public snapshot contains35files: permitted source, active V1 model, evaluation records, training scripts, tests, configuration, README and notices. Boxer/lock JSON, identical V1 backup and experimental V2 binary remain local only; do not publish them or the old local main history. Raw datasets, environments, caches and credentials are excluded. Dataset/player notices and NOTICE.md remain authoritative; no project-wide reuse licence has been selected. Clean-snapshot28 backend tests and interaction regressions previously passed without the optional animation JSON files.

Use a new branch based on origin/main for public changes, with a normal fast-forward push only. Never merge/push the unrelated old local main or force-push. Keep the approved production runtime, assets, ML behavior and Vercel deployment unchanged.

## Documentation cleanup — 2026-11-21
Branch docs/readme-pipelines starts from verified origin/main b14a4cb. Only README.md and AGENTS.md may change. README diagrams labelled Inference Pipeline and Training Pipeline; Models and Evaluation is a separate section. Diagram bodies, metrics, dataset attribution, licences and limitations unchanged. README has no event, university or submission references. Shell fetch encountered DNS resolution failure, not an authentication failure; the remote base was verified independently through a read-only connector request. No connector write attempted. Owner subsequently confirmed this documentation commit was pushed. The implementation entry below supersedes the earlier docs-only scope.


## Local code-quality V2 implementation — 2026-11-21
Explicit owner authorization; isolated improve/code-quality-v2 starts directly from cached clean origin/main 9d6c339f0c7613e616dda5c297104e32814edfe9. No network troubleshooting, GitHub writes/merges, Vercel actions, retraining or submission. Do not push this branch without new instructions.
Refactored app.py and ml/{inference,rules,urls}.py into readable statements and focused helpers with constants, docstrings and annotations. ml/contracts.py documents existing response dictionary shapes using TypedDict only. Artifact loading remains lazy/cached; classifier calls, output strings, thresholds, warning evaluation/deduplication order, headers and HTTP error behavior preserved. No app-factory/blueprint expansion or runtime dependency added. Double TF-IDF computation, shared URL warning-code collision and HTML500 behavior deliberately retained to avoid higher-risk changes.
Frontend app/experience state now lives in private closures with explicit frozen ScamShieldUI/ScamShieldExperience interfaces; no lexical globals shared across scripts. Example selection consolidated; constants name existing limits/timings; statements and preference code formatted. XMLHttpRequest, storage, live regions, navigation, animation behavior and visible copy preserved. CSS, templates, supplied animations/player, dependencies, models and metric records unchanged.
Regression evidence:38 backend tests pass, including43 frozen complete API/analysis/URL examples,30 mocked threshold boundaries and300 direct comparisons against original baseline source. Baseline fixtures captured before changes include exact headers/statuses/body fields and known edge defects. Existing Node interaction suite and9 independent new frontend tests pass: loading classes now tracked, network/timeout/503/non-JSON failures, rejected animation/snapshot promises, storage failure, retry and43-case baseline DOM-state parity. Shared stateful harness replaces duplicated mocks. Historical-source differential tests explicitly skip when baseline Git objects are absent; frozen contract/state tests remain available. JS syntax, whitespace checks and Python line lengths checked. No new real-browser visual or screen-reader verification claimed.
Immediate next step: review this local commit; do not deploy/push or undertake CSS, accessibility behavior, model optimization or defect fixes in this authorized parity-only pass.
