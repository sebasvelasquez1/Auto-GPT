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
