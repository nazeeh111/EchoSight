# Independent affected follow-up at 5f778a8

The two P2 cancellation findings from [the previous review](../../independent-review-f5bf0fa.md) are closed at exact commit `5f778a887817761b9db0626256698c5f678b497f`. The [follow-up report](../../independent-review-5f778a8.md) explains scope and limits. This bundle preserves the independent helper, compact per-case outputs and exact reviewed source hashes. No large raw recordings or dense epoch outputs are committed.

Reproduce in a full checkout using the existing pinned project environment:

```sh
mkdir -p work/review-5f778a8/source
git archive 5f778a887817761b9db0626256698c5f678b497f | tar -x -C work/review-5f778a8/source
.venv/bin/python evidence/completion-cancellation/independent/reproduce.py --checkout work/review-5f778a8/source --output work/review-5f778a8/reproduction
```

Use that immutable commit; the helper records its loaded source hashes for comparison with source-hashes.json. It generates the existing development moved-reflector fixture and processes four raw epochs once. It then uses exact cached epoch results to inject cancellation at controlled comparison boundaries, raises real SIGINT through CLI, and processes raw input again to exercise both mappers' terminal callbacks. It executes 12 boundary/schema cases plus independent helper copy/idempotency and both solver-finally runtime checks. It does not fit a new scientific model, tune thresholds or run a held-out benchmark. Reproduction outputs remain under work/.

The store/API/CLI runtime bytes were independently compared with the prior reviewed commit; they are unchanged. Previously passing store failure-publication, cancellation/recovery and HTTP cancellation tests were not redundantly rerun. Cancellation remains cooperative, not asynchronous preemption. This follow-up does not establish physical-device accuracy.
