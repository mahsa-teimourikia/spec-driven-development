# Trusted harness boundary

This directory supplies deterministic keys to the offline teaching harness. The
candidate source and packaged application receive neither this path nor the
keyring. The keys are public repository fixtures, so they demonstrate signature
verification mechanics—not production secrecy or independent identity.

Production should replace this fixture with workload identity, isolated secret
management, rotation, revocation, and externally verified attestations.
