# Cómo medir de verdad los ads de TikTok Shop (y por qué el diseño anterior estaba mal)

**Origen: el dueño del proyecto rechazó la lógica anterior el 2026-09-17, y tenía razón.**
Research hecho a petición suya. **No exhaustivo:** el portal de documentación de la
Marketing API (`business-api.tiktok.com/portal/docs`) responde HTTP 200 pero sirve una
aplicación JavaScript que no se puede leer como texto, así que la lista completa de
campos de la API de reportes no se leyó de primera mano. Lo que sí se leyó textualmente
es el centro de ayuda de TikTok Ads y el SDK oficial en GitHub (fuentes al final).

## 1. El error de diseño (corregido)

El código vetaba el veredicto SCALE de un **producto** cuando los ingresos incluían
ventas orgánicas. Está mal, y el argumento del dueño es el correcto:

> Si hay ventas orgánicas, eso es **una muestra de que el mercado quiere el producto**.
> Los ads llegan a más personas, así que **escalan lo que el orgánico ya probó**.

Penalizar a un producto por venderse solo invierte el incentivo. Peor: las ventas
orgánicas son la evidencia **más limpia** que existe, porque nadie pagó para ponerlas
frente a nadie.

Lo que sí es cierto es una pregunta **más estrecha**: *¿son eficientes los anuncios?*
Esa es una decisión de **presupuesto publicitario**, no de producto. Ahora vive aparte
en `frio/ad_efficiency.py` y **se reporta al lado** del veredicto, nunca como candado.

## 2. Por qué los datos de Ads no pueden responder la pregunta estrecha

Palabras textuales de TikTok (leídas 2026-09-16/17):

- **Gross revenue (GMV Max):** *"The total gross revenue of TikTok Shop orders, both paid
  and organic, attributed to your campaign."*
- **ROI:** *"Note: ROI includes both organic and paid orders."*
- Y lo más contundente, de la página de atribución de GMV Max:
  *"If a customer purchases Product A while the GMV Max campaign is active, but doesn't
  view or click on any ads, the purchase will be attributed to GMV Max."*

O sea: durante una campaña GMV Max, **prácticamente toda venta del producto se le
acredita a la campaña**. Eso no es atribución, es un total de ventana de campaña.

**Matiz importante que no teníamos:** los **TikTok Shop Ads normales** (no GMV Max) SÍ
tienen atribución real, con ventanas declaradas: **7 días post-clic y 1 día post-vista**,
y el clic tiene prioridad sobre la vista. Así que el tipo de campaña decide si hay
atribución o no. GMV Max compra automatización a cambio de perder la medición limpia.

## 3. Las dos soluciones reales (ambas implementadas)

### Solución 1 — atribución pagada real (la buena) · requiere Shop
TikTok Seller Center, en **Data Compass**, reporta separadamente:

- **"Ads Gross Revenue:"** *"Sales attributed to ads"*
- **"Non-Ads Gross Revenue:"** *"Sales not attributed to Ads"*

Con desglose adicional de afiliado vs. no-afiliado, en
`Seller Center → Analytics → Growth & Insights → Sales Performance → Gross Revenue → Breakdown`.
Ventana de atribución 7 días clic / 1 día vista. **Esto es del lado Shop, no de Ads** —
es la razón técnica más fuerte para conectar TikTok Shop.

Ojo con una diferencia documentada por TikTok: Seller Center reporta las ventas **del día**,
mientras Ads Manager usa la ventana de 7 días. Los dos números **no van a coincidir**, y
eso es esperado, no un error.

### Solución 2 — lift incremental (sirve sin Shop) · implementada
Con una línea base de ventas orgánicas de **antes** de la campaña:
`lift = ingresos ahora − línea base`. Eso es lo que añadieron los anuncios. Es la misma
idea que TikTok invoca cuando describe GMV Max como optimización de *"incremental GMV"*.
No necesita el desglose pagado/orgánico, solo historial — que ya guardamos en
`metrics_daily`.

**Limitación declarada en el propio código:** es una estimación, no atribución. Una
tendencia de demanda o una estacionalidad también mueven el lift.

### Si no hay ninguna de las dos → `unknown`
No hay tercer nivel optimista. `assess_ad_efficiency` devuelve `unknown` explícito, y el
texto aclara que **eso no cuenta contra el producto**.

## 4. Consecuencia operativa

| Pregunta | Datos que necesita | Estado |
|---|---|---|
| ¿El producto se vende? | Ingresos totales (orgánico incluido) + costos reales | ✅ Funciona hoy |
| ¿El anuncio es eficiente? | `Ads Gross Revenue` (Shop) **o** línea base previa | ✅ Implementado, requiere uno de los dos |
| ¿Subo el presupuesto? | Lo anterior + aprobación humana | Humano decide, con ambas lecturas a la vista |

## 5. Corrección adicional encontrada de paso: la comisión estaba mal

El código usaba **8%** de comisión de plataforma. **Ninguna fuente lo respalda.**
La documentación propia de TikTok (seller-us.tiktok.com university) dice **6% por orden
calificada desde 2024-04-01** en la mayoría de categorías; 5% en ciertas subcategorías de
joyería; y promoción de nuevo vendedor del 3% por 30 días. Corregido a 6%.

**Costos reales adicionales documentados por TikTok que NO estaban en el modelo:**
- **Impuesto sobre la comisión**, vigente desde 2025-11-01.
- **Refund Administration Fee**: 20% de la comisión, con tope de $5 por SKU.

Ambos dependen del estado y de la tasa de devoluciones, así que **no se inventó un
número**: `fin_referral_fee_tax_pct` queda en 0 y visible, para llenarlo desde un estado
de cuenta real. Un 0 visible es honesto; un número inventado no.

## Fuentes (leídas textualmente salvo donde se indica)

- TikTok Ads Help — "How to view reporting for your Product GMV Max campaign":
  https://ads.tiktok.com/help/article/how-to-see-reporting-for-your-product-gmv-max-campaign
- TikTok Ads Help — "About attribution for GMV Max":
  https://ads.tiktok.com/help/article/about-attribution-for-gmv-max?lang=en
- TikTok Ads Help — "About attribution for TikTok Shop Ads" (ventanas 7d clic / 1d vista):
  https://ads.tiktok.com/help/article/about-tiktok-shop-ads-attribution?lang=en
- TikTok Ads Help — "About Ads Metrics in Seller Center" (Ads vs Non-Ads Gross Revenue):
  https://ads.tiktok.com/help/article/about-ads-metrics-in-seller-center
- TikTok Ads Help — "About gross revenue for TikTok Shop Ads":
  https://ads.tiktok.com/help/article/about-gross-revenue-for-tiktok-shop-ads?lang=en
- TikTok Shop Seller University (comisiones; vía resultados de búsqueda sobre
  seller-us.tiktok.com, no abierto directamente — **evidencia de segundo nivel**):
  https://seller-us.tiktok.com/university/essay?knowledge_id=6837873164977921
- SDK oficial de TikTok, `StoreApi` (leído en GitHub): expone
  `GET /open_api/v1.3/gmv_max/store/list/` y `.../store/shop_ad_usage_check/` — es decir,
  **Ads sí ve que tu Shop está vinculado**, pero **no hay endpoint para listar los
  productos de tu Shop** desde el lado Ads:
  https://github.com/tiktok/tiktok-business-api-sdk/blob/main/python_sdk/docs/StoreApi.md
