# Label-free clock refinement: bounded development and affected-behavior results

The additional observed-rate trigger removes the three exposed≈143ppm accepted clock errors and the direct-only null's false echo candidate. Across1248paired recordings, accepted/rejected counts remain1180/68. Candidate-level false matches decrease813→799 and missed paths2989→2985 under the frozen75µs one-to-one matching rule. All24existing scene mappings retain their per-case true/false/missed-plane counts. **This is a narrow acquisition improvement; it does not improve the reported scene reconstruction counts, solve source ambiguity or qualify physical-device accuracy.** No main code has changed.

## What was compared

`run-v1/freeze.json` SHA-256 `5e8dbca0bfca5d5767b8c2023e11c44b95e33bc20253df71652185e0d645ce79` pins the protocol, renderer, runner, immutable de8442b signals/storage and exact candidate code before new generation. The candidate adds a single trigger to the existing rate-matched-template retry: observed within-pulse displacement `abs(alpha_est−1)*duration` exceeds `0.5/bandwidth`. For40ms/12kHz this is≈1042ppm. It uses the observed coarse alpha, never generating truth. Existing one-retry limit,±1ms pilot search, smaller-maximum-residual winner rule,100µs/5000ppm rejection, weak-direct detection, response resampling and candidate extraction remain unchanged.

Both algorithms processed the same1152previous v3/v4 raw recordings and96new controls at seeds2701/2713. Every saved original clock/candidate/status was exactly reproduced before comparison. The96controls cover8clock rates from−4500to+4500ppm and direct-null, overlapping multipath, weak direct, nonlinear waveform, smooth clock warp and clock step families. Their truth is loaded only after both processing calls. No source classification was run or changed. No reserved seed2609/2621 was generated.

The baseline clock errors over50ppm fall3→0. The worst accepted affine error falls142.96→39.27ppm; median absolute error0.175→0.159ppm. The fraction exceeding1.96times reported alpha SD falls2.29%→0.68%; this is a conditional residual statistic on these simulations, not calibrated coverage. All118changed clock outputs and unchanged failures remain in full results. No common-accepted record's absolute clock error worsens by more than1ppm; every changed accepted estimate has absolute error/SD below0.89. An unchanged case still has4.43standardized units of error. A smaller pilot residual is not, by itself, evidence of a correct physical rate.

All frozen development gates pass: fewer large accepted affine errors and null false candidates, no newly accepted weak/warped controls, no valid admission loss, no aggregate false/miss increase on common-accepted valid inputs, and candidate maximum runtime0.038s below the2s limit. This pass is not automatic production approval. The independent pre-results concern about affine wrong-lobe bias remains mathematically valid and is addressed by exposing every per-record change rather than substituting aggregate counts for evidence.

## Losses and ambiguity are preserved

Eleven recordings have an increased false-candidate count or increased missed-path count; seven have a net additional missed path. Five recording/path instances with separated weak true echoes now fall below the unchanged7%relative-amplitude threshold, at≈6.5–6.8%. Others involve selection between overlapping paths3.5–312µs apart, within the extractor's350µs minimum peak spacing. These include qualified single-room and near-reflector recordings, not only difficult dual-source controls. Local raw maxima, thresholds, repeat support, selected candidates and evaluation assignments are preserved in `postfreeze-peak-diagnosis.json`.

Five recordings have increased false-candidate counts, all in dual-source cases. Two still use a reference≈0.4–0.52ms later than the earliest physical arrival; correcting clock rate does not identify which emitter defines the direct path. Other extra candidates are associated with overlapping/dispersive waveform peaks111–363µs from generating geometric delays. One-to-one assignment changes also affect which of nearly coincident paths is counted. `postfreeze-false-candidate-diagnosis.json` records every unmatched delay and physical-reference error. These counts are candidate-level compatibility failures against synthetic paths, not additional false mapped planes or measured echo labels.

All16nonlinear-waveform controls are rejected by both routes as direct-reference ambiguous. This preserves conservative behavior but also shows incomplete support for distorted recordings; it is not a successful reconstruction test. All16weak-direct and32smooth/step-warp controls remain rejected. Sixteen direct-null and16multipath targeted controls remain accepted; the100µs overlapping truth contributes16misses in both arms. No negative-control acceptance was converted into a claimed success.

## Authorized postfreeze scene and historical regressions

Both observation sets were run through the same immutable de8442b mapper for all24existing scenes. The original saved mapper counts were reproduced; every individual case retains the same matched/false/missed counts:

| Previously exposed cohort | Original | Candidate |
|---|---:|---:|
|12v3 scenes|62matched,13false,0missed|62matched,13false,0missed|
|12v4 scenes|62matched,12false,0missed|62matched,12false,0missed|

No warning classifier clears geometry in this comparison. Supplied scene truth is read only after both fits; frozen matching gates remain unchanged. All13/12false planes remain failures. These regression scenes do not validate arbitrary source arrangements or improve the original frozen held-out targets. Evidence is `postfreeze-scenes/report.json` and paired full outputs with raw/baseline hashes.

The historical27affine-clock cases remain27/27accepted;30warp/missing/noise controls remain0/30accepted. Maximum accepted geometric delay error improves1.548→1.379µs. The existing25measured-RIR hybrid recordings retain21accepted/4rejected; every recorded clock/candidate/diagnostic/direct-arrival output is identical between routes. They do not exercise independent measured device clocks and do not validate the problematic measured direct-path assumption. No new downloads or hardware were used. Evidence: `postfreeze-historical.json`.

A reviewer helper initially failed to import the separate evaluation package; the error was preserved in `scenes-first-import-error.log`, the helper import path corrected, then all48scene fits completed. This was an operational reviewer-script import issue, not a numerical result or changed algorithm.

## Mathematical and integration limits

The selected pilot residual can conceal a coherent affine lobe bias. The independent arrival-level example in `work/clock-refinement-independent-design.md` demonstrates that smaller residual and alpha SD can accompany a worse rate, without claiming raw realization. The current test found no consequential new rate/uncertainty regression, but cannot prove that failure impossible. Pilot selection, reuse of the same data for the fitted template and residual-based winner selection remain conditional assumptions. Existing alpha SD also uses RMS residuals rather than a full selection-aware model; no uncertainty-calibration claim is made.

The additional trigger leaves low estimated rates untouched. Thus some accepted tens-of-ppm multipath/source biases persist, as does wrong-direct selection. It does not estimate non-affine warp, resolve overlapping echoes, restore clipped/distorted waveform validity or determine absolute source-clock scale. The trigger is an engineering use of nominal bandwidth resolution, not a universal identifiability condition. Source/receiver pose uncertainties and geometry semantics are unchanged.

The evidence supports considering this small trigger change as a bounded acquisition fix after independent review of the per-record regressions and shared-code integration tests. It does not justify a broader clock-calibration or spatial-performance claim. A received-repetition cross-correlation clock estimator remains a serious independent design alternative if these unresolved assumptions become limiting; it has not been implemented or tested in this branch, and there is no need to launch a search over variants merely because this bounded comparison passed.

## Reproduction and artifact boundaries

All source and output files are owned under `work/clock-refinement/`. Existing outputs intentionally reject overwrite. In a fresh output copy, run `runner.py freeze`, then `runner.py run`, followed by `summarize.py`; the local immutable de8442b checkout and preserved v3/v4 raw inputs are required. `scenes.py`, `historical_controls.py` and `regression_diagnosis.py` are explicitly postfreeze affected-behavior checks. Root-level NumPy/SciPy dependencies suffice; no added packages. Full paired results contain raw hashes and conditional diagnostics. The separately archived evaluation-oracle experiment is `oracle-archive-5347fc5f87c4/`; it was never loaded by candidate fitting.
