# Engineering Data and Model Governance

**Status:** Initial software contract implemented; scientific model validation not established.

## Numerical value contract

Every engineering numerical value is represented with:
- stable value ID and human-readable name;
- numerical value and explicit unit;
- provenance class;
- intended use;
- model/source metadata appropriate to its provenance;
- credibility status and applicability limitations.

## Provenance classes

| Class | Required metadata | Meaning |
|---|---|---|
| `sourced` | Source identifier, title and release/version | Transcribed or derived from a cited external source. Source citation alone does not prove applicability. |
| `calculated` | Equation identifier and model version | Computed by an identified equation/model. Equation implementation and inputs require separate verification. |
| `illustrative` | Explicit assumption note | Synthetic or placeholder value used for demonstration, software tests or scenario exploration. Never a real hardware specification by implication. |

## Credibility states

- `unassessed`: no documented verification/validation assessment is attached.
- `verified`: implementation verification evidence exists for the stated requirements.
- `validated`: evidence supports the model for a stated intended use and domain; applicability limitations must be recorded.
- `unvalidated`: the model/value is explicitly not validated for the intended engineering use.

The API currently validates metadata completeness only. It does not independently confirm source authenticity, numerical correctness, dimensional consistency, model verification, model validation, uncertainty bounds, or flight suitability.

## Release gate

A physical model must not be described as engineering-grade for a stated use until its requirements, governing equations, input data, verification cases, independent validation evidence, uncertainty treatment, and applicability limits have been reviewed and approved.
