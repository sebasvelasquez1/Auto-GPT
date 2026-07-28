# GMV Max, Icon.com y el estado real de los agentes autónomos de comercio

**Fecha:** 2026-07-28. **Estado del research: PRIMERA PASADA, NO EXHAUSTIVA.**

## ⚠️ Advertencia de método (leer primero — regla de knowledge/README.md)

Esta investigación se corrió con **dos limitaciones duras del entorno**:
1. **`WebFetch` bloqueado al 100%** — la política de red del entorno devuelve 403 a
   todos los dominios. **No se leyó ni una sola página primaria.** Todo lo de abajo
   viene de *extractos de buscador*, un escalón de evidencia por debajo de lo que
   esta regla exige.
2. **Presupuesto de búsquedas agotado** (200/200) a mitad de la investigación.

**Consecuencia:** cada cita de política DEBE re-verificarse contra su URL primaria
antes de guiar una decisión de construcción. Se marca la confianza por afirmación.
Varias ramas (indie builders, China/SEA, Partner Center) quedaron sin cubrir.

---

## 1. ★ HALLAZGO PRINCIPAL — TikTok se quedó con el loop: GMV Max es obligatorio

**Confianza: ALTA en el hecho, MEDIA en las fechas exactas (extracto de buscador).**

- TikTok **retiró la puja manual para anuncios de Shop**. Video Shopping Ads y
  Product Shopping Ads **discontinuados el 15-jul-2025**; **GMV Max obligatorio
  ~1-sep-2025**.
- La arquitectura que permitía "fijar topes de puja, listas de keywords y controlar
  ubicaciones" **fue eliminada**, reemplazada por un único tipo de campaña
  automatizada que optimiza GMV total de la tienda.
- El endpoint legacy de Smart+ Campaign Creation API se apagó tras el 31-mar-2026.
- Fuentes (extractos, no leídas): influencermarketinghub.com/tiktok-shop-gmv-max-advertisers/ ;
  shopifreaks.com/tiktoks-move-to-gmv-max-is-getting-backlash-from-advertisers/ ;
  ads.tiktok.com/help/article/gmv-max-migration-tiktok-shop-ads (403, no leída)

### Qué significa para Frío, sin adornos
Nuestro motor de optimización a nivel de anuncio (Fase 4 + Fase 6) apunta a
**superficies de control que TikTok ya eliminó** para vendedores de Shop. En 2026 no
se puede ajustar autónomamente puja/ubicación/keywords en TikTok Shop — lo hace la IA
de TikTok y no ofrece la perilla.

### Pero hay una grieta importante — y es NUESTRA oportunidad
Compradores de medios reportan que TikTok **atribuye a GMV Max todas las compras de
la tienda ocurridas durante la campaña, incluso de clientes que nunca vieron un
anuncio** — inflando el desempeño reportado. **La plataforma es a la vez el
optimizador y el árbitro que se califica solo.** Por eso la medición independiente de
P&L gana valor justo cuando el control de anuncios se pierde.

**Lo mismo ocurre en otras plataformas:** Meta Advantage+ y Google Performance Max
absorbieron la capa de optimización igual que GMV Max.

### ✅ EVIDENCIA DURA — el contrato de API oficial de TikTok lo confirma
**Confianza: ALTA.** Único artefacto leído de fuente PRIMARIA en toda la investigación:
el SDK oficial `github.com/tiktok/tiktok-business-api-sdk` (org `tiktok`), archivos
`yml_files/campaign_gmv_max_create.yml` y `gmv_max_bid_recommend.yml`.

**Campos que el anunciante puede fijar al crear una campaña GMV Max:**
`advertiser_id, store_id, campaign_name, budget, auto_budget_enabled, roas_bid,
deep_bid_type, optimization_goal, shopping_ads_type, item_list, identity_list,
schedule_*`

**NO existe targeting en la API. Ninguno.** Sin audiencia, sin intereses, sin
edad/género, sin ubicaciones, sin lookalike, sin keywords, sin ajuste de puja, **sin
objeto ad group** (el nivel de grupo de anuncios no existe en GMV Max).

Los enums traen una bandera `is_valid`, y solo permiten UNA configuración legal:

| Campo | Únicos válidos | Marcados `is_valid: false` |
|---|---|---|
| `optimization_goal` | **`VALUE` solamente** | 27 otros (CONVERT, CLICK, REACH, VIDEO_VIEW…) |
| `deep_bid_type` | **`VO_MIN_ROAS` solamente** | DEFAULT, MIN, PACING, AEO, VO_MIN… |
| `shopping_ads_type` | `LIVE`, `PRODUCT` | **`PRODUCT_SHOPPING_ADS`**, **`VIDEO`**, CATALOG_LISTING_ADS |

Además: la puja la **recomienda la plataforma** (`GET /gmv_max/bid/recommend/`), y la
selección de video por defecto es `AUTO_SELECTION` = *"video auto selected by automation"*.

⚠️ **Matiz honesto:** `is_valid:false` es específico de ESTE endpoint. Prueba que esos
valores **no se aceptan al crear una campaña GMV Max**; **NO prueba por sí solo** el
retiro global de VSA/PSA, y **no trae fechas**. No convertir esto en "TikTok retiró VSA
el 1-sep-2025" — esa inferencia no la sostiene el artefacto.

### El mismo patrón en China (Qianchuan/巨量引擎) — y aún más cerrado
SDK comunitario `bububa/oceanengine` (comentarios transcritos de docs oficiales, no
verificables directamente). En modo 托管 (gestionado):
- La estrategia entera del comerciante son **dos opciones**: `0 优先跑量` (priorizar
  volumen) o `1 优先成本` (priorizar costo).
- `CampaignID` **devuelve null** en planes gestionados.
- No se puede editar el targeting geográfico.
- **DECISIVO:** *"目前暂不支持拉取开启'计划托管'功能的广告计划数据"* — bajo 托管, una
  herramienta de terceros **ni siquiera puede LEER los datos de rendimiento por plan o
  por creativo vía API.**
- En 全域推广 el reporting es **solo agregado a nivel cuenta**, sin dimensión por
  anuncio ni por creativo. `PROGRAMMATIC_CREATIVE` es el único tipo permitido.

### La implicación honesta para un agente autónomo de anuncios
El loop clásico del optimizador autónomo — leer métricas por creativo → matar
perdedores → escalar ganadores → ajustar targeting/pujas — está **estructuralmente no
disponible** en estos modos. No es "en desventaja competitiva": **la API no expone ni
los datos para leer ni las palancas para mover.**

**Lo que SÍ sobrevive fuera de la zona en disputa** (razonamiento, no cita): suministro
de producto y creativos (la plataforma sigue necesitando videos y títulos), pre-scoring
antes de lanzar, **P&L real cruzando COGS/fulfillment/devoluciones** (la plataforma
optimiza ROAS sobre SU gasto, no la ganancia neta del comerciante), decisiones de
portafolio entre productos, y el veredicto cosechar/cancelar. **El analizador comercial
y el pre-score de Frío quedan FUERA de la zona en disputa; el motor de kill/scale a
nivel anuncio queda DENTRO.**

---

## 2. ★ CASO DE ADVERTENCIA — Icon.com murió haciendo exactamente esto

**Confianza: ALTA** (varias fuentes independientes coinciden).

| | |
|---|---|
| Prometía | "Primer AI Admaker del mundo" / "AI CMO" — planear, crear y desplegar miles de anuncios autónomamente |
| Financiación | US$9.2M seed; Founders Fund (Thiel) + ángeles de OpenAI, Ramp, Flexport, Cognition |
| Notable | Pagó **US$12M por el dominio icon.com** (2025) |
| Desenlace | **Muerto.** Feb-mar 2026: equipo desaparecido de LinkedIn, sitio tras un muro de auth, reportado en bancarrota |
| **El detalle clave** | Sus últimas páginas vivas vendían **"38 anuncios UGC humanos (100% reales / no IA)" a US$399** |

El intento mejor financiado de "creador autónomo de anuncios con IA" terminó
**vendiendo anuncios hechos por humanos, publicitados explícitamente como NO-IA.**

Fuentes: techstartups.com/2026/03/05/icon-the-ai-ad-startup-shuts-down... ;
ctol.digital/news/icon-com-12m-domain-human-ads-ai-startup-collapse-investors-2026/ ;
dnjournal.com/archive/lowdown/2026/posts/0306.htm ; crunchbase.com/organization/icon-ai

**NO VERIFICADO:** la razón *interna* del fracaso. No se halló post-mortem de los
fundadores. "No lograron que la IA funcionara" es inferencia periodística.

---

## 3. El competidor vivo más cercano — Superscale

- superscale.ai — fundada 2024, **US$5M seed de Creandum**.
- Pipeline: pegar URL del producto → analiza anuncios de competidores → escribe copy
  → genera video UGC + estáticos con IA → **publica directo en Meta, TikTok y Google Ads**.
- Precio: **US$49 / 99 / 199 / 399 al mes**.
- **Eso es la mayor parte del pipeline de Frío, ya funcionando, a US$99/mes.**
- **Autonomía: SIN RESOLVER.** No se halló evidencia de que escale presupuestos
  autónomamente, mate perdedores por P&L medido, ni emita veredicto a nivel producto.
  Se lee como agente de *producción y lanzamiento creativo*, no de asignación de capital.
- ⚠️ Casi todo el detalle viene del marketing propio de Superscale. **Vendor-reported.**

## Otros verificados

| Empresa | Qué hace | ¿Autónomo? | Estado |
|---|---|---|---|
| Albert.ai | Compra de medios cross-channel | Autónomo (vendor-reported), enterprise | **Adquirida por Zoomd (mar-2022)** |
| Aampe | Agentes de mensajería por usuario | Autónomo — pero es **CRM, no anuncios** | **Adquirida por MoEngage**; levantó US$18M |
| BLKBOX.ai | Testing/producción creativa | **Operado por humanos** | Viva, ~80 empleados, sin financiación |
| Omnicom | Agentes IA ejecutando compras programáticas | Genuinamente autónomo | Viva — **enterprise programmatic, no SMB** |

**Patrón:** todo actor genuinamente autónomo es (a) enterprise programmatic,
(b) otra categoría, (c) ya absorbido por un comprador, o (d) muerto. **Nadie
verificado hace test-and-scale autónomo a nivel producto para PyMEs.**

---

## 4. Barreras de política de plataforma (TODAS requieren re-verificación)

- **Google Ads API — Required Minimum Functionality (RMF):** *"End users must be able
  to review and edit the bid adjustments before it is set by the Google Ads API
  Client."* **PERO:** las herramientas **"Internal Use Only" están EXENTAS de RMF** —
  y Frío, siendo solo para IntoSpirit, no queda atado por la restricción más estricta
  hallada. Matiz honesto: RMF exige que la herramienta *ofrezca* revisión, lo que no
  es idéntico a *prohibir* que un usuario opte por automatizar. **No afirmar que
  "Google prohíbe la puja autónoma" — no está probado.**
- **TikTok Marketing API:** descrita como "la más restringida de las grandes APIs de
  paid social" — onboarding en Business Center → sandbox → revisión de app en
  producción → verificación de negocio → **auditoría de cumplimiento de seguridad de
  datos**; **varias semanas**.
- **Meta:** "Ads Management Standard Access" renombrado **"Marketing API Access Tier"
  el 4-may-2026**; dividido en Limited Access y Full Access (requiere App Review +
  Business Verification).

**Veredicto por plataforma: PERMITIDO CON CONTROLES PESADOS, no prohibido.** No se
halló ninguna cláusula que prohíba tajantemente el gasto autónomo por un agente
tercero. La barrera no es "ilegal" — es *restringida, auditada, revocable, y cada vez
más innecesaria porque la plataforma lo hace nativamente*.

---

## 5. Tasa de fracaso de startups de agentes IA

- **Razonablemente creíble:** Gartner predice que **>40% de los proyectos de IA
  agéntica se cancelarán para 2027**. **NO VERIFICADO contra el comunicado original.**
- **BAJA CALIDAD — NO CITAR:** "70-95% de los agentes IA fallan en producción"
  (Fiddler AI — vendor con interés comercial en que el número asuste); "analicé 847
  despliegues, 76% fallaron" (post de Medium sin fuente); "40% de startups de IA
  fallaron en <24 meses" (contenido SEO sin metodología). Se citan mutuamente.

**Qué tienen en común los sobrevivientes — INFERENCIA, no hallazgo con fuente:**
los vivos venden **autonomía sobre lo creativo** (barato equivocarse) o operan
**dentro de un contrato enterprise** (hay un humano responsable). El único muerto
—Icon— fue el único que vendió **autonomía sobre el dinero** a PyMEs. Hipótesis
consistente con 5-6 datos, no un patrón probado.

---

## 6. Conclusión estratégica (para firma del dueño)

1. **No existe verificablemente un agente autónomo de ciclo completo como producto
   comercial hoy.** Lo más cercano vivo (Superscale) es autónomo sobre *creativo +
   publicación* a US$49-399/mes.
2. **"Nadie lo construyó" NO es principalmente señal de oportunidad aquí.** Hay una
   razón documentada: **las plataformas se quedaron con el loop.**
3. **Pero el fracaso es específico y NO es fatal para Frío.** Icon murió vendiendo
   *creativo autónomo* a PyMEs — y creativo es justo la capa ya comoditizada
   (US$99/mes). Mientras tanto, el reporte de la propia TikTok está documentado como
   **inflado a su favor**. La capa defendible es la que Frío ya tiene y los
   competidores verificablemente no: **medición independiente y determinista de P&L
   real, con veredicto a nivel producto (cancelar/vigilar/continuar/escalar/cosechar).**
   No "quién compra los anuncios" — **"de quién te fías para saber si esto da dinero".**
4. **Foso:** por costo, ninguno observado. El único durable visible es **la medición
   independiente confiable + el rastro de auditoría**, precisamente porque la
   plataforma es hoy a la vez el optimizador y el árbitro.

### Cambio de postura recomendado (pendiente de aprobación del dueño)
- **Re-ponderar la Fase 6** lejos de la optimización de puja/ubicación en TikTok Shop
  (esa superficie ya no existe) y hacia los controles que SÍ quedan y son compatibles
  con GMV Max: **presupuesto, selección de producto, rotación de creativos, targets de ROI**.
- **Duplicar la apuesta en el veredicto independiente de P&L como producto estrella.**
- **Quedarse single-tenant (solo IntoSpirit) más tiempo** del que asume el roadmap SaaS:
  la restricción de política más estricta hallada (RMF de Google) **exime explícitamente
  a las herramientas de uso interno**.

---

## COULD NOT VERIFY / GAPS

- **Ninguna política primaria fue leída.** GMV Max, RMF de Google y los tiers de Meta
  **necesitan re-verificación en la fuente** antes de guiar una decisión.
- Si Superscale escala/mata presupuestos autónomamente — **el desconocido más
  relevante** sobre el competidor más cercano.
- Mecanismo real del fracaso de Icon (sin post-mortem de fundadores).
- Haus, Intelligems, Mutiny, Pencil, AdCreative — no alcanzados.
- Indie hackers / Reddit / YouTube — **cobertura cero** (dominios bloqueados).
- Reglas de divulgación de contenido IA (TikTok synthetic media, Meta, CAC china) —
  relevantes para nuestra fase de AI-UGC, **sin examinar**.
- Acciones de enforcement por gasto publicitario automatizado — no se hallaron, pero
  **la ausencia de evidencia es débil** porque los foros que la tendrían estaban bloqueados.

---

## 7. Barrido de builders independientes y open source (2 barridos independientes)

**GitHub sí era accesible**, así que esta sección tiene evidencia real (READMEs leídos
textualmente, fechas de commits verificadas), a diferencia del resto.

### Hallazgo titular
**Cero casos verificados —open source o indie— de un agente IA corriendo el loop
completo con gasto publicitario real.** Ni uno.

### ★ La validación más fuerte de nuestra arquitectura
**Todos los builders serios llegaron independientemente al MISMO invariante que
nosotros:** campañas creadas en `PAUSED`, y confirmación humana explícita en cada
escritura. Sin contacto entre ellos.

| Repo | ★ | Compuerta (verbatim del README) |
|---|---|---|
| AgriciDaniel/claude-ads | **7,572** | Read-only por defecto; escrituras requieren IDs + diff antes/después + aprobación + rollback |
| pipeboard-co/meta-ads-mcp | 1,108 | *"explicit confirmation on every write"*; campañas nuevas **arrancan pausadas** |
| TheMattBerman/meta-ads-kit | 281 | *"always with your approval"*; emite payloads dry-run |
| attainmentlabs/meta-ads-cli | 30 | *"Campaigns are created as PAUSED by default"* + tope `MAX_DAILY_BUDGET` |
| brandu-mos/konquest-meta-ads-mcp | 40 | *"Supervised, not autonomous — operator confirms every write"* |
| markifact/markifact-mcp | 51 | *"Nothing goes live without you saying yes."* |

**Tres de estos VENDEN la compuerta humana como característica diferenciadora**, no
como limitación. Nuestro invariante de seguridad no es conservadurismo — es el consenso.

### El único que promete autonomía total
`mikee-ai/meta-ads-agent`: *"without you lifting a finger"*, **2 commits, creado y
actualizado el mismo día**, 0 estrellas, licencia propietaria que prohíbe ingeniería
inversa, sin código ni arquitectura. **Vende a US$497–2,997/mes o US$14,997 vitalicio.**
El patrón vale decirlo claro: *el único proyecto que promete autonomía total es el de
2 commits vendiendo licencias de US$2,997/mes.*

### Los mejores intentos reales, y dónde se detienen
- **`YunyueLi/Drip`** — scoring determinista de 8 señales → SCALE/PAUSE/HOLD/REDUCE/REFRESH,
  *"the LLM only narrates"* (idéntico a nuestro principio). Modos shadow→copilot→autonomous.
  **Su propio README:** *"the first verified live write on a real ad account is still on
  the roadmap."* El agente open-source más avanzado **se detuvo exactamente en la
  frontera de la escritura en vivo.**
- **`brac/presswork`** — el mejor pipeline POD real (Etsy trends → FLUX → listing → ledger
  con márgenes). `HUMAN_REVIEW_ENABLED` **por defecto true**. **Sin publicidad pagada
  en absoluto** — depende solo de descubrimiento orgánico de Etsy.
- **`rushikeshdhumal/ecommerce-growth-agent`** — el caso aleccionador: tiene un loop
  plan→act→observe sobre Google/Meta/Klaviyo, **pero TODAS las integraciones son MOCK.**
  Parece el loop completo; no toca nada real.
- `IncomeStreamSurfer/print_on_demand_printify_automation` (126★) — **trampa**: muerto
  desde jul-2023, era era SD v1.5, 4 scripts sueltos. Las estrellas son artefactos de
  audiencia de YouTube.

### El terreno desocupado es la UNIÓN, no la autonomía
`presswork` hace POD descubrimiento→creativo→publicar **sin anuncios**. `Drip` hace
kill/scale determinista **sin productos y sin haber escrito nunca en vivo**. **Nadie ha
conectado descubrimiento → creativo → gasto con compuerta → P&L real por producto.**
Y nadie ha publicado pre-score predictivo + detección de fatiga/meseta + veredicto a
nivel producto juntos.

### 🚨 RIESGO OPERATIVO NUEVO — baneos por patrón de llamadas
Reportes (X/@theericcarlson, corroborado en forma por un blog de Supermetrics — **ambos
SIN VERIFICAR**, dominios bloqueados) indican que conectar un **MCP de Meta Ads** a una
cuenta de Facebook **provocó baneos**, incluso confirmado por un account manager. La
hipótesis: agentes golpeando APIs a frecuencia de máquina acumulan señales de anomalía.

**Lo crítico:** si esto es direccionalmente cierto, el peligro es la **forma del patrón
de llamadas**, NO la lógica de compuertas. **Nuestros topes de gasto y HITL NO protegen
contra esto.** Regla operativa a adoptar: los conectores de ads en vivo deben ir por una
**app registrada + API key oficial**, nunca por un shim MCP o scraping. Requiere
verificación independiente antes de encender cualquier conector de anuncios en vivo.

### Sobre forkear código: no hay nada que forkear
- **No existe cliente Python de TikTok Shop** en ningún lado (ni PyPI, ni repo con tests).
- Las implementaciones Python que existen están dentro de apps **sin licencia**
  (= todos los derechos reservados, inusables).
- **Nada de guardarraíles de gasto / HITL existe como librería.** La lista curada del
  dominio (`awesome-agentic-advertising`) **no tiene ni una entrada** sobre topes de
  presupuesto o revisión humana para plataformas de anuncios.

**Conclusión de ingeniería:** la mitad valiosa y riesgosa de Frío — reglas deterministas
de kill/scale, ledger append-only con topes duros, asimetría kills-auto/scales-gated,
fatiga/meseta, pre-score, y veredicto de P&L por producto — **no tiene equivalente
open source en ninguna parte.** Dos barridos independientes no hallaron ninguno. Ese
trabajo está correctamente construido en casa, y **es el foso.**
