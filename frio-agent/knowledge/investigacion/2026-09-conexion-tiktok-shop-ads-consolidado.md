# Cómo conectar un agente a TikTok Shop y TikTok Ads — investigación consolidada

**Fecha:** 2026-09-15. **5 investigaciones paralelas** (TikTok Shop paso a paso, TikTok
Ads paso a paso, realidad de practicantes en foros/Reddit, código real en GitHub, papers
académicos recientes). Contrastado contra los documentos oficiales de TikTok que el
usuario compartió previamente (su contenido quedó preservado en `CLAUDE.md` y en este
repo tras perderse el archivo subido).

## ⚠️ Método — mejoró mucho respecto a research anteriores
Antes, la documentación de TikTok estaba 100% bloqueada y todo venía de resúmenes de
buscador. **Esta vez sí se leyeron páginas oficiales de fuente PRIMARIA** — vía dos
espejos de GitHub que replican la documentación con sus IDs de documento originales
(`lazykern/ecommerce-api-docs`, `henry-md/ad-mcps` — este último dejó de existir a
mitad de la investigación, causando que una rama tuviera que cambiar de espejo).
Donde se cita "primario", significa que se leyó el texto real, no un resumen.

---

## 1. 🎯 LA PREGUNTA MÁS IMPORTANTE: ¿un individuo sin empresa puede conectarse?

### Lado Ads — CONFIRMADO, NO se puede
Texto exacto de la fuente oficial (`doc_id: 1738855176671234`, leído directamente):
> *"You will be rejected if you are using a personal email or a temporary email...
> Currently, we are unable to onboard personal accounts or individual developers."*

El sitio de la empresa debe ser *"publicly accessible... fully developed and
professionally presented"* y coincidir con el dominio del correo. Solo hay 3 tipos de
usuario: Technology Company / Direct Advertiser / Agency — ninguno es "individuo".
**Se necesita: entidad legal + dominio propio + sitio web real + correo en ese dominio.**

### Lado Shop — MÁS AMBIGUO de lo que pensábamos, con dos documentos oficiales que se contradicen
Se encontraron **dos páginas oficiales primarias que no coinciden**, y — siguiendo
nuestra regla — **no se elige la que suena mejor**:

- **El formulario de certificación detallado** (Seller Developer Onboarding Onepager,
  Paso 4) exige explícitamente: *"Certificate of Incorporation copy... **The applicant
  must be of enterprise type**"* + nombre legal de empresa + foto del local con el
  nombre de la entidad legal visible. **Esto es un requisito duro de empresa
  registrada, citado textualmente.**
- **La página general de onboarding** (más alto nivel) describe el mismo paso de forma
  mucho más liviana: *"Select the category Seller inhouse developer... and link the
  activated TikTok Shop account... ensure the seller account information you entered
  is authentic"* — **sin mencionar certificado de empresa para esta ruta** (solo lo
  exige para la ruta de App Developer/ISV en esa misma página).

**No se pudo determinar cuál prevalece** — si el formulario detallado es una versión
más nueva/estricta, si varía por región ("*required qualifications vary from country to
country*", dice el propio documento), o si depende del tipo de cuenta de vendedor ya
abierta.

**Mi recomendación honesta:** el documento más detallado y específico para este paso
exacto (el formulario de certificación) es la señal más fuerte, y **yo no planificaría
asumiendo que un Gmail sin empresa basta**. Pero como cuesta $0 intentarlo, **la forma
más rápida de resolver esto de verdad es empezar el registro en Partner Center** (sin
comprometerse a nada irreversible) y ver qué pide el formulario real, o preguntarle
directamente al soporte de partners.

### 🟢 La puerta que sí es clara: el MCP oficial de TikTok Ads
> *"You do NOT need to register a developer account or create a developer app to
> connect to TikTok for Business MCP Server... publicly available to all users."*

Esto viene de 3 fuentes independientes que coinciden (aunque ninguna se leyó en la
página oficial en bruto — está en un árbol de documentación distinto al que se pudo
espejar). **Es la ruta más prometedora para alguien sin empresa constituida.** Ver §5.

---

## 2. TikTok Shop — pasos exactos (con correcciones a lo que creíamos)

### Ruta completa
1. Cuenta en Partner Center (mismo correo que tu Seller Center — **obligatorio**, no
   hay opción de correo alternativo).
2. **Ya debes tener una tienda TikTok Shop activada** antes de poder registrarte como
   developer (confirmado, es requisito no negociable).
3. Categoría: **"Seller inhouse developer / TikTok Shop Seller"**.
4. Verificar cuenta de vendedor (login/password).
5. Llenar el formulario de certificación (ver §1 — el punto de fricción).
6. Crear la app: **App type = Custom App únicamente** (ver corrección abajo).
7. Probar en un **Development Shop** (ver §4).
8. Autorizar: abrir el link de autorización de tu app, iniciar sesión como vendedor.
9. Intercambiar `code` por tokens.
10. **Publicar** la app (paso separado de solo "crearla").

### ✅ CORREGIDO — Custom App vs Public App
Para un Seller Developer construyendo solo para su propia tienda: **Custom App es la
única opción real**, no "Public App recomendado" como sugería un resumen anterior. La
tabla oficial de tipos de developer solo lista "Custom App" para la categoría "Seller
Developer" — Public App aparece solo para System Integrator / App Developer. La
afirmación de "se recomienda Public" venía de mezclar la guía genérica de ISV con el
flujo específico de vendedor — **error de lectura corregido.**

### ✅ CORREGIDO — "Service Id" NO es una tercera credencial en la página de tu app
Es real, pero es una **constante fija de la región** dentro de la URL de autorización
(`service_id=7369437808455026474` para US), no algo que aparezca junto a tu App Key/App
Secret. No es un credencial tuyo — identifica el endpoint de autorización de TikTok.

### ✅ CORREGIDO — vida del access token: 7 días, no 24 horas
Confirmado en dos documentos oficiales: *"default expiration time set to seven days."*
La cifra de "24 horas" que circulaba corresponde al token de **Ads**, no al de Shop —
eran dos APIs distintas que se estaban confundiendo.

### ✅ CORREGIDO — sandbox SÍ funciona, y en más países de lo que creíamos
La afirmación de "solo UK e Indonesia" **queda refutada**. El documento oficial dice:
*"available for cross-border and local shops in JP, MY, PH, SG, TH, US, UK, and VN, and
for local shops in ID."* Existen dos niveles: **Core Function Account** (KYC mínimo, sin
info de pago) y **Full Function Account** (flujo completo). Y se confirma: **sí se
puede empezar a desarrollar antes de la aprobación completa de la app** — es
justamente para eso que existe.

### shop_cipher — matiz importante que antes no teníamos
No es "requerido siempre" — es **requerido solo para tiendas de China habilitadas para
venta cross-border**, y **opcional para tiendas locales en US/UK/SEA** (que es tu caso).

### ⚠️ Firma de webhooks — hueco real en la propia documentación de TikTok
La página oficial de resumen de webhooks está **vacía en la fuente** (0 bytes,
confirmado en los metadatos del espejo — no es un fallo nuestro de lectura). Construimos
la verificación a partir de **dos fuentes independientes que sí coinciden** (ver §3), no
de un ejemplo oficial de TikTok, porque ese ejemplo no existe en ningún lugar accesible.

---

## 3. Código real en GitHub — dos bugs corregidos en nuestro firmante

Se releyó el código fuente oficial de TikTok (`tiktok/ttspc-server-sample`) y se
confirmó **nuestro algoritmo sigue siendo exacto**, ahora cuádruple-verificado contra 4
implementaciones independientes (oficial de TikTok, PHP, TypeScript, C#).

**Dos correcciones reales aplicadas al código:**
1. **Parámetros con valor vacío deben excluirse de la firma** — encontrado en el SDK C#
   con el comentario `"过滤空参数，空参数不参与firma"` (filtra parámetros vacíos, no
   participan en la firma). Si alguna vez pasamos un parámetro opcional como `""` en
   vez de omitirlo, la firma habría fallado silenciosamente contra el servidor real.
   **Ya corregido y probado.**
2. **`v2` de firma queda descartado** — se leyó el código fuente real del SDK que lo
   mencionaba: la rama `v2` existe en el archivo, pero **nunca se invoca en ningún
   lugar** — el código de producción tiene codificado `version: 'v1'`. Era código
   especulativo sin usar del autor de ese SDK, no una firma real de TikTok.
3. **Verificación de webhooks implementada** — confirmada por dos fuentes
   independientes que coinciden exactamente (un repo de referencia + código de
   producción real en PHP): `HMAC-SHA256(app_key + cuerpo_crudo)`, en el header
   `Authorization` sin prefijo `Bearer`, sin timestamp (sin protección contra replay —
   hay que deduplicar por `tts_notification_id`).
4. **`grant_type=authorized_code`** (ortografía no estándar, no "authorization_code")
   confirmado idéntico en dos SDKs de producción independientes — ya lo teníamos bien.

---

## 4. TikTok Ads — el camino más detallado de todos (lectura de fuente primaria completa)

- **GMV Max SÍ es controlable por API** completa: crear, actualizar (incluido
  presupuesto), reportes, recomendación de puja — confirmado leyendo directamente el
  YAML del SDK oficial.
- **✅ Confirmado y corregido con números exactos:** el auto-aumento de presupuesto de
  GMV Max es **aditivo, no compuesto** — cada aumento suma un % fijo del presupuesto
  ORIGINAL (default 50%, rango 50-300%), hasta 10 veces al día. Ejemplo textual de
  TikTok: **$500/día puede llegar a $3,000 en un solo día.** Ya está codificado en
  `spend.gmv_max_worst_case_daily_budget()` (commit anterior de hoy).
- **Automated Rules API confirmada como interruptor de emergencia real** — reglas que
  TikTok ejecuta en sus propios servidores (`TURN_OFF`, ajuste de presupuesto/puja),
  cada 30 minutos como mínimo. Sigue funcionando aunque nuestro proceso muera.
- **Términos de Servicio del Developer SÍ se consiguieron esta vez** (archivo completo,
  65KB, vía un proyecto de archivo de ToS) — y **permiten explícitamente** la
  interacción automatizada: *"you may... use automated means in your Application to
  collect information from or otherwise interact with the TikTok Developer
  Services."* No hay ninguna cláusula que exija un humano en el ciclo para crear
  anuncios o cambiar presupuestos — el límite real es el rate limit (contractual, no
  solo técnico) y no competir con los servicios de TikTok.
- **Rate limits Shop vs Ads son sistemas DISTINTOS** — Shop: 50 QPS fijo por app+tienda.
  Ads: escalonado por nivel (Basic 10 QPS / 600 QPM / 864,000 QPD por defecto), con
  límites específicos por endpoint documentados en detalle.

---

## 5. El servidor MCP oficial — la pieza más prometedora para tu situación

- Lanzado **30-jun-2026** como parte del "Agentic Hub".
- Dos endpoints: uno con ~400 herramientas ("flat", recomendado para agentes de
  contexto grande como Claude) y uno de ~40 herramientas núcleo ("layered").
- Auth: **OAuth 2.1 con PKCE**, sin necesidad de registrar developer app.
- **Concesión de acceso: 30 días**, luego hay que re-autorizar.
- Expone escrituras reales, incluido GMV Max — **no es de solo lectura**.
- ⚠️ **Aprobación humana: NO es un requisito de la plataforma, es solo convención.**
  Terceros venden "revisa antes de aprobar" como diferenciador de producto — si TikTok
  lo exigiera nativamente, no lo venderían como feature. **Nuestra propia compuerta de
  aprobación sigue siendo la única protección real** — no delegarla a la plataforma.

### ✅ VERIFICADO EN VIVO — 2026-09-16 (primera vez contra el servidor real)

Hasta ahora todo lo de arriba venía de un registro de sondeos de un tercero
(api-evangelist/tiktok-ads), porque el entorno de build tenía TikTok bloqueado. Desde
una sesión con salida a internet se ejecutó el flujo real. **Qué se confirmó de primera
mano** (no leído, ejecutado):

- Los dos endpoints existen y responden `401` con
  `WWW-Authenticate: Bearer resource_metadata="…"` → sí anuncian RFC 9728.
- El documento de metadatos del servidor de autorización dice, textual:

  | Campo | Valor real |
  |---|---|
  | `authorization_endpoint` | `https://business-api.tiktok.com/portal/mcp-tt4b-authorize` |
  | `token_endpoint` | `…/open_mcp/tt-ads-mcp-flat/oauth/token` |
  | `registration_endpoint` | `…/open_mcp/tt-ads-mcp-flat/oauth/register` |
  | `revocation_endpoint` | `…/open_mcp/tt-ads-mcp-flat/oauth/revoke` |
  | `code_challenge_methods_supported` | `["S256"]` (PKCE obligatorio) |
  | `scopes_supported` | `["mcp:tt4b"]` |
  | `token_endpoint_auth_methods_supported` | `["none"]` |

- **La afirmación clave queda confirmada por ejecución, no por lectura:** el registro
  dinámico de cliente (RFC 7591) funcionó y TikTok emitió un `client_id` real
  (`913d5ea1…`) **sin cuenta de developer, sin app registrada y sin empresa**.
  `token_endpoint_auth_methods: ["none"]` = cliente público, sin `client_secret`.

**Dos desviaciones reales encontradas al ejecutarlo** (ambas corregidas en el código):

1. **El desafío OAuth solo responde a `POST`.** Un `GET` al endpoint MCP devuelve
   `405 Method Not Allowed` en texto plano, **sin** cabecera `WWW-Authenticate`. Es el
   transporte "Streamable HTTP" de MCP. Nuestro conector sondeaba con `GET` — por eso
   falló la primera ejecución real.
2. **La URL de metadatos no sigue el RFC 8414.** TikTok sirve la forma *path-append*
   estilo OpenID Connect (`{issuer}/.well-known/oauth-authorization-server`) y
   devuelve `404` en la forma *path-insert* que el RFC 8414 exige. El código ahora
   prueba las dos, la observada primero.

**Detalle menor pero útil:** el registro dinámico es **determinista** — dos ejecuciones
con el mismo `client_name` + `redirect_uris` devolvieron **el mismo `client_id`**, no
uno nuevo. No genera clientes basura al reintentar.

**Lo que sigue SIN verificar** (y no se puede sin que el usuario apruebe en la UI de
TikTok): el canje del código por tokens, el `refresh`, y la vida real de 30 días de la
concesión (ese dato sigue siendo del tercero, no de primera mano).

---

## 6. Realidad de practicantes (Reddit/foros — cobertura limitada, honesto al respecto)
Reddit, Stack Overflow, Hacker News quedaron **totalmente bloqueados** esta vez también.
Lo más valioso salió de **issues reales de GitHub** de gente construyendo esto en 2026:
- **Nadie publica su cronograma real de aprobación con fecha** — el rango 2-3 días vs
  3+ semanas sigue sin resolverse en ninguna fuente pública.
- **El estado HTTP no es el canal de error** en la API de TikTok — casi todo responde
  200 aunque falle; hay que revisar el campo `code` en el cuerpo. Confirmado por dos
  fuentes independientes.
- Un ingeniero real documentó perder días por: re-serializar el JSON (rompe la firma),
  confundir los dos algoritmos de firma, y el orden de parámetros posicionales
  diferente entre SDKs de distinto lenguaje.
- **Vincular una cuenta real de TikTok para pruebas de sandbox es PERMANENTE e
  IRREVERSIBLE** — confirmado en los propios docs de TikTok. Advertencia crítica que ya
  quedó documentada en investigación previa.

---

## 7. Papers académicos — lo más relevante para nuestra arquitectura
- El benchmark más parecido a lo que construimos (**E-Commerce Bench**, 2026) encontró
  que **el agente que ganó más dinero fue de los peores evitando proveedores
  fraudulentos** — rentabilidad y seguridad son ejes casi independientes. Reforzamos
  que medir solo "¿dio dinero?" no basta.
- **Bug de corrección real identificado:** nuestros intervalos de Wilson para decidir
  "matar" un creativo **no son válidos bajo evaluación repetida** ("peeking") — la
  literatura recomienda secuencias de confianza "anytime-valid" en su lugar. Esto
  produce falsos "matar" más seguido de lo que nuestro nivel de confianza declarado
  sugiere. Es un bug de calidad (mata cosas buenas de más), no de seguridad (nunca
  gasta de más) — pendiente de arreglar en una tarea aparte.
- Conversión con retraso: la literatura confirma que decidir con datos muy recientes
  **sesga las decisiones de "matar" hacia ser demasiado agresivas** — recomienda
  esperar un mínimo de "madurez" de los datos antes de juzgar.

---

## Conclusión — plan de acción recomendado

1. **No hay atajo mágico para el requisito de empresa del lado de Ads** — ahí es
   definitivo. Del lado de Shop, **hay ambigüedad real entre dos documentos oficiales**
   — vale la pena simplemente intentar el registro para ver qué pide en la práctica,
   sin comprometerse a nada irreversible.
2. **La ruta más rápida y de menor fricción para empezar: el servidor MCP oficial de
   Ads** — no pide cuenta de developer. Vale la pena probarlo primero.
3. **Nuestro código de firma ya está corregido** con los dos bugs reales que encontró
   esta investigación, y la verificación de webhooks quedó implementada por primera vez.
4. Dos bugs de arquitectura quedaron identificados para una tarea futura (no urgente,
   no de seguridad): intervalos de confianza más robustos para "matar" creativos, y un
   guardia de "madurez mínima" de datos antes de decidir.
