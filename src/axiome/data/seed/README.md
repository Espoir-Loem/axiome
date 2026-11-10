# Seed knowledge

- `rules.axl`: reference logic program (**axiomatic** rules).
- `facts.json`: curated facts, each attached to a source.

Contribution rules:
1. Only add **definitional or universally established** facts. Anything debatable goes through the research pipeline (M3), not the seed.
2. Every group cites its `source`. A new source requires review.
3. In M1, `is_a` deliberately conflates instance-of and subclass-of; the split is planned (RFC-0001, open questions).
4. No property inheritance with exceptions (e.g. "birds fly"): `property_inheritance` is monotonic.
5. The canonical vocabulary is English; localized labels will be added separately (M2).
