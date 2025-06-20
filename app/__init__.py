# app/__init__.py

"""
This is the root package initializer for the `app` module.

Although currently empty, its presence signifies that this folder is a Python package.
This file can be used to define package-level variables, set up logging,
or configure imports when `app` is imported as a module.

In the context of the LLM Router system, this file is intentionally left blank.

💡 You typically create an `__init__.py` file to:
- Mark a directory as a Python package.
- Perform one-time initialization logic if needed.
- Expose high-level APIs (e.g., `from app import settings`).
- Control package imports via `__all__`.

Since all submodules and configuration are explicitly imported elsewhere in this system
and this package is structured as a FastAPI application, no logic is required here.
"""
