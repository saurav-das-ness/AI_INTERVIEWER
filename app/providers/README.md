# Providers Layer

This folder is reserved for external runtime adapters.

- `bedrock/` should contain model-provider adapters.
- `vector/` should contain ChromaDB or retrieval-specific adapters.

Provider-specific code should stay isolated here so services depend on abstractions, not vendor details.
