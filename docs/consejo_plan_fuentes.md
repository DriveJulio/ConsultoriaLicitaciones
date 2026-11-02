# Consejo sobre el plan de fuentes

Revisión de `docs/plan_fuentes.md` por los dos orquestadores (Claude Fable), sin acceso a internet:
ninguna afirmación fue verificada contra fuentes vivas.

## Especialista

### 1. Fuentes y frecuencias

**Está bien:** N1 diario, P1/P3 3×D sobre expedientes seguidos, P5 (BO 3.ª), "datos abiertos primero", J1/J2 con BAC/PBAC.

**Sobra o bajar de ritmo** [INFERENCIA]:
- N8 Congreso: ruido puro; mensual o a demanda. Un proyecto de ley no cambia nada hasta que sale en el BO (y N1 lo atrapa).
- N4 SIGEN: los precios testigo por proceso no son públicos; mensual.
- N5 PTN: útil para fundar impugnaciones, no urgente; mensual + a demanda.
- P4 datos abiertos: la periodicidad suele ser baja [SUPUESTO]; sirve para inteligencia (precios, competidores), no para alertas.

**Falta:**
- **Ventana pre-apertura intensiva** [INFERENCIA]: en las 72 h previas a la apertura, pasar P1/P3 de 3×D a horaria. Circulares y prórrogas aparecen ahí.
- **Avisos de mantenimiento/caída de COMPR.AR y CONTRAT.AR** [INFERENCIA]: impactan en plazos (prórroga automática [A VERIFICAR]).
- **Estado del cliente para contratar** (recordatorios, no scraping): SIPRO, situación fiscal ante ARCA/AFIP, certificado del Registro Nacional de Constructores para obra pública [norma y nombre vigente A VERIFICAR]. Un cliente inhabilitado el día de apertura es la falla más cara.
- **Valor del módulo** como evento disparador (recalcular umbrales), no ítem semanal.
- **INDEC** mensual para redeterminación de precios en obra pública [INFERENCIA].
- P7: sumar UNOPS/PNUD y organismos ONU [SUPUESTO].
- P6: candidatos típicos (YPF, AySA, Trenes Argentinos, ARSAT, ENARSA, Nucleoeléctrica, universidades) [SUPUESTO; según cartera].
- BO: segunda pasada a la tarde por ediciones extraordinarias [SUPUESTO].

### 2. Etapas críticas y plazos que disparan

Todos los días/porcentajes **[A VERIFICAR]**; registrar siempre hecho disparador + tipo de día + norma.

- **Convocatoria** → antelación mínima hasta apertura y fecha límite de **consultas al pliego**.
- **Circular modificatoria** → puede correr la apertura; riesgo máximo la que sale 48 h antes.
- **Prórroga/postergación de apertura**.
- **Acta de apertura** → oferentes y precios; plazo breve para vista y observaciones → análisis comparativo.
- **Intimación a subsanar** → plazo breve; muchas veces solo en el escritorio del proveedor → avisar al cliente.
- **Dictamen de evaluación** → EL evento crítico: dispara el plazo de **impugnación** (con garantía si corresponde). Perderlo = perder el derecho.
- **Adjudicación** → recursos (Ley 19.549 / Dec. 1759/72 post Ley 27.742), garantía de cumplimiento, orden de compra.
- **Obra pública** → garantía de mantenimiento de oferta, replanteo, redeterminación.

### 3. Principios "que nada parezca raro"

Están bien. Agregaría:
- **Solo GET, nunca formularios ni login**, aunque el cliente ofrezca credenciales.
- **Paridad informativa:** el sistema no ve nada que un competidor no pueda ver.
- **Back-off:** ante 429/5xx bajar ritmo; ante bloqueo, pausar 24 h y pasar a manual.
- **IP argentina fija y declarada** en la bitácora.
- Si robots.txt prohíbe una ruta: dataset o manual, sin "evaluar".
- **Retención** de ofertas/actas de terceros con plazo fijo (Ley 25.326).
- **Nada sale al cliente sin firma humana** cuando tiene consecuencia legal.

### 4. Priorización

1. Fase 0 + **calendario de plazos de expedientes reales** cargado a mano.
2. Fase 1: N1 + P1/P3 con ventana pre-apertura + P5.
3. Fase 2: P2 + N3 (módulo, pliego único) + alertas de estado del cliente.
4. Fase 3: J1/J2 (CABA/PBA) **antes** que N2–N8.
5. Fase 4: N2, N5, N7 mensual; N4, N6, N8 a demanda; P4 para inteligencia.
6. Fase 5: P6, P7, INDEC.
