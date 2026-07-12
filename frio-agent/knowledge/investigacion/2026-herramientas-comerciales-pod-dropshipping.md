# Herramientas comerciales para research/testing de POD y Dropshipping

**Fecha:** 2026-07-12. **Estado:** research puntual sobre 5 herramientas específicas
que el usuario compartió — **NO es un barrido exhaustivo del mercado**. Cada
afirmación de esta sección fue contrastada con una búsqueda independiente antes de
escribirse; donde el texto original del usuario y mi búsqueda no coincidieron, se
documenta la discrepancia explícitamente (regla de `knowledge/README.md`).

## 1. Las 5 herramientas — verificadas, qué hacen, qué no coincide

### Sell The Trend (Nexus AI)
- **Existe, verificado.** Web research independiente confirma: motor "Nexus AI"
  escanea **11 millones de productos** (26 puntos de datos) cruzando AliExpress,
  Amazon, actividad de tiendas Shopify y señales sociales. Tiene "TikTok Ads
  Explorer" (ad-spy), un "dropshipping detector" (qué tiendas venden el mismo
  producto) y un creador de video-ads integrado. ~40,000 comerciantes usuarios.
  Precio: Essential ~$39.97/mes, Pro ~$99.97/mes.
- **Discrepancia:** el texto del usuario decía "millones de productos" en
  Shopify/AliExpress/redes — es consistente en dirección, pero la cifra concreta
  (11M productos / 40K comerciantes) no estaba en el texto original; la confirmo
  yo, no la traía el usuario.
- **Cita importante (auto-crítica de la propia herramienta, hallada en reviews):**
  *"No garantiza product-market-fit, desempeño creativo ni fiabilidad del
  proveedor... las sugerencias de IA aún necesitan validación manual — momentum no
  siempre es igual a rentabilidad."* → Es una herramienta de **apoyo a la
  decisión humana**, no un agente que decide y ejecuta.
- Fuentes: sellthetrend.com; dodropshipping.com/sell-the-trend-review-product-research-tool;
  minea.com/best-website-for-dropshipping/product-research-tools/sell-the-trend-review

### Tradelle
- **Existe, verificado.** Mi búsqueda independiente encontró: **20 millones de
  productos** en **1.2 millones de tiendas Shopify** + 100,000+ fuentes online.
  Dashboard de tendencias, análisis de estacionalidad y saturación, importación a
  Shopify en 1 clic, fulfillment automatizado, cobro solo tras la venta.
- **⚠️ DISCREPANCIA SIN RESOLVER:** el texto del usuario decía **"200 millones de
  productos de 10 millones de tiendas"** — **10 veces más** que lo que yo
  encontré (20M/1.2M). No puedo confirmar cuál cifra es correcta; ambas son
  auto-reportadas por el propio vendedor en algún momento, ninguna verificada por
  un tercero independiente. **No elijo una — dejo la discrepancia documentada.**
  Posible explicación (no confirmada): distintas versiones de su página de
  marketing en momentos distintos, o la cifra del usuario viene de otra fuente
  que no ubiqué.
- Fuentes: tradelle.io; serchen.com/blog/tradelle-io-review-a-powerful-all-in-one-platform-for-dropshipping-in-2025;
  tradelle.io/blog/the-11-best-dropshipping-product-research-tools

### SP Product Researcher (Service Points)
- **Existe, verificado — y esta sí coincide con precisión.** El texto del
  usuario decía "monitorea más de 100,000 tiendas activas de dropshipping
  diariamente" — mi búsqueda independiente encontró **exactamente** esa cifra:
  *"monitors over 100,000 active dropshipping stores daily using AI
  algorithms."* Enfoque "producto-primero": agrupa todas las tiendas/anuncios
  que venden el MISMO producto, en vez de rastrear tienda por tienda. Gratis (va
  incluido si conectas tu tienda a Service Points).
- Fuentes: servicepoints.eu/en/other-tools/sp-product-researcher;
  servicepoints.nl/en/blog/5-best-ai-product-research-tools-dropshipping-2026

### AdTest.AI
- **Existe, verificado.** Es más sofisticado de lo que sugería el texto del
  usuario: no es solo un modelo predictivo — combina **puntuación por IA (13
  dimensiones, usando modelos de Anthropic/Google/AWS/TwelveLabs) CON validación
  real de audiencia (paneles humanos de primera parte)**. Su "Mixed Score" cruza
  lo que la IA predice contra lo que la audiencia real reporta. Se posiciona
  explícitamente contra la investigación de mercado tradicional (lenta, cara,
  de seis cifras al año).
- Confirma el concepto que el usuario describió (puntuación antes de gastar en
  medios), con el matiz de que no es solo IA — también usa humanos reales.
- Fuente: adtest.ai; koji.so/blog/best-ad-testing-software-2026

### Creatify AI
- **Existe, verificado, coincide bien con el texto del usuario.** Confirma: URL
  del producto → extrae imágenes/descripción → genera guion + video UGC con
  avatares + voces multilenguaje (75+ idiomas). Precio real: desde ~$33–39/mes
  (Starter), Pro ~$59/mes — el texto del usuario no daba precio.
- **Matiz que el texto del usuario omitía (encontrado en reviews independientes):**
  quejas recurrentes de "lip-sync" desincronizado, sistema de créditos confuso, y
  **Trustpilot 2.1/5 estrellas** (vs G2 4.8/5) — fuentes de reseñas distintas dan
  puntuaciones muy distintas. Ya estaba en nuestro catálogo previo (ver plan
  maestro) como alternativa a Higgsfield/Arcads — esto no es un hallazgo nuevo,
  solo lo corrobora con más detalle.
- Fuentes: creatify.ai/use-cases/ugc; ezugc.ai/review/creatify-ai;
  cleverfashionmedia.com/creatify-review-2026-is-this-ai-ad-generator-worth-39-month

## 2. El patrón que comparten las 3 de "research/analítica"

Sell The Trend, Tradelle y SP Product Researcher tienen el MISMO mecanismo de
fondo: agregan datos de **miles de tiendas que venden el MISMO producto/SKU**
(típicamente sourced de AliExpress) para saber si ya está saturado y quién más lo
vende. Ese mecanismo **requiere que el producto sea un SKU compartido por muchas
tiendas** — es decir, es estructuralmente un patrón de **dropshipping**, no de
POD. En POD tu diseño es único tuyo; no hay "10,000 tiendas vendiendo mi mismo
diseño" que agregar de esa forma.

## 3. Respuesta a la pregunta del usuario: ¿aplican a lo nuestro? ¿dropship o también POD?

| Herramienta | Mecanismo | Dónde aplica en Frío |
|---|---|---|
| Sell The Trend, Tradelle, SP Product Researcher (la parte de **descubrir/validar producto**) | Agregación cross-tienda de un SKU compartido | **Dropshipping — Phase 2A (aún no construida)**, como fuente de datos alternativa/adicional a Kalodata/AutoDS/FastMoss ya contemplados. NO aplica igual a POD (no hay SKU compartido). |
| Sell The Trend (TikTok Ads Explorer) / Tradelle (visibilidad de tiendas competidoras) — la parte de **ad-spy** | Inteligencia de anuncios de competidores | Se solapa con nuestro **Pillar 1 compartido** (ad research: Creative Center + Meta Ad Library + Apify) — esto SÍ aplica a ambos pipelines, POD incluido. |
| Creatify AI | Generación de video UGC desde URL de producto | **Motor compartido — Phase 3 creation.** Ya estaba contemplado como alternativa a Higgsfield/Arcads en el plan maestro; no es exclusivo de ningún pipeline. |
| AdTest.AI | Puntuación predictiva + panel real ANTES de gastar en medios | **Gap real y genuino, compartido por ambos pipelines** — ver sección 4. |

**Conclusión directa a tu pregunta:** no es "todo para dropshipping" ni "todo para
ambos" — se reparte. Las 3 de descubrimiento de producto son mayormente
dropshipping; la parte de ad-spy y Creatify son del motor compartido; AdTest.AI
señala una pieza que nos falta a los dos.

## 4. ¿Dónde estamos fallando / por qué dije que no existe algo como lo nuestro?

**Reviso mi afirmación anterior con evidencia, no de memoria:**

- Las 5 herramientas verificadas aquí son **software que un humano opera y
  decide** — ninguna ejecuta el ciclo completo sola. La propia Sell The Trend lo
  dice explícitamente en sus reviews: *"las sugerencias de IA aún necesitan
  validación manual."* AdTest.AI da un score; el humano decide. Ninguna calcula
  un **P&L real con veredicto de negocio** (cancelar/vigilar/continuar/escalar/
  cosechar) ni **ejecuta** publicar/lanzar/matar campañas bajo topes de gasto.
  Eso sigue siendo lo que no encontré en ninguna de las 5.
- **Pero debo ser honesto sobre el alcance:** esto verificó solo las 5 que
  compartiste. **No hice un barrido exhaustivo de "¿existe ya un AGENTE
  autónomo (no dashboard) que corra todo el ciclo POD/dropship con veredicto
  financiero?"** — esa es una pregunta de investigación distinta y más
  específica que no he corrido todavía. Si la quieres, la hago aparte.

**Fallas reales nuestras, identificadas por comparación honesta:**
1. **Sin dato real de mercado todavía** — nuestro descubrimiento de competidores
   y origen de producto corren sobre *fixtures* (ejemplos), mientras estas 3
   herramientas tienen datos en vivo, actualizados, con años de recolección
   (40,000 comerciantes en Sell The Trend, por ejemplo). Esto no es una falla de
   diseño — es la brecha esperable de un sistema recién construido vs. productos
   maduros con miles de usuarios y datos históricos.
2. **Sin puntuación predictiva pre-lanzamiento** — hoy pasamos de "armar el
   brief" directo a gastar dinero real (aunque sea poco) para obtener señal.
   AdTest.AI mete un filtro ANTES de gastar. Es una capa que no tenemos.
3. **Sin la amplitud de datos de ad-spy** que tienen estas herramientas
   comerciales (TikTok Ads Explorer de Sell The Trend, por ejemplo) — nuestra
   capa de ad research depende hoy de Creative Center/Meta Ad Library/Apify,
   más limitada en cobertura que un producto dedicado con años de scraping.

## 5. Recomendación (no ejecutada todavía — pendiente de tu decisión)

- **Para Dropshipping (Phase 2A, sin construir):** cuando se construya, evaluar
  Sell The Trend / Tradelle / SP Product Researcher como **fuente de datos a
  la que nos conectamos** (glue, no reconstruir su infraestructura de scraping)
  — coherente con nuestro principio ya establecido de usar herramientas
  existentes en vez de reinventarlas.
- **Creatify AI:** ya contemplada como alternativa de proveedor en
  `connectors/video_gen.py` junto a Higgsfield/Arcads/Prizmad — no requiere
  cambio de arquitectura, solo decidir si se agrega como opción concreta.
- **AdTest.AI / puntuación predictiva:** esto sí es una decisión de arquitectura
  real pendiente — ¿agregamos una fase "3.5: pre-score predictivo" antes del
  test pagado? No lo construí — es tu decisión, y quería primero traerte el
  research antes de tocar código.
