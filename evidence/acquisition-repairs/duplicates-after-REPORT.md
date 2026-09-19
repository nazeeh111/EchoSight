# Independent recheck of exact waveform reuse fix

2026-09-19. Replayed the original adversarial development construction with fresh stores against the coordinator's fix. No main source files were changed in this pass.

| Recording entry | Before fix | After fix |
| --- | --- | --- |
| Raw SessionStore import, three equivalent container forms | 12 accepted observations, 3 surfaces | All 12 rejected with `recording_waveform_reused`; 0 surfaces, `no_result` |
| Archive export/reload and fresh processing | 12 accepted observations, 3 surfaces | All 12 rejected; 0 surfaces, `no_result` |
| Actual local HTTP upload/job/result, four container forms including native ZIP | 12 accepted observations, 3 surfaces | All 12 rejected; 0 surfaces, `no_result` |
| Twelve genuinely different synthetic recordings, development seed 1701 | Not used to derive the fix | 12 accepted, 12 waveform hashes, 6 surfaces |

Every rejected observation retains its original container hash and the full twelve-member equivalence group. Original bytes were verified against their hashes in all three stores: 12 capture references retained per store, three distinct original containers for import/replay and four for HTTP. No raw recording was deleted or rewritten by the independence check.

Positive and negative zeros produce the same waveform digest without modifying their original bit patterns; changing nominal sample rate changes the digest. No approximate-content or shifted/gain-normalized comparison was used.

## Reproduction and evidence

The fresh scripts are `probe.py`, `api_probe.py`, `verify.py` in this directory. They mirror the pre-fix scripts in the parent directory. Run from the backend root with `PYTHONPATH=.` and `.venv/bin/python`; use a fresh scratch directory for each complete reproduction because the store intentionally refuses duplicate session creation. The HTTP test uses localhost and required an approved scoped sandbox escalation. No external service, hardware or microphone was involved.

Full after outputs: `result.json`, `replay-result.json`, `http-result.json`, `unique-control-result.json`. Concise assertions and exact checked module hashes are in `verification.json`; hashes were checked unchanged before/after the final verification pass. `import-replay-log.txt`, `http-log.txt` and `verification-log.txt` preserve command evidence. Original pre-fix artifacts remain in the parent directory.

This is an independent regression reproduction of the accepted exact-copy defect. It does not establish independence of distinct recordings, robustness to near-copies, phone accuracy, or general geometry correctness. Cross-source integration is separately owned by the evaluation specialist.
