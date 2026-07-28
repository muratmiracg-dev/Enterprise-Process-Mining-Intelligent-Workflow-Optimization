# Contributing

## Development

1. Create a branch from `main`.
2. Install `python -m pip install -e ".[dev]"`.
3. Keep business assumptions explicit and avoid real company or personal data.
4. Run `make quality test verify`.
5. Open a pull request using the template.

## Change discipline

- Changes to the ideal process require synchronized BPMN, configuration,
  conformance tests, and documentation updates.
- Data-generation changes must preserve deterministic gzip output or explicitly
  document a benchmark version change.
- KPI definition changes require a versioned migration note.
- Model changes require temporal validation, explainability, and a model-card
  update.
- Simulation assumptions must never be presented as guaranteed financial return.

Commit messages should be imperative and scoped, for example:
`feat(simulation): add supplier lead-time scenario`.
