# Independent affected follow-up: cancellation repairs

**Both P2 findings from the f5bf0fa assembled review are closed at exact commit `5f778a887817761b9db0626256698c5f678b497f`. No new P1/P2 finding was reproduced in this affected review.** This conclusion covers the two cancellation boundaries and the shared helper refactor. It does not declare the scientific backend objective complete.

The reviewed runtime was extracted with `git archive` into `work/review-5f778a8/source`. Relevant code and schema bytes were independently matched against Git objects. No runtime edits were made. The earlier failure artifacts remain unchanged in [the prior bundle](assembled-repairs/independent-f5bf0fa/).

## Reproductions and disposition

1. **Controlled cancelled claims: closed.** Four existing development moved-reflector epochs were processed from 48 actual WAVs, each returning one inferred plane. Exact cached epoch outputs were then used for deterministic comparison-boundary injections. Cancellation after spatial comparison, after the first receiver, and after the last receiver under a no-change timing budget now clears both `conditional_spatial_changes` and `receiver_evidence`. All three boundaries were exercised through direct core calls and real CLI SIGINT. The CLI returns130 and saves the sanitized result. Completed epoch objects agree with the original compacted records, including their geometry and every recording hash. Input objects remain unchanged.
2. **Outer pipeline terminal callback: closed.** Both mapper and baseline now check cancellation after the public final progress callback. Direct calls and CLI SIGINT return `cancelled`, with empty surfaces, hypotheses, dimensions and guidance while preserving twelve observations, twelve recording fingerprints and the result identity. The exact same boundary previously returned successful geometry.
3. **Schema enforcement: verified.** Normal completed scene/comparison outputs validate. Relabeling those claim-bearing outputs `cancelled` is now rejected by both public schemas. Actual sanitized cancellation outputs validate. These checks use the real generated output objects, not hand-written successful geometry.
4. **Shared finalizer: verified.** `_cancelled_result` copies the result envelope, diagnostics list and search object before changes; it removes the union of single-source and multi-source derived claims and preserves observation/processed-session input evidence. An independent copy/idempotency check passes. Both solver exception handlers rebind their local `out` to the sanitized copy before return, so their `finally` runtime update reaches the returned object. Controlled clock probes verified returned runtime3s and5s for the single/multi-source branches, respectively. Those synthetic clock values verify control flow, not measured performance.

Twelve independent boundary/schema cases passed, plus the helper checks above. The unchanged successful moved-reflector comparison remains available when not cancelled. No full test suite or new held-out evaluation was run; the coordinator's201-test result is separate background evidence.

## Publication and recovery scope

`echosight/storage.py`, `api.py` and `cli.py` are byte-identical to the independently reviewed f5bf0fa versions. The prior controlled store cancellation/failed-publication, store recovery and actual loopback HTTP cancellation checks all passed. Their logs remain in the previous bundle. Since no publication logic changed, those checks were not rerun as a ritual. The now-sanitized direct outputs align the reusable core and CLI with that already verified store boundary.

The controlled finalizer is applied to all return paths in the function, including early no-change, failed-repeat and input-diagnostic exits. The independent executable cases specifically cover spatial completion, first receiver and final no-change receiver; other return paths were inspected and are covered by the implementer's separate targeted checks. Cooperative cancellation is observed at these explicit boundaries; arbitrary asynchronous arrival after the last check cannot be universally prevented by a synchronous core API. Store publication remains separately guarded.

## Evidence and reproduction

- [Independent helper](completion-cancellation/independent/reproduce.py)
- [Compact results, including source hashes and recording fingerprints](completion-cancellation/independent/results.json)
- [Reviewed source hashes and unchanged publication files](completion-cancellation/independent/source-hashes.json)
- [Reproduction instructions](completion-cancellation/independent/README.md)

Local full outputs and recording fixtures remain in `work/review-5f778a8/run`; raw audio is excluded from this evidence bundle. All classifications remain simulated development evidence, not measured room accuracy or device validation. Source/clock/model limitations recorded in the parent review remain unchanged.
