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
Branch docs/readme-pipelines starts from verified origin/main b14a4cb. Only README.md and AGENTS.md may change. README diagrams labelled Inference Pipeline and Training Pipeline; Models and Evaluation is a separate section. Diagram bodies, metrics, dataset attribution, licences and limitations unchanged. README has no event, university or submission references. Shell fetch encountered DNS resolution failure, not an authentication failure; the remote base was verified independently through a read-only connector request. No connector write attempted. Immediate next step: normal local Git push of this docs branch to public main, then verify remote SHA and README headings.
