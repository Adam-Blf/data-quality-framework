# Changelog

## 0.1.0 - 2026-07-28

- Initial release: Great Expectations suite on the official French postal
  code dataset (data.gouv.fr / La Poste, Licence Ouverte v2.0).
- Checks: completeness, full-row uniqueness, value ranges, schema drift,
  referential consistency (postal code / department prefix), freshness.
- HTML Data Docs generation and CI artifact publishing.
- Corruption injection demo proving the quality gate fails on bad data.
- Unit tests for the custom Python checks (no network dependency).
