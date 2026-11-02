# Plan de fuentes: qué miramos, cada cuánto y cómo

> **Estado:** borrador para revisión. Ninguna URL fue visitada para armar este plan. Las direcciones salen
> de conocimiento previo y están marcadas **[URL A CONFIRMAR]** hasta que una persona las abra y valide.
> Nada se automatiza antes de completar la **Fase 0** (sección 5).

## 1. Principios: que nada parezca raro (porque nada lo es)

1. **Solo información pública y sin login.** No usamos usuarios ni contraseñas de clientes, no resolvemos
   captchas, no evadimos bloqueos ni límites. Si un portal pide login o bloquea, se pasa a vía manual o formal.
2. **Datos abiertos primero.** Si existe un dataset, API, RSS o descarga oficial, se usa eso antes que leer páginas.
3. **Identificación transparente.** User-Agent con nombre del sistema y un mail de contacto de la consultora.
   Sin disfrazarnos de navegador.
4. **Ritmo humano.** Máximo 1 pedido cada 5 segundos por portal, solo las páginas necesarias, con caché.
   Nada de recorrer portales completos.
5. **Respetar robots.txt y términos de uso** de cada sitio (se revisan a mano en la Fase 0 y se documentan).
6. **Bitácora de accesos.** Cada acceso queda registrado (fecha, URL, motivo, resultado) para poder
   mostrar exactamente qué se consultó y por qué.
7. **Vía formal para lo que no está publicado.** Expedientes GDE y actuaciones internas: pedido de vista
   (procedimiento administrativo) o acceso a la información pública (Ley 27.275). La IA redacta, una persona firma
   y presenta.
8. **Datos personales.** Ofertas y actas tienen nombres, CUIT y montos: se guardan solo para el fin del
   seguimiento (Ley 25.326), sin difundirlos fuera del equipo.

## 2. Catálogo de fuentes

Frecuencias: **3×D** = 09:00, 14:00 y 18:30 · **D** = diario hábil · **S** = semanal · **M** = mensual ·
**DEM** = a demanda (cuando un agente lo necesita).

### 2.1 Normativa (qué cambia en las reglas)

| # | Fuente | Qué miramos | Frec. | Método | URL |
|---|---|---|---|---|---|
| N1 | Boletín Oficial de la Nación — 1.ª sección | Leyes, decretos, resoluciones y disposiciones que toquen contrataciones | D 08:20 | Sumario del día → filtro por palabras clave → lector | boletinoficial.gob.ar/seccion/primera/AAAAMMDD [URL A CONFIRMAR] |
| N2 | InfoLEG | Texto actualizado y "normas que modifican" del marco base | S + DEM | Ficha de cada norma del marco | infoleg.gob.ar / servicios.infoleg.gob.ar [URL A CONFIRMAR] |
| N3 | Oficina Nacional de Contrataciones (ONC) | Comunicaciones generales, valor del módulo, pliegos modelo, manuales, normativa propia | S | Página de normativa/novedades de la ONC | argentina.gob.ar/jefatura/innovacion-publica/oficina-nacional-de-contrataciones [URL A CONFIRMAR] |
| N4 | SIGEN | Normas de control, precios testigo y normas sobre contrataciones | S | Sección normativa | sigen.gob.ar [URL A CONFIRMAR] |
| N5 | Procuración del Tesoro (PTN) | Dictámenes con doctrina sobre contrataciones | S | Buscador o listado de dictámenes | ptn.gob.ar [URL A CONFIRMAR] |
| N6 | SAIJ | Jurisprudencia y doctrina sobre contratos administrativos | DEM | Buscador | saij.gob.ar [URL A CONFIRMAR] |
| N7 | Oficina Anticorrupción | Guías de integridad (Ley 27.401) y conflicto de intereses (Ley 25.188) | M | Página de publicaciones | argentina.gob.ar/anticorrupcion [URL A CONFIRMAR] |
| N8 | Congreso (Diputados y Senado) | Proyectos de ley sobre contrataciones (alerta temprana) | S | Buscador de proyectos | hcdn.gob.ar · senado.gob.ar [URL A CONFIRMAR] |
| N9 | Boletines oficiales provinciales y de CABA | Ídem N1, solo en las jurisdicciones donde haya clientes | D | Ídem N1 | ver 2.3 |

### 2.2 Procesos nacionales (oportunidades y expedientes en curso)

| # | Fuente | Qué miramos | Frec. | Método | URL |
|---|---|---|---|---|---|
| P1 | COMPR.AR | (a) **expedientes seguidos**: convocatoria, circulares, acta de apertura, cuadro comparativo, dictamen de evaluación, impugnaciones, adjudicación, orden de compra | 3×D | Vista pública de cada proceso; se compara con la foto anterior | comprar.gob.ar [URL A CONFIRMAR formato de vista pública] |
| P2 | COMPR.AR | (b) **convocatorias nuevas** por rubro u organismo de interés de los clientes | D | Búsqueda pública de procesos, o dataset abierto (P4) si existe | comprar.gob.ar [URL A CONFIRMAR] |
| P3 | CONTRAT.AR | Obra pública nacional: ídem P1 y P2 | 3×D / D | Ídem | contratar.gob.ar [URL A CONFIRMAR] |
| P4 | Datos abiertos (datos.gob.ar) | Datasets de convocatorias y adjudicaciones de COMPR.AR / CONTRAT.AR: histórico de precios, competidores, organismos | S | Descarga del dataset (sin scraping) | datos.gob.ar [URL A CONFIRMAR existencia y periodicidad] |
| P5 | Boletín Oficial — 3.ª sección (Contrataciones) | Convocatorias publicadas por organismos que no usan COMPR.AR o que publican en ambos lados | D | Sumario del día → lector | boletinoficial.gob.ar/seccion/tercera/AAAAMMDD [URL A CONFIRMAR] |
| P6 | Organismos y empresas del Estado con portal propio | Ej.: Vialidad Nacional, AySA, empresas energéticas y otras sociedades del Estado; universidades nacionales | D | Página de licitaciones de cada uno | **relevar según cartera de clientes** |
| P7 | Proyectos con financiamiento internacional (BID, Banco Mundial, CAF) | Llamados en Argentina bajo normas del banco, no del Decreto 1023/2001 | S | Avisos de adquisiciones de cada banco | [URL A CONFIRMAR] |

### 2.3 Provincias, CABA y municipios (solo donde haya clientes o interés)

| # | Jurisdicción | Portal de compras | Boletín oficial | Norma base |
|---|---|---|---|---|
| J1 | CABA | Buenos Aires Compras (BAC) y BAC Obras [URL A CONFIRMAR] | Boletín Oficial CABA [URL A CONFIRMAR] | Ley 2095 [A VERIFICAR] |
| J2 | Provincia de Buenos Aires | PBAC [URL A CONFIRMAR] | Boletín Oficial PBA [URL A CONFIRMAR] | Ley 13.981 + Decreto 59/2019 [A VERIFICAR] |
| J3 | Córdoba | Portal de compras públicas [URL A CONFIRMAR] | Boletín Oficial Córdoba [URL A CONFIRMAR] | [A VERIFICAR] |
| J4 | Santa Fe | Portal de compras [URL A CONFIRMAR] | Boletín Oficial Santa Fe [URL A CONFIRMAR] | [A VERIFICAR] |
| J5 | Mendoza | Instancia propia de COMPR.AR [A CONFIRMAR] | Boletín Oficial Mendoza [URL A CONFIRMAR] | [A VERIFICAR] |
| J6 | Resto de provincias y municipios | Se agregan uno por uno cuando aparezca un cliente o un proceso de interés | — | — |

### 2.4 Vías que NO se automatizan

| Qué | Por qué | Cómo se hace |
|---|---|---|
| Expedientes GDE / actuaciones internas | No están publicados en línea | Pedido de vista o de acceso a la información pública; la IA redacta, una persona presenta |
| Escritorio de proveedor en COMPR.AR / CONTRAT.AR, SIPRO, TAD | Requieren login del cliente | Lo opera el cliente o la consultora a mano; la IA solo recibe lo que se le pase |
| Portales con captcha o que bloqueen el acceso automático | No se evaden | Revisión manual, o pedido de acceso a datos abiertos al organismo |

## 3. Cómo se lee cada fuente (cadena de agentes)

1. El **monitor** (código, sin IA) descarga la página o dataset y lo compara con la foto anterior.
   Si no cambió, no se gasta ningún token.
2. Si cambió, **Haiku (lector)** lee el material crudo con líneas numeradas y devuelve un extracto fiel.
3. **Opus (analista)** analiza el extracto. Si tiene dudas:
   - le **pregunta a Haiku** sobre la misma fuente (`preguntar_al_lector`), y Haiku responde con cita textual y
     número de línea;
   - con esa ubicación, Opus **va al lugar preciso** (`ver_fragmento`) y lee el texto original de esas líneas, sin
     releer todo el documento.
4. **Fable (Especialista)** recibe lo urgente, verifica plazos, decide y genera la alerta. El Asesor audita
   en el consejo semanal.

## 4. Riesgos técnicos

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Los portales bloqueen IPs extranjeras o de datacenter (GitHub Actions corre en EE. UU.) | El monitor no lee | Runner propio en Argentina (VPS chico o una PC de la oficina) |
| Páginas dinámicas (ASP.NET) que no muestran contenido sin JavaScript | Foto vacía o incompleta | Navegador headless solo para esas URLs, o dataset abierto |
| Cambios de diseño en los portales | Falsos "sin cambios" o falsos cambios | Alerta a las 3 fallas seguidas y revisión del extracto vs. la foto |
| Haiku omite un dato | Opus no lo ve | Citas textuales obligatorias, diferencias crudas para Opus y preguntas de seguimiento a Haiku |

## 5. Plan de implementación por fases

| Fase | Qué | Quién |
|---|---|---|
| **0. Validación manual** | Abrir cada URL de este plan, confirmarla, leer robots.txt y términos de uso, anotar si pide login o captcha y si hay dataset abierto. Definir el mail de contacto del User-Agent. | Persona del equipo (≈ 2-3 h) |
| **1. Núcleo** | N1, P1, P3 (expedientes seguidos) y bitácora de accesos | Sistema (ya está la base) |
| **2. Oportunidades** | P2, P4 y P5: convocatorias nuevas por rubro y organismo | Sistema |
| **3. Normativa ampliada** | N2-N8 semanales | Sistema |
| **4. Jurisdicciones** | J1-J6 según cartera de clientes | Sistema + validación manual de cada portal |
| **5. Financiamiento internacional y portales propios** | P6, P7 | Sistema |
