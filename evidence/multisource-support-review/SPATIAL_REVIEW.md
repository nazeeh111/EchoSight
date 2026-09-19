# Independent bounded evaluation of support-pruning experiment

Frozen candidate module SHA256: b1ac9e0e34f542d8f890797fd109db29ea4c3dbca7698bf30edb6abef28754ce. Original module SHA256: 55e060183836b11b9976fe0f2187c3b97101687ff34d35d65c6319489e66f6aa. Frozen acceptance SHA256: 626166532905ca48a53639f6521df93aecc6f2bcf8dd77618bd20b8272fd35f7.

The isolated change removes candidates that lose the existing support requirement after exclusive assignment/refit, then repeats refit and assignment on surviving candidates. No candidate is added and the plane count decreases each unsuccessful pass, so the loop is bounded by the original maximum ten planes. The successful final links feed the unchanged covariance, source-diversity, parent-path and compact/hidden-parent interpretation checks. This changes selection behavior and can expose previously withheld geometry; therefore more recovered planes alone would not justify promotion.

Independent `check_spatial.py` execution completed successfully and produced `spatial-check.json`. It verifies the frozen module/acceptance hashes, input-file identities and complete 12-case membership; independently recomputes maximum-cardinality one-to-one matches under the unchanged 5-degree/0.15-m criteria; and confirms candidate exclusivity plus every definitive surface's four-or-more captures at every source, eight-or-more total supports and rank-three receiver positions.

All independently recomputed counts agree with the builder's saved results. Higher-order 1129 improves from zero to six matched planes, zero false surfaces and two horizontal planes. The other eleven cases retain their counts. Across the complete frozen denominator, matched planes increase from 34 to 40 with zero false surfaces in either method. This is a regression on exposed retained observations, not a new blind or measured result.

Limits and promotion checks:

* Two-source 1103 remains ambiguous with no definitive surfaces and fails its minimum recovery requirement. The full frozen scientific requirement is still unmet.
* Coordinate-frame mismatch 1193 has `calibration_needed` in both inference-only replays, outside the frozen allowed status list. The raw entrypoint performs earlier validation and must be checked separately; this saved-input route cannot certify that acceptance gate. This is not attributed to the candidate because the original replay behaves identically.
* Inference-only runtimes do not certify the complete 60-second raw-input gate. Retained raw 1129 should verify actual extraction-to-output after integration.
* The newly repeated refit loop has no internal cancellation checks. Check cancellation at least per pruning pass and before each nonlinear fit before production promotion. The existing downstream cancellation check prevents final published geometry, but does not bound responsiveness inside the enlarged work segment.
* Preserve other frozen mismatch controls in an affected regression, particularly distributed-source cases: retaining survivors can uncover coherent false planes that the previous all-or-nothing return withheld. No blanket scientific success follows from this 12-case suite.

No production edits, raw generation, full-suite repetition or inference rerun occurred in this evaluation lane. The builder's execution and this independent saved-output audit are distinct evidence classes.

## Bounded follow-up

Inspected v2 candidate SHA256 b61f4742927c8270a5133526bddbff5080b806242f6ff2e08310bc9499622085 against v1. Its only executable changes are cancellation checks at each pruning pass and each fit; numerical logic is identical. Builder's saved v1 raw-check-results.json records 1129 returning six matched planes, zero false, in 5.25 seconds versus original zero planes in 3.90 seconds, and 1193 returning allowed `no_result` through the raw entrypoint in both versions. Input hashes remain unchanged according to that runner. These close the identified v1 raw-route ambiguity and runtime observation, as source-reported checks, not independent raw replication. V2 targeted raw/cancellation checks remain owned by builder/coordinator. The broader mismatch regression remains warranted before integration.
