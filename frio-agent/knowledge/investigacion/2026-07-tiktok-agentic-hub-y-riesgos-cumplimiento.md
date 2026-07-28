# TikTok lanzó SUS PROPIOS agentes — y dos riesgos de cumplimiento que nos tocan

**Fecha:** 2026-07-28. **Segunda pasada.** Cierra la brecha "reglas de divulgación de IA
— sin examinar" del documento `2026-07-gmv-max-y-agentes-autonomos.md`.

## ⚠️ Método
`WebFetch` bloqueado al 100% (403 de política de red en todos los dominios) y
presupuesto de búsqueda agotado. **Cero páginas primarias leídas.** Todo viene de
extractos de buscador — un escalón por debajo de lo que exige nuestra regla. **Cada
cita debe re-verificarse en su URL antes de guiar una decisión de construcción.**

---

## 1. ★ TikTok lanzó un Agentic Hub + servidor MCP oficial (30-jun-2026)

| | |
|---|---|
| Qué | Marketplace de "AI Skills" sobre **TikTok for Business MCP** |
| Docs | `business-api.tiktok.com/portal/docs/tiktok-ads-mcp-server/v1.3` (ya va en v1.3) |
| Expone | gestión de campañas, reporting, audiencias, operaciones de creativos, catálogo |
| Escrituras | `POST /campaign/create/`, `POST /campaign/update/` (nombre, presupuesto, modo) |
| Acceso | cuenta TikTok for Business + Business Center dueño de la cuenta publicitaria |
| Socios | HubSpot, Wix, Constant Contact, WorkMagic, Innovid, Kochava, Shoplazza… |

**Autonomía: NO VERIFICADO.** Un analista describe las Skills como *"single-job Skills
with no unattended-spend claims"* y *"human approval gates… el cambio es de 'entramos a
Ads Manager' a 'aprobamos lo que un agente propuso'"* — pero eso es **caracterización de
un analista, NO texto oficial de TikTok.** No pude verificar si TikTok **exige**
aprobación humana o si simplemente las Skills actuales funcionan así. **Esta distinción
es crítica para nosotros y está sin verificar.**

Dato notable: **la plataforma convergió independientemente en NUESTRO invariante de
seguridad** — el agente propone, el humano autoriza el gasto.

### Seller Center "AI Homepage" — 5 agentes (beta 9-abr-2026)
Solo vendedores US L2L seleccionados, solo PC. Los cinco: Shop Insight, To-Do List, New
Seller Coach, Smart Product Analysis, Product Opportunity Radar + un "Seller Assistant"
lateral que puede lanzar campañas GMV Max con acciones *"guided or one-click"*.

**Veredicto: son superficies de recomendación + ejecución de un clic, NO agentes
autónomos.** Señalan y sugieren; un humano hace clic.

### ¿Nos vuelve redundantes? No — pero mueve la frontera
TikTok se quedó con **puja, ubicación y selección de creativo**. Sus nuevos agentes se
quedan con **mostrar insights y ejecutar de un clic**. Ninguno hace lo que ya
identificamos como nuestra capa defendible: **medición independiente y determinista de
P&L con veredicto por producto** — que vale MÁS ahora que la plataforma es a la vez
optimizador y árbitro que se autocalifica.

**El MCP es una plataforma para montarnos, no un competidor a vencer.** Da la superficie
de escritura (presupuesto, campaña, creativo, catálogo) que SÍ sobrevive a GMV Max — y
son exactamente los controles hacia los que ya recomendamos re-ponderar la Fase 6.

---

## 2. ¿La política permite un agente autónomo? — SÍ, con controles

**No se halló ninguna cláusula que lo prohíba.**
- **Developer ToS de TikTok:** *"you may use automated means in your Application to
  collect information from or otherwise interact with the TikTok Developer Services, as
  described in the TikTok Developer Documentation."* TikTok se reserva **auditar**.
- **Automated Rules nativas de TikTok:** hasta 5 condiciones + 1 acción, evaluadas
  **cada 30 minutos**, y pueden **auto-pausar bajos rendimientos Y auto-SUBIR presupuesto**
  cuando el ROAS supera un objetivo. *La propia TikTok envía automatización autónoma que
  AUMENTA gasto* — la evidencia más fuerte de que escalar por agente está sancionado.
- Terceros ya lo hacen: Bïrch (ex-Revealbot) es socio oficial de Meta, Google, TikTok y Snap.

**Permitido ≠ fácil:** la Marketing API sigue siendo "la más restringida de las grandes
APIs de paid social" (sandbox → revisión → verificación de negocio → auditoría de
seguridad de datos).

---

## 3. 🚨 Qué SÍ te banea — y dos riesgos que nos tocan directo

**Formulación clara:** TikTok permite automatización **a través de superficies API
sancionadas**, y prohíbe la que alcanza el servicio **por fuera** de ellas, o que
fabrica engagement/identidad.

- **Manipulación de plataforma** = *"usar automatización para registrar u operar cuentas
  en masa"*; las Community Guidelines prohíben *"herramientas de automatización, scripts
  u otros trucos diseñados para eludir sus sistemas"*.
  → **Automatización de navegador / clics scripteados en Seller Center = vector de baneo.
  API = puerto seguro.** REGLA ADOPTADA: prohibido el browser automation en todo el código.
- **Responsabilidad por cuentas conectadas:** una sanción se extiende a cuentas ligadas.
- **Escala de enforcement (H1 2025):** 70M+ artículos bloqueados, 200k+ productos
  removidos post-listado, **700k+ cuentas de vendedor desactivadas**.

### 🚨 RIESGO A — "digital renderings" vs nuestros mockups POD
La Product Listing Policy prohíbe *"placeholders and digital renderings of a product"*;
la imagen principal debe ser fondo blanco puro, sin logos/texto/gráficos añadidos.
**Nuestros mockups de Fase 2 SON renderizados digitales.** Conflicto directo, sin
resolver.
⚠️ Contra-evidencia (inferencia, no prueba): POD se vende masivamente en TikTok Shop con
integraciones Printful/Printify, lo que sugiere que no se aplica a mockups POD. **ALTA
prioridad de verificar en la fuente antes de publicar listados.**

### 🚨 RIESGO B — divulgación de contenido IA es OBLIGATORIA
Aplica a imágenes de producto generadas con IA, modelos IA, y escenas de estilo de vida
fabricadas — **incluso si el producto es real pero el entorno es generado**. Exento:
edición ligera (corrección de color, quitar fondo).
**Penalizaciones:** advertencias → restricción de publicación → **inhabilitar
PERMANENTEMENTE el retiro de comisiones** → baneo permanente. Hay detección automática
escaneando contenido sintético no divulgado.
⚠️ **Discrepancia de fechas sin resolver:** una fuente dice vigente 13-may-2026, otra
dice penalizaciones escalonadas desde 26-may-2026. Ambas de terceros. No citar ninguna.

**ACCIÓN TOMADA:** `require_ai_disclosure` pasó de `False` a **`True` por defecto**
(config.py). Estaba apagada por considerarse solo un tema FTC; ahora hay mandato de
plataforma con penalización severa. Bajo incertidumbre, el default seguro es divulgar.

---

## 4. Livestream con IA: PROHIBIDO. Video pregrabado con IA: permitido (con etiqueta)

- **Douyin** (norma AIGC, may-2023): los humanos virtuales deben registrarse, el operador
  debe tener autenticación de nombre real, y **un livestream con persona virtual debe ser
  conducido por una persona real en tiempo real — la interacción totalmente por IA NO se
  permite.** Enforcement: **170,000+ salas procesadas** por "无人直播" (livestream sin
  humano) — cifra a nivel de titular, sólida.
- **Un VP de Douyin Group (李亮) declaró on-record** que el livestream sin humano está
  prohibido y se sanciona.
- **WeChat Channels (视频号)** fue más lejos: propuso prohibir el livestream virtual (2024).
- **TikTok Shop convergió (~jul-2026):** prohibió **voces IA y audio pregrabado** en LIVEs
  comerciales; se exige comunicación verbal (o en lengua de señas) en tiempo real.
  Enforcement vía Creator Health Rating → restricción de comisión → baneo.
  ⚠️ Detalles menos confiables (NO citar como hecho): el tope de "avatar ≤50% de pantalla"
  y la frase exacta de la política.

**Lectura neta para Frío:**
1. ✅ **El video corto pre-producido con IA para anuncios sigue permitido en todas las
   plataformas, sujeto a etiquetado.** Es exactamente el carril de nuestra Fase 3 — intacto.
2. ❌ **El hosting autónomo de livestream con IA está prohibido en Douyin, WeChat Channels
   y TikTok Shop.** **Debe quedar FUERA del roadmap.**

---

## 5. Dropshipping y POD — política

**Dropshipping: permitido con restricciones — pero TODAS las fuentes son blogs de
vendedores** (AutoDS, Shoplazza, LooperBuy), cada uno con interés comercial. **No se
halló texto oficial.** Restricciones reportadas: dropshipping con proveedor OK,
**arbitraje minorista prohibido**; "In Transit" en 2 días hábiles; lista blanca de
transportistas cross-border desde 1-feb-2026; **depósito de US$1,500 por tienda** desde
15-dic-2025; desde 6-ene-2026 las órdenes USPS deben usar TikTok Shipping.

**POD: soportado, con ruta de integración real.** Printful tiene integración directa con
TikTok Shop (**US + UK**); Printify (**solo US**). Solo el modelo **Seller Shipping** es
compatible. Como ya elegimos Printful, la restricción de región se cumple.

---

## 6. COULD NOT VERIFY / GAPS
- **Ninguna página primaria leída.** Todo es extracto de buscador.
- **Si TikTok EXIGE aprobación humana en las escrituras del MCP** — el desconocido más
  relevante para decidir la arquitectura de la Fase 6.
- **Si la prohibición de "digital renderings" se aplica realmente a mockups POD.**
- **Fechas de vigencia de la divulgación AIGC en conflicto** (13 vs 26-may-2026).
- **Inventario completo de herramientas del MCP** — una fuente dice que TikTok describió
  capacidades pero *"no publicó inventario de herramientas ni endpoints nombrados"*.
- **Política de dropshipping sin fuente autoritativa** — solo blogs de vendedores.
- Sin barrido de GitHub/Product Hunt/YC/Reddit; sin inventario del TikTok Shop App Store;
  **cobertura cero de China/SEA** en esta rama.
- **Esta investigación NO fue exhaustiva.**

## 7. Acciones recomendadas
1. **Re-verificar en la fuente antes de escribir código:** (a) si el MCP de TikTok exige
   aprobación humana en escrituras, (b) el ban de "digital renderings" vs nuestros mockups.
2. **Adoptar el MCP oficial de TikTok como transporte de la Fase 6** — ya usamos MCP para
   Higgsfield, así que el patrón encaja, y convierte nuestra integración más riesgosa de
   "automatización no oficial" a "superficie de socio sancionada".
3. ✅ **HECHO:** divulgación AIGC activada por defecto en el pipeline de creativos.
4. ✅ **REGLA ADOPTADA:** browser automation prohibido en todo el código — es la frontera
   del baneo, no solo una preferencia de limpieza.
5. **Livestream autónomo con IA: fuera del roadmap.** Prohibido en las tres plataformas.

---

## 8. 🚨 BLOQUEADOR CRÍTICO PARA EL REGISTRO (evidencia: docs oficiales espejados)

Del doc oficial "Register as a developer" (`business-api.tiktok.com/portal/docs?id=1738855176671234`,
obtenido vía un espejo verbatim que declara su `source_url`):

- El correo de comunicación **debe ser de dominio de empresa verificado**:
  *"You will be rejected if you are using a personal email or a temporary email."*
- El sitio web de la empresa debe ser **"publicly accessible… valid, functioning, fully
  developed and professionally presented"** y **coincidir con el dominio del correo**.
- ***"[TikTok] cannot onboard personal accounts or individual developers."*
- Resolución en **3 días hábiles**. Tipo de usuario a elegir: **Direct Advertiser**.

**Impacto directo:** una cuenta **@gmail.com será rechazada**. Antes de aplicar hace
falta (a) un dominio propio de IntoSpirit, (b) un correo en ese dominio, (c) un sitio web
vivo y profesional en ese mismo dominio. Esto es de la Marketing API (ads); **NO
VERIFICADO** si TikTok Shop Partner Center exige lo mismo, pero el patrón de pedir
"certificado de registro de empresa" en el flujo que vio el usuario apunta en la misma
dirección.

## 9. 🟢 SANDBOX CONFIRMADO — se puede construir ANTES de la aprobación

Del doc oficial `id=1738855331457026`:
- Base URL: **`https://sandbox-ads.tiktok.com/open_api`**
- **Una cuenta sandbox por app de desarrollador**; los permisos de la app se reflejan
  automáticamente en la cuenta sandbox.
- **~20 endpoints soportados** — exactamente los que necesita nuestra Fase 6: CRUD y
  status de campaign/adgroup/ad, subida de imagen y video, `/report/integrated/get/`,
  identity.
- Límites sandbox: 1 QPS / 30 QPM / 1,000 QPD por endpoint.
- ⚠️ **Datos de reporte simulados SOLO para 2020-12-08 → 2020-12-19** → la lógica de
  métricas sigue necesitando nuestros fixtures offline (que ya tenemos).

## 10. Contrato operativo de la Ads API — restricciones que el código DEBE respetar

| Restricción | Valor | Por qué importa |
|---|---|---|
| **`DELETE` es IRREVERSIBLE** | *"The operation status of a deleted campaign cannot be modified"* | **Un "kill" jamás debe mapear a DELETE.** Solo `DISABLE`. → `ads_kill_operation="DISABLE"` |
| **Bloqueo de presupuesto** | **23:55–00:00** en la zona horaria de la cuenta | No se pueden fijar ni actualizar presupuestos. El scheduler nunca debe intentarlo ahí. |
| Lotes | 20 IDs por request (status, presupuesto, creación de ads) | Hay que trocear. |
| Rate limit por defecto | Tier **Basic: 10 QPS / 600 QPM / 864,000 QPD**; error `40100` | Generoso para nuestro loop. |
| Reportes sync | máximo 30 días por request | Rangos mayores → async. |
| Async reports | 1 QPS/app, 4,500 tareas/app/día, 500 creaciones/cuenta/hora | |
| Latencia de datos | ~11 horas (reportado por Airbyte, terceros) | Re-sincronizar ≥3 días por atribución. |

### La revisión de anuncios es ASÍNCRONA y SIN SLA — cambia la arquitectura del loop
`GET /ad/review_info/` devuelve `ALL_AVAILABLE` | `PART_AVAILABLE` | `UNAVAILABLE`.
**No se halló ningún SLA documentado — la latencia es NO VERIFICADA.**
El pipeline **no puede asumir "creado = sirviendo"**. Debe: crear → **consultar
`review_info` hasta `ALL_AVAILABLE`** → recién ahí arrancar el reloj de gasto/medición →
si `UNAVAILABLE`, regenerar el creativo o apelar (`/adgroup/appeal/`, también por
consulta repetida).
⚠️ **Trampa silenciosa:** tratar `PART_AVAILABLE` como éxito. Significa entrega
geográfica parcial → distorsiona el cálculo de CPA/ROAS contra el targeting pretendido.

### GMV Max: candado de exclusividad
*"For each TikTok Shop, only one ad account can be authorized to create GMV Max
Campaigns using the TikTok Shop."* Requiere `exclusive_authorization/create/` y aceptar
las GMV Max Guidelines. La superficie de acción se reduce a: **objetivo de ROAS +
presupuesto diario + selección de productos/identidades + añadir/quitar creativos +
pausar.** `GET /gmv_max/bid/recommend/` da un valor de referencia **de la propia TikTok**
para contrastar cualquier ROAS que proponga el LLM — guardarraíl determinista gratis.
Usar `request_id` como idempotencia para que un reintento no duplique una campaña que gasta.

### Automated Rules como segundo interruptor de emergencia
Acciones disponibles: `TURN_ON`, `TURN_OFF`, `MESSAGE`, `DAILY_BUDGET`,
`LIFETIME_BUDGET`, `BID`. Recomendación de ingeniería: **incluso con nuestro motor como
optimizador principal, registrar una regla `TURN_OFF` del lado de TikTok sobre un umbral
de gasto/ROAS** — un segundo interruptor independiente que sigue funcionando **aunque
nuestro proceso muera**. Ganancia de seguridad real para un sistema que gasta solo.

## 11. ⚠️ Los ToS de desarrollador NO se pudieron leer
`developers.tiktok.com` bloqueado. **No se puede afirmar nada sobre qué dicen los ToS
respecto a decisiones automatizadas, auto-pujas, operaciones masivas o creación de
anuncios totalmente automática.** Hay endpoints `term/check|confirm|get` — o sea, existen
términos que el anunciante debe aceptar programáticamente, y su contenido es justo lo que
no pudimos leer.
**REGLA: un humano debe leer los ToS antes de cualquier gasto real.** Es decisión
legal del dueño, no una que yo pueda asumir.

---

## 12. 🚨 GMV Max SUBE SU PROPIO PRESUPUESTO — agujero en nuestro modelo de seguridad

**El hallazgo más importante para la arquitectura, y el más peligroso.**

Docs de ayuda de TikTok (`about-gmv-max-auto-budget-increase`,
`about-one-click-gmv-max-campaign-creation` — V-SEARCH, no leídas directamente):
GMV Max **aumenta su propio presupuesto diario hasta +50%, reportadamente varias veces
en un mismo día**, cuando el ROI se sostiene. También **crea campañas enteras solo** para
productos inscritos en eventos promocionales de TikTok Shop.
⚠️ Los multiplicadores exactos ("+50%, hasta 10× el mismo día") mezclan el artículo de
ayuda con blogs de terceros — **el mecanismo está bien corroborado, las cifras exactas NO**.
Confirmarlas contra el artículo oficial antes de codificarlas en lógica de topes.

Meta Advantage+ y Google PMax se comportan igual.

### Por qué esto rompía nuestro diseño
Nuestro `spend_ledger` registra **lo que NOSOTROS autorizamos**. Si la plataforma gasta
por su cuenta, el ledger queda limpio mientras el dinero real se va. **Confiar solo en el
ledger, con GMV Max encendido, sería una falsa sensación de seguridad.**

**La plataforma debe modelarse como un ACTOR EXTERNO que puede romper nuestro tope.**

### ✅ ACCIÓN TOMADA
`spend.reconcile_platform_spend()` — compara lo autorizado contra el gasto **real
reportado por la plataforma**:
- Detecta y reporta la deriva (`platform_overspent`, `drift_usd`).
- **Lanza `SpendCapError` si el gasto REAL supera el tope diario**, aunque nuestro ledger
  esté impecable — porque el tope ya se rompió en el mundo real.
- **Regla:** todo conector de anuncios en vivo DEBE llamarla en cada ciclo de polling.
- Tests en `tests/test_spend_reconcile.py`.

---

## 13. Validación independiente de nuestro invariante (barrido V-CODE de GitHub)

**Resultado negativo sólido: no existe ningún repo open source que sea un agente autónomo
para vender en TikTok Shop. Ninguno.** El espacio se divide en tres mitades que **nadie ha
unido jamás**: SDKs de TikTok Shop · MCPs de TikTok Ads · skills de creativos UGC.

Búsquedas que devolvieron **cero**: `autogpt ecommerce agent selling`,
`langgraph ecommerce autonomous agent product`, `tiktok shop automation agent gmv`,
`ecommerce agent autonomous product listing ads spend`.
**No hay agente de e-commerce basado en AutoGPT. Ni de TikTok Shop con CrewAI. Ni de
dropshipping TikTok con CJ** (los repos de CJ son wrappers pelados, 0–1★).

### Dos proyectos llegaron por su cuenta a NUESTRO invariante exacto
- `superjack2050/1688-cli` (47★): compras protegidas tras prompts TTY o un flag `--agent`
  explícito *"so agents can't move money silently"* — el mejor diseño de compuerta de gasto hallado.
- `wes4ray-coder/store-command-center-public`: "prayer queue" de aprobación humana;
  `paypal_payout`/`wallet_send`/`secret_export` son compuertas duras **no desactivables**;
  el resto se auto-ejecuta dentro de topes.
- `mvanhorn/printing-press-library`: MCP deliberadamente **solo lectura** —
  `"mcp_ready": "safe_v1_read_only"`, mutaciones *"deferred until idempotency and retry
  behavior are designed"*.

**Nuestro invariante está alineado con el consenso, no atrasado respecto a él.**

### ⚠️ Y el contraejemplo que muestra el riesgo
`amekala/ads-mcp` (75★): **37 herramientas de TikTok, ciclo completo — pausar/reanudar/
actualizar campañas, grupos, anuncios y presupuestos. Gasto real. Única protección:
"las campañas nuevas siempre se crean pausadas". Sin aprobación secundaria.**
`pizzzzzza/printkk-agent-skill` (9★): enseña a agentes a **crear órdenes PrintKK y pagar
con wallet**, **sin compuerta, sin estimación de costo, sin confirmación documentada.**

### Vaporware — la trampa de este espacio
- `Zeeshanahmad4/TikTok-Shop-Affiliate-Outreach-Bot` (**56★**): **SIN CÓDIGO FUENTE.** Solo
  README — repo de marketing de una app de escritorio cerrada y de pago. **El "bot" de
  TikTok Shop con más estrellas de GitHub no tiene código adentro.**
- `Two-Weeks-Team/socialseed-agent`: **el repo contiene únicamente un LICENSE. Cero código.**
- `Vanszs/tiktok-viral-factory` (6★): el README dice "publica… totalmente automatizado";
  **el código dice `TikTok integration (manual → auto-post) ⬜ Pending`.**

**Lección de método:** dos de estos fueron reportados inicialmente como agentes autónomos
funcionales **basándose en sus READMEs**. Revisar el código los desmintió. Nunca creer un
README sin abrir el código.

### Competidores comerciales — lo verificado
- **Agentative** (agentative.ai): producto real, **híbrido configurable** — *"puedes fijar
  requisitos de aprobación para cualquier tipo de acción que quieras revisar antes de que
  se ejecute"*. Misma postura que Frío. **Pero: empresa anónima, sin fundadores, sin
  financiación, sin reseñas independientes.** ⚠️ Discrepancia de precio sin resolver:
  $49/mes vs $149/mes, ambas de su propio sitio.
- **Stormy AI** (YC S24): legítima y financiada, **pero NO es competidora** — es de
  contacto con creadores. Su propio blog: *"marca campañas de bajo rendimiento **para que
  tú las pauses**"* y avisa de stock *"en una hoja de cálculo compartida"*. Marca y avisa;
  no actúa. Su biblioteca de blogs sobre TikTok Shop es **SEO, no su producto.**
- **Creatify**: el tercero más cercano a autonomía real — integración de **escritura** a
  cuentas de Meta/Google/TikTok. Aun así: *"tú fijas objetivos y guardarraíles y apruebas
  la dirección… tú tienes la última palabra."*

**Conclusión estructural:** la autoridad de gasto sin supervisión está en manos de **las
propias plataformas publicitarias**, no de ningún proveedor de AI-UGC. Todas las
herramientas creativas se detienen en "listo para publicar" o "lanza con un clic".
