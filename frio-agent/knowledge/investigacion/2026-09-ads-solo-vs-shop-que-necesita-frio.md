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

**Corregido en código (no solo anotado):** `assess_viability(..., revenue_includes_organic=True)`
**veta el veredicto SCALE** y lo baja a CONTINUE, explicando el motivo y el remedio.
Asimetría deliberada, coherente con la regla del proyecto: CANCEL **no** se veta, porque
con ingresos inflados una pérdida se ve *mejor* de lo que es, así que cancelar con esos
datos es conservador, no arriesgado. Ver `tests/test_organic_contamination.py`.

**Separar pagado de orgánico requiere datos de órdenes del lado Shop.** Ese es el
argumento técnico más fuerte para conectar Shop, más allá del catálogo y la publicación.

## Recomendación

1. **Ahora:** conectar solo Ads. Sirve para investigar, crear, probar, medir y **matar
   perdedores** (que es la mitad que ahorra dinero). Los costos se entran a mano.
2. **Antes de escalar con dinero de verdad:** conectar Shop. Sin eso, el código
   deliberadamente no permitirá un SCALE limpio.

## Fuentes

- TikTok Ads Help Center — "How to view reporting for your Product GMV Max campaign":
  https://ads.tiktok.com/help/article/how-to-see-reporting-for-your-product-gmv-max-campaign
  (leída textualmente, 2026-09-16)
- Portal de docs de la Marketing API: HTTP 200 pero no legible como texto (SPA) —
  limitación registrada, no se afirma nada sobre campos exactos de la API.
