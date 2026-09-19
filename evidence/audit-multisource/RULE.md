# Frozen development comparison rule

Before rerunning source-relocation development (2026-09-19):

1. Keep the complete jointly fitted first-order candidate model and its exclusive candidate evidence. No truth labels, extra peaks, or geometry bounds enter comparison.
2. Enumerate all nonempty subsets of at most10 proposed parent planes (maximum1023). A subset offers its first-order paths and all physically validated ordered two-bounce paths. Unknown finite extent, scattering strength and occlusion remain unknown.
3. Every originally selected candidate must have at least one path compatible within3 marginal standard deviations. Marginal tolerance includes detector, shared direct timing/clock, surveyed receiver/source and effective speed; local fitted parent covariance may widen it. This engineering compatibility gate is not a calibrated hypothesis test after candidate selection.
4. For each candidate, choose its best compatible path by absolute delay residual. Compare the total squared residual normalized by fixed detector+direct timing scales with the original first-order model on exactly the same evidence. An alternative is sufficient only if its score is no worse. This descriptive score is not a likelihood or posterior; off-diagonal correlations are not used to produce a significance claim.
5. Preserve all sufficient subsets as indices (bounded1023), render the smallest sufficient parent model plus the original model as explicit competing hypotheses, and expose only the parent intersection across all sufficient models as invariant across these tested explanations. Never assert removed reflectors are absent. If none are sufficient, preserve original conditional result. Existing source/mirror ambiguity must remain.
6. Test equal inputs, hidden parent echoes absent, and a genuine extra finite reflector. Do not change held-out criteria; report residual failures.
