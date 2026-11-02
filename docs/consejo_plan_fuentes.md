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

## Asesor — respuesta al Especialista

### 1. Acuerdos, desacuerdos y lo que no se vio

**Acuerdo pleno:** ventana pre-apertura horaria; dictamen de evaluación como evento crítico; nada sale al cliente sin firma humana; J1/J2 antes que N2–N8; P4 como inteligencia, no alerta.

**Desacuerdos / exageraciones:**
- **"Solo GET, nunca formularios"** [INFERENCIA]: exagera. Las búsquedas públicas de COMPR.AR/BAC son formularios sin login; prohibirlos mata P2. La línea correcta es *sin credenciales ni evasión*, no *sin POST*.
- **"Paridad informativa"**: bien como principio, mal como control: el riesgo real es **correlacionar de más** (datos de terceros).
- **"Pausar 24 h ante bloqueo"**: arbitrario. Mejor: pausar + abrir issue + decisión humana.
- **N8 Congreso "ruido puro"**: medio punto. Un proyecto de reforma es señal comercial para la consultora. Mensual.
- **"IP argentina fija y declarada"**: correcto, pero es una decisión del dueño (asume por escrito que el sistema accede desde su infraestructura).

**Lo que no se vio:**
- **Responsabilidad profesional** [INFERENCIA]: si la IA calcula mal un plazo y el cliente lo pierde, responde la consultora. Falta: cláusula contractual sobre el alcance de la herramienta, doble cómputo (IA + humano) de plazos con consecuencia jurídica, seguro de RC profesional [A VERIFICAR cobertura local]. Es el riesgo n.º 1 del negocio.
- **Huella del User-Agent** [INFERENCIA]: quien lea logs puede inferir qué sigue la consultora. El motivo va solo en la bitácora interna; el UA, sin nombre de cliente ni de expediente.
- **Datos de terceros** [NORMA Ley 25.326 + INFERENCIA]: guardar actas para el seguimiento es defendible; armar perfiles históricos de competidores es otra finalidad. Requiere política escrita, retención con plazo y posible registro de la base [A VERIFICAR obligación ante la AAIP].
- **robots.txt inaccesible = sin restricciones**: legalmente débil. Si el sitio da error, no leer hasta el próximo ciclo.
- **Términos de uso de COMPR.AR/BAC** [A VERIFICAR]: pueden prohibir acceso automatizado aunque robots.txt lo permita. Fase 0 debe anotarlo por portal.
- **Alucinación de plazos a escala**: un error en `marco_normativo.md` se replica a todos los clientes. Falta un test de regresión con casos reales (fecha disparador → vencimiento esperado).

### 2. Mejoras de producto que no están en el plan

| Mejora | Valor | Esfuerzo | Costo |
|---|---|---|---|
| Calendario de vencimientos por cliente (ICS/mail) con hecho disparador, norma y estado "confirmado por humano" | Altísimo | Medio | Bajo |
| Checklist de aptitud del cliente (SIPRO, situación fiscal, registros de obra) con recordatorios | Alto | Bajo | Bajo |
| Comparativo de ofertas post-apertura con borrador de observaciones/impugnación | Alto | Alto | Medio |
| Resumen semanal por cliente firmado por un humano | Medio-alto | Medio | Bajo |
| Modo "segunda opinión" de pliegos (monetizable por unidad) | Alto | Medio | Medio |

### 3. Decisiones del dueño antes de arrancar

- Mail de contacto y texto del User-Agent.
- Dónde corre el monitor (VPS en Argentina u oficina) y titular de la IP.
- Qué hacer si los términos de uso de un portal prohíben automatización.
- Política de datos de terceros (qué, cuánto tiempo, si hay base histórica de competidores).
- Cláusula contractual con clientes: la IA asiste, la consultora responde.
- Quién firma cada alerta con consecuencia legal y en qué plazo.
- Presupuesto mensual de tokens y tope de corte.
- Jurisdicciones iniciales según cartera real.

### 4. Priorización final

1. Decisiones del punto 3 + Fase 0 + cláusula con clientes.
2. Back-off y "robots inaccesible = no leer"; UA sin huella de cliente.
3. Fase 1 (N1, P1/P3 con ventana pre-apertura, P5) + calendario de vencimientos con doble cómputo y test de regresión de plazos.
4. Checklist de aptitud del cliente.
5. P2 + N3 (módulo como evento).
6. J1/J2.
7. Comparativo de ofertas y "segunda opinión".
8. Resto (N2–N8, P4 con política de datos, P6/P7, INDEC).

## Estado de implementación tras el consejo

- Hecho: robots.txt respetado; **robots inaccesible = no leer** (se reintenta el próximo ciclo); 5 s entre pedidos por dominio; bitácora interna con motivo (`data/accesos.jsonl`); UA con nombre del sistema + contacto, sin clientes ni expedientes; ante 403/429/503 se pausa el dominio 24 h **y se abre una alerta** para decisión humana.
- Pendiente de decisión del dueño: ver sección 3 del Asesor.
- Pendiente de desarrollo: ventana pre-apertura horaria, calendario de vencimientos con doble cómputo, test de regresión de plazos, checklist de aptitud del cliente, búsquedas públicas (P2).
