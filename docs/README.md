# EchoSight documentation

Start with the [repository README](../README.md) for the simulated room demo, optional local Echo Bot and backend setup. The demo is a presentation of the concept; these backend guides describe processing actual recording inputs.

| Task | Guide |
| --- | --- |
| Install, process recordings and replay results | [Usage](USAGE.md) |
| Call the local recording API | [API routes and errors](API.md) |
| Build a frontend for backend results | [Frontend handoff](FRONTEND_HANDOFF.md), [JSON schemas](../schemas/) and [result examples](../examples/frontend/) |
| Interpret material and color outputs | [Materials and appearance](MATERIALS_APPEARANCE.md) |
| Understand session inputs and calibration | [Data contract](CONTRACT.md), [calibration](CALIBRATION.md) and [acquisition](ACQUISITION.md) |
| Examine the physical model | [Signal model](SIGNAL_MODEL.md) and [inference](INFERENCE.md) |
| Assess scientific progress and limitations | [Current state](../STATE.md), [evaluation](EVALUATION.md) and [requirement coverage](audit/COVERAGE.md) |
| Prepare physical device validation | [Hardware acceptance](HARDWARE_ACCEPTANCE.md) and [iOS recorder](../acquisition/ios/README.md) |
| Check scope and provenance | [Charter](CHARTER.md), [scope addendum](CHARTER_ADDENDUM.md), [sources/licenses](SOURCES.md) and [demo model](../demo/MODEL.md) |

Physical validation with our devices remains pending. Software tests, simulated UI confidence labels and successful synthetic examples do not establish measured room accuracy. Historical reviews and frozen failures are retained in [evidence](../evidence/).
