# Independent review protocol, declared before probes

Review immutable snapshot b5de1137125e098c6e546463abb18495585fdbcc48b2c3ed5b7fe3b2c896e417. No old evaluation fitting, no source-model threshold changes, no prototype edits. Verify every manifest file.

The processing convention is R(k)=median_j corr[y(alpha*(t_j+u)+b),p](k)/||p||²; d is the interpolated maximum of |R| near the reacquired direct window. Stored times are tau_k=(k-d)/fs. The prototype forms z(t)=R(d+fs*t)/R(d). A pure raw recording translation changes b, while d and z remain nearly invariant. A declared clock-parameter perturbation must change the resampled segments, recorrelation, median, d and normalization together. A direct-origin uncertainty is not an independent Gaussian displacement of a waveform already defined to have its measured peak at zero.

Independent tests: render one fresh analytic direct-plus-echo recording with a known affine clock and no room labels. Translate raw bytes by3samples and run the immutable process_recording again; compare normalized responses and clock intercept. Compare with a3sample axis-only shift of the original response. Repeat the physical clock at+600ppm rather than+200ppm with the same source signal. This verifies representation, not detection accuracy or hardware nuisance distribution.

Independently test the two-component amplitude profiler on a normalized synthetic response with correlated basis columns. Compare clipped unconstrained coefficients with scipy's box-constrained least squares at each exact same permitted alignment. This assesses objective correctness, not a new scene/source discrimination benchmark.

No full classifier searches or heldout scene generation. Record all failures and numerical tolerances. Any follow-up raw uncertainty study requires a new specification that preserves correlation of affine slope/intercept and recomputes direct anchor/kernel, or treats direct bias as a shared forward-model nuisance against unchanged data.
