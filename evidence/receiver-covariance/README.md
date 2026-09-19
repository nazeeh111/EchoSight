# Correlated receiver-array propagation checkpoint

The optional declared full covariance replaces scalar receiver uncertainty and retains shared errors across distinct capsules and repeated source sessions. [Contract](../../docs/RECEIVER_COVARIANCE.md). It does not repair biased poses or establish physical confidence calibration. Source/receiver cross terms remain unsupported and must be declared absent for this contract.

The implementation passes36focused checks and the integrated177test suite (57.297seconds). [Builder source hashes](verification.json), [focused execution](focused-tests.txt), [integrated execution](integrated-tests.txt). Source hashes are relative to the repository root; the separately archived candidate design is design-only and has not changed detection/scoring. Independent immutable review is the next gate.
