# Postfreeze evaluation-oracle clock diagnosis

This addendum follows the immutable completed v4 snapshot `587df54570155117f92df5a970e47e335a371ecaef31cc16d38f2e6a95108187`. It changes no results, classifier, threshold or source model. Three already exposed development recordings, seed2459/source2/receiver1 in direct-null, single-room and near-reflector families, were re-extracted for diagnosis only. No mapping was rerun.

The renderer samples `y(t_receiver)=x((t_receiver-offset)/alpha)`. Its alpha is therefore exactly the receiver-time versus source-buffer-time slope targeted by the pilot regression; the physical speed/source-clock conversion was already incorporated into path delay and is not another factor to apply to alpha. On the null recording actual alpha1.0014913832594845 becomes estimated1.0013484353454214:−142.9479ppm. Reported alpha SD30.8379ppm gives−4.6355standardized units. This is a conditional standard-error discrepancy on one exposed case, not a calibrated tail probability.

Raw re-extraction with the immutable original code exactly reproduced saved clock and candidate outputs. The original chosen pilot lags relative to physical starts are approximately+38.4µs for the first four repeats and−194µs for the last three. The fitted residual maximum99.65µs is just below the100µs rejection/retry condition. This leaves the nominal-rate acquisition template in use. The evidence supports a selected correlation-lobe change, not a wrong alpha convention or actual non-affine recording clock.

`oracle_clock_v4.py` creates an isolated in-memory copy of immutable signals code. It forces the already existing bounded retry and uses generating alpha ONLY to build that retry's stretched pulse template. Existing nearest-peak selection, accepting only a smaller affine residual, least-squares pilot refit, rejection behavior, waveform resampling, direct anchoring and candidate extraction remain unchanged. Generating alpha is not supplied as the fitted slope. This is an evaluation oracle unavailable to a real receiver, not a proposed algorithm or fitting input to any benchmark.

| Measure, direct-null recording | Original | Evaluation-oracle retry |
|---|---:|---:|
| Clock-rate error |−142.95ppm|−0.275ppm|
| Maximum pilot fit residual |99.65µs|0.070µs|
| Direct response amplitude |0.02850|0.17289|
| Direct timing SD |107.96µs|41.67µs|
| Resolved echo candidates |1|0|

The original null candidate has delay539.86µs, amplitude0.088relative to direct, and6/7repeat support, despite no physical reflector in the renderer. It vanishes with the oracle retry. There was no false mapped surface for this scene in the original evaluation; this is a false candidate and distorted response, not proof of false geometry.

Single-room and near-reflector matched controls show the same clock result. Geometric excess-delay comparisons are evaluation-only nearest-candidate compatibility, not labeled inference. Original wall timing errors reach28.6mm in path length; most become less than0.2mm with the oracle template. The improvement is not universal: floor/ceiling paths are physically only100.18µs apart, below the extractor's350µs separation guard. The corrected response produces one fewer candidate; nearest compatibility for ceiling worsens from5.8mm to34.4mm while floor becomes accurate. The original extra peak must not be counted as proof of reliable overlap resolution. All reported nearest timing residuals, including this miss, remain below1.71of the combined local direct/candidate/rate standard deviations; the shared input uncertainty is not being silently discarded to manufacture a stronger claim.

Thus the conditional acquisition retry can miss a material rate-lobe bias when an erroneous train happens to pass its residual check. A non-oracle, independently frozen experiment would be needed to determine whether using an estimated-rate matched template more broadly improves accepted clock error/false candidates without introducing wrong-lobe or multipath associations. Another unresolved issue is resolving overlapping paths without fabricated echoes. No threshold adjustment, loop over this exposed answer, classifier retest or production promotion is warranted by this oracle alone.

Executed evidence: `oracle_clock_v4.py`, `v4-oracle-clock-results.json` (includes immutable and oracle code hashes, raw hashes, full pilot diagnostics and all per-path timing comparisons). Original v4 source-warning results and frozen failures remain unchanged.
