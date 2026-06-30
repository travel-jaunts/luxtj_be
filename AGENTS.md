# Agent Guidelines

- Keep all `__init__.py` files empty in all packages and sub-packages.
- Do not place imports, exports, constants, or executable code in `__init__.py` files.
- Import concrete symbols directly from their module files instead of package-level re-exports.
