# app/adapters/__init__.py

"""
This is the package initializer for the `app.adapters` module.

The `adapters` package contains all provider-specific implementations of
the LLM adapter interface (`BaseAdapter`). Each adapter implements the
required methods: `chat`, `chat_stream`, and `embed`.

Examples:
- `openai_adapter.py`
- `ollama_adapter.py`
- `deepseek_adapter.py`

This `__init__.py` is intentionally left empty but:
- Marks this folder as an importable Python package
- Enables dynamic imports (e.g., via `importlib.import_module`)
- Helps documentation tools and RAG systems index the adapter architecture

🧠 See also: `adapter.py`, which acts as the adapter entry point and wrapper.
"""
