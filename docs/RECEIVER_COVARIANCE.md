# Experimental multi-source receiver survey covariance

Multi-source inference can now represent a surveyed array whose different capsules share translation and rotation uncertainty. This changes uncertainty propagation and, when relevant, competing-path compatibility. It does not change candidate extraction, association, plane fitting, or measured survey means. This is a supplied uncertainty model, not empirical confidence calibration.

The optional declaration lives inside a source bundle's `shared_calibration`:

```json
{
  "receiver_pose_covariance": {
    "group_ids": ["array1-left", "array1-right"],
    "covariance_m2": [
      [0.0004,0,0,0.0003,0,0],
      [0,0.0004,0,0,0.0003,0],
      [0,0,0.0004,0,0,0.0003],
      [0.0003,0,0,0.0004,0,0],
      [0,0.0003,0,0,0.0004,0],
      [0,0,0.0003,0,0,0.0004]
    ],
    "assumption": "independent_of_source_and_effective_speed",
    "scalar_policy": "replace"
  }
}
```

Coordinates are metres in the bundle's common surveyed frame; each ordered block is `(x,y,z)`. This two-group example illustrates the matrix shape, not a sufficient acquisition arrangement. For `G` groups the matrix is `3G × 3G`, finite, symmetric (relative tolerance `1e-8`, absolute `1e-12`), and positive semidefinite after symmetrization (minimum eigenvalue at least `-1e-12 m²`). Entries must be JSON numbers, not strings or booleans. Symmetrization within that tolerance is recorded in output.

The declaration requires all four keys exactly. IDs are unique strings of 1–160 characters; at most 64 groups. They must cover exactly the unique `receiver_pose_group_id` values of all supplied captures/observations, including recordings rejected for quality. A reused group must have the same nominal position within `1e-8 m`; observation and capture group IDs must agree. Repeated source sessions use the same group block, not independent copies. Entries not used by accepted evidence remain in the declaration; no data-dependent change of survey meaning occurs. Raw processing validates the declaration before reading recording files; prepared processing validates it before proposals. Malformed declarations return explicit failure diagnostics, not a scalar fallback. Cancellation remains supported.

`scalar_policy: "replace"` is mandatory. Existing valid `receiver_position_std_m` metadata remains stored, but contributes **zero additional receiver covariance** when this matrix is supplied. Differing scalar values across reused captures are therefore not competing active calibrations: the explicitly selected full matrix governs propagation. Nominal reused positions must still agree. Without this declaration, legacy scalar behavior is retained: each distinct receiver group is independent and isotropic; reuse of a group shares its survey error across sources.

The result's `receiver_pose_uncertainty` describes the active mode, group order, symmetrized full matrix, replacement policy and independence assumption. Raw result identity includes the supplied bundle, so differing covariance declarations change its identifier. Original raw WAV/native packages and prepared observation metadata are not rewritten.

## Physical meaning and propagation

For a capsule at `r_i` on an array with surveyed origin `o`, a small rigid displacement is

`delta r_i = delta t + delta omega × (r_i-o) + epsilon_i = B_i eta + epsilon_i`,

where `B_i = [I, -skew(r_i-o)]`. Thus an array translation/rotation covariance `Sigma` and independent local capsule uncertainty `D_i` produce block covariance

`C_R[i,j] = B_i Sigma B_j.T + (i == j) D_i`.

These six rigid parameters are a way to construct the supplied matrix; the backend does not assume every receiver belongs to one rigid array. Independent arrays can use separate block groups and independent terms. Units in a rotation/translation construction must be radians and metres before producing the final metre-squared matrix.

For first-order plane images `q`, direct source `s`, receiver `r`, and effective propagation speed `v` in metres per source-buffer second, the excess delay is `mu=(|q-r|-|s-r|)/v`. Its receiver gradient is `g_r=((s-r)/|s-r| - (q-r)/|q-r|)/v`. Stacking that gradient into the appropriate group blocks gives `J_R`. The receiver contribution is `J_R C_R J_R.T`; it is added once to the existing source/speed and timing contributions.

Plane uncertainty uses the sandwich covariance of the executed ordinary least-squares estimator, `L C L.T`, with `L=pinv(J_plane)`, retaining existing residual inflation. Parent-path gates use the corresponding receiver marginal variance and the already propagated full parent-plane uncertainty. They remain the existing conservative marginal compatibility rule, not a joint posterior over reflection orders. Fixed plane-versus-point/parent comparisons receive the full covariance. Compact-path location covariance uses its own physical receiver derivative `(unit(r-p)+unit(s-r))/v` and the full matrix, propagated through the executed fixed-weight estimator. Source/source and source/speed cross terms are unchanged.

A common 20 mm translation projected identically onto five capsules leaves 20 mm uncertainty in their average. Independent scalar marginals would report `20/sqrt(5)=8.94 mm`. Some contrasts instead cancel common translation, so correlation is not merely an inflation multiplier. These relationships hold locally, conditional on declared covariance and selected acoustic paths.

## Limits and verification

The declaration explicitly assumes receiver survey errors are independent of source position and effective speed. It cannot encode shared source/receiver coordinate-frame error or survey cross terms. If those terms are material, this contract is insufficient; do not silently treat them as zero by claiming this declaration fits that acquisition. A future complete joint source/receiver/speed matrix would be needed. Gaussian covariance also cannot repair systematic source-position bias, an incorrect propagation model, occlusion, wrong candidate assignments, or source directivity. No priors were widened using measured target surfaces.

Run:

```sh
.venv/bin/python -m unittest tests.test_receiver_covariance tests.test_multisource tests.test_path_alternatives -q
```

The focused tests check an independently differentiated rigid-array model and 40,000 nonlinear Monte Carlo draws plus 600 actual nonlinear plane refits under shared rigid-array error; an independently assembled plane nuisance covariance; full versus diagonal projection; source terms unchanged; reuse without duplicate receiver blocks; fixed comparison and actual point sandwich propagation; parent marginal projection; identical legacy/full-diagonal results; explicit scalar replacement; malformed/oversized/non-PSD input; raw WAV admission and prepared replay transport; unchanged original bytes; cancellation; and inconsistent rejected-capture poses. The raw transport test stubs candidate extraction to isolate this contract, while the existing acquisition tests exercise actual waveform extraction. No phone hardware measurement or calibrated physical confidence coverage is claimed.
