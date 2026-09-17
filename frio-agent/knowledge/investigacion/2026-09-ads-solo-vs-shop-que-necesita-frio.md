# ¿Frío puede operar solo con TikTok Ads, o necesita también TikTok Shop?

**Pregunta del usuario, 2026-09-16.** Respondida contra el código real del repo (qué
importa cada módulo) y contra documentación oficial de TikTok leída en esta sesión.
**Research no exhaustivo:** el portal de docs de la Marketing API
(`business-api.tiktok.com/portal/docs`) responde HTTP 200 pero sirve una app JavaScript
que no se puede leer como texto, así que la lista completa de campos de la API de
reportes **no** se leyó de primera mano. La fuente que sí se leyó textualmente es el
centro de ayuda de TikTok Ads (ver abajo).

## Respuesta corta

**Sí, el ciclo central funciona solo con Ads.** Pero el veredicto financiero
("¿sirve o no sirve?") queda **degradado**, y tres cosas son imposibles sin Shop.

## Qué necesita cada pieza (leído del código, no supuesto)

| Pieza | ¿Necesita Shop? | Evidencia en el código |
|---|---|---|
| Competencia + research de anuncios + estratega | No | Fuentes externas / fixtures |
| Creación de AI-UGC (Higgsfield) | No | `modules/creation.py` |
| Pre-score predictivo | No | `modules/prescore.py` |
| Motor de optimización (matar/escalar por anuncio) | No — pero ver contaminación | `metrics.py` consume métricas de anuncios |
| Lanzar / pausar / cambiar presupuesto | No | `connectors/tiktok_ads.py` |
| **Leer los diseños existentes del vendedor** | **Sí** | `modules/product_pod.py` importa `TikTokShopCatalog` |
| **Publicar listings** | **Sí** | `modules/commerce.py`, tras `seller_approved` |
| **Costos reales (precio, costo, envío, devoluciones)** | Parcial | `financials.CostStructure` — hoy son entradas manuales/config, la API de Ads no los tiene |

Nota sobre nuestra propia configuración: la capacidad `ads.launch_campaign` está hoy
condicionada a `ads_live_enabled AND seller_approved` (`modules/ads.py`). `seller_approved`
es **nuestra** bandera de seguridad, no un requisito de TikTok — no obliga a tener la
conexión de Shop, pero sí obliga a una decisión humana explícita.

## 🔴 Hallazgo crítico — los ingresos que reporta Ads NO son atribuibles limpiamente

Fuente leída textualmente (centro de ayuda oficial de TikTok Ads, artículo
"How to view reporting for your Product GMV Max campaign", leído 2026-09-16):

- **Gross revenue:** *"The total gross revenue of TikTok Shop orders, both paid and
  organic, attributed to your campaign."*
- **ROI:** *"The total return on investment (ROI) from all TikTok Shop orders attributed
  to your campaign. This is calculated by dividing the Gross revenue by the Cost."*
- **Advertencia propia de TikTok:** *"Note: ROI includes both organic and paid orders.
  High ad spending can make this metric seem low, even if your campaign is performing
  well. To judge product performance, use Gross revenue instead."*

Métricas que sí ofrece ese reporte: `Cost`, `Orders` (órdenes SKU), `Cost per order`,
`Gross revenue`, `ROI`.

**Por qué importa:** nuestro analizador calcula POAS = ingresos / gasto publicitario. Si
los ingresos incluyen ventas orgánicas que los anuncios **no** causaron, el POAS sale
**inflado** → un producto puede parecer "escalable" cuando el anuncio aporta poco. Ese es
justo el error que gasta dinero de verdad.

> ### ⛔ CORRECCIÓN (2026-09-17) — lo que decía este párrafo estaba MAL
>
> Este documento afirmaba que la solución era **vetar el veredicto SCALE del producto**
> cuando los ingresos incluían ventas orgánicas. **El dueño del proyecto lo rechazó y
> tenía razón.** Vetar el producto confunde dos preguntas: las ventas orgánicas son
> *evidencia de que el mercado quiere el producto*, y los ads escalan lo que el orgánico
> probó. Penalizar al producto por venderse solo invierte el incentivo.
>
> El veto se **eliminó**. La pregunta estrecha y legítima —*¿son eficientes los ads?*—
> ahora vive aparte en `frio/ad_efficiency.py` y se reporta **al lado** del veredicto,
> nunca como candado. Además apareció un matiz que aquí faltaba: los Shop Ads normales
> (no GMV Max) **sí** tienen atribución real (7 días clic / 1 día vista).
>
> Análisis completo y soluciones: `2026-09-medir-ads-tiktok-shop.md`.

**Separar pagado de orgánico requiere datos de órdenes del lado Shop.** Ese es el
argumento técnico más fuerte para conectar Shop, más allá del catálogo y la publicación.

## Recomendación

1. **Ahora:** conectar solo Ads. Sirve para investigar, crear, probar, medir y **matar
   perdedores** (que es la mitad que ahorra dinero). Los costos reales se entran una vez
   con `frio costs set` (ver `product_costs.py`).
2. **Conectar Shop cuando quieras saber si el ANUNCIO funciona**, no para poder escalar.
   El producto se puede escalar con datos de Ads solos; lo que falta sin Shop es separar
   qué ventas causó el anuncio (`Ads Gross Revenue` en Seller Center).
   *(Corregido 2026-09-17: antes este punto decía que el código bloquearía el escalado
   sin Shop. Ya no lo hace, y no debía hacerlo.)*

**Dato del lado Ads verificado en el SDK oficial:** `GET /open_api/v1.3/gmv_max/store/list/`
existe, así que la API de Ads **sí ve que tu Shop está vinculado**. Pero en `StoreApi` no
hay ningún endpoint que liste **los productos** de tu Shop — leer tu catálogo sigue
necesitando la API de Shop.

## Fuentes

- TikTok Ads Help Center — "How to view reporting for your Product GMV Max campaign":
  https://ads.tiktok.com/help/article/how-to-see-reporting-for-your-product-gmv-max-campaign
  (leída textualmente, 2026-09-16)
- Portal de docs de la Marketing API: HTTP 200 pero no legible como texto (SPA) —
  limitación registrada, no se afirma nada sobre campos exactos de la API.
