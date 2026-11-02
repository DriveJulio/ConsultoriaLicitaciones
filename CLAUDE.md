# CLAUDE.md

Sistema agéntico de licitaciones (Argentina). Ver README.md para arquitectura.

- Orquestadores: `claude-fable-5-1` (Especialista y Asesor). Analistas: `claude-opus-5-5` con `effort: medium`.
- Historial de los orquestadores es append-only (preserved thinking): no editar mensajes previos.
- Fable 5.1 / Opus 5.5: no usar `tool_choice` any/tool, ni `thinking` disabled/budget_tokens.
- Nunca inventar normas, artículos ni plazos: marcar [A VERIFICAR].
- Tests offline: `pytest -q` (sin API key; el LLM se mockea).
