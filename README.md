# Consultoría Licitaciones — IA agéntica para contrataciones públicas en Argentina

Sistema de agentes que vigila el Boletín Oficial y los expedientes que sigue la consultora, y que
mejora de forma continua a partir del diálogo entre dos orquestadores.

## Arquitectura

```
                 ┌──────────────────────────┐        ┌──────────────────────────┐
                 │  ESPECIALISTA (Fable 5.1)│◀──────▶│    ASESOR (Fable 5.1)    │
                 │  orquestador principal   │ consejo│ contralor legal + producto│
                 └────────────┬─────────────┘        └────────────┬─────────────┘
                              │ delegar_a_analista                │
                              ▼                                   ▼
                 ┌────────────────────────────────────────────────────────────┐
                 │   ANALISTAS (Opus 5.5, esfuerzo medio) — analizan y concluyen│
                 └──────────────────────────────┬─────────────────────────────┘
                                                │ leer_url / extractos
                 ┌──────────────────────────────▼─────────────────────────────┐
                 │   LECTORES (Haiku 5.5, esfuerzo bajo) — leen el material   │
                 │   crudo (BO, COMPR.AR, CONTRAT.AR, InfoLEG, archivos) y     │
                 │   devuelven un extracto fiel con citas textuales           │
                 └────────────────────────────────────────────────────────────┘
   Monitores:  Boletín Oficial (diario)  ·  Expedientes (09:00 / 14:00 / 18:30)
   Salidas:    reports/  ·  data/registro.jsonl  ·  issues de GitHub con label "alerta"
```

- **Especialista** (Fable): decide, delega, verifica plazos y registra alertas/decisiones.
- **Asesor** (Fable): audita el criterio del Especialista y propone mejoras al sistema.
- **Analistas** (Opus 5.5, `effort: medium`): analizan extractos de normas, pliegos, actas y dictámenes;
  buscan fuentes con `web_search` y las leen con `leer_url`.
- **Lectores** (Haiku 5.5, `effort: low`): toda lectura de material crudo pasa por acá (avisos del BO, páginas
  de expedientes, URLs, archivos largos). Copian textual normas, artículos, fechas, plazos y montos, y descartan
  el ruido. El material se parte en bloques de ~80K tokens para quedar en la tarifa baja de Haiku. Textos
  cortos (< 12.000 caracteres) pasan directo, porque resumirlos no ahorra. Cada reporte incluye una tabla de
  tokens por modelo (y `data/uso_tokens.jsonl` guarda el histórico).
- Las propuestas que cambian el sistema o el criterio legal **no se auto-aplican**: quedan para aprobación humana.

## Horarios (hora Argentina, GitHub Actions)

| Tarea | Cuándo | Workflow |
|---|---|---|
| Boletín Oficial (cambios normativos) | L a V 08:20 | `boletin-oficial.yml` |
| Control de expedientes | todos los días ~09:00, ~14:00, ~18:30 | `expedientes.yml` |
| Consejo Especialista ↔ Asesor | lunes 10:40 | `consejo.yml` |

GitHub puede demorar los cron unos minutos; por eso se programan ~10 min antes. Los cron solo corren
desde la rama por defecto del repo.

## Puesta en marcha

1. Agregar el secret `ANTHROPIC_API_KEY` en *Settings → Secrets and variables → Actions*.
2. Cargar los procesos a seguir en `config/expedientes.yaml` (URL pública de la vista ciudadana).
3. Correr una vez `verificar-marco` para validar `knowledge/marco_normativo.md` contra fuentes oficiales.
4. Activar notificaciones de issues del repo (GitHub avisa por mail/app cuando hay una alerta).

## Uso local

```bash
pip install -e ".[dev]"
```

```bash
python -m licitaciones_ai boletin              # BO de hoy (o --fecha 2026-11-02)
python -m licitaciones_ai expedientes          # control de expedientes
python -m licitaciones_ai consejo --rondas 2   # diálogo Especialista ↔ Asesor
python -m licitaciones_ai verificar-marco      # verifica vigencia del marco normativo
python -m licitaciones_ai preguntar "¿Plazo para impugnar el dictamen en la LP 12/2026?"
```

```bash
pytest -q
```

## Variables de entorno

| Variable | Default |
|---|---|
| `LIC_ORQ_MODEL` / `LIC_ORQ_EFFORT` | `claude-fable-5-1` / `high` |
| `LIC_WORKER_MODEL` / `LIC_WORKER_EFFORT` | `claude-opus-5-5` / `medium` |
| `LIC_LECTOR_MODEL` / `LIC_LECTOR_EFFORT` | `claude-haiku-5-5` / `low` |
| `LIC_LECTOR_UMBRAL` / `LIC_LECTOR_CHARS` | `12000` / `280000` (umbral para resumir / tamaño de bloque) |

Las llamadas a Fable y Opus usan `fallbacks: "default"`: si el modelo rechaza una consulta, el servidor la
reintenta con un modelo alternativo. Haiku no tiene ese fallback: si rechaza un bloque, el analista recibe el
texto original recortado.

## Límites conocidos

- "Público" no es "publicado en línea": los expedientes GDE no están abiertos en internet. El monitor sigue
  lo que publican COMPR.AR / CONTRAT.AR / portales; lo demás requiere pedido de vista o de acceso a la
  información pública (Ley 27.275).
- Algunos portales (COMPR.AR) son páginas dinámicas: si una URL no se puede leer 3 veces seguidas, se
  genera una alerta para revisarla.
- El marco normativo inicial tiene ítems **[A VERIFICAR]**: no usarlo como criterio firme hasta validarlo.
