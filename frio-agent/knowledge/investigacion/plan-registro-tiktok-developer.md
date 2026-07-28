# Plan simple: registrarte como developer en TikTok Shop (para ejecutar mañana)

**Tiempo estimado:** 15–20 minutos. **No hay código. Es llenar un formulario.**
**Requisito previo:** tener una tienda TikTok Shop activada → ✅ YA lo cumples.

Fuente: documentación oficial de TikTok (Developer.md, TikTok_Shop_developer_guide.md).
Somos "Seller Developer" → Custom App → autorización directa 1:1 a TU tienda.

---

## Antes de empezar, ten a la mano
- [ ] Tu login de TikTok Shop (el mismo con el que entras al Seller Center).
- [ ] Nada más — los datos del negocio ya están ligados a tu tienda.

---
## 🛑 ALTO — actualización tras la investigación (2026-07-28)

**NO envíes el formulario "Start Business" / "Category & market"** (el de
`/approval/profile/apply-certificate`) todavía. Razones:

1. Su texto ("post your service", "clients... authorize your service") es del embudo
   de **Service Partner** — quien vende servicios a OTROS vendedores. Nosotros somos
   *seller developer* (app privada para nuestra propia tienda). Probablemente es el
   embudo equivocado.
2. La región de registro **NO se puede cambiar una vez aprobada**. Enviar mal = daño
   permanente.
3. La documentación de TikTok sí distingue dos rutas: existe una página propia
   "Seller Developer Onboarding Onepager"
   (`partner.tiktokshop.com/docv2/page/seller-developer-onboarding-onepager`)
   distinta de "Register as a service partner".

**Acción de mayor valor (2 min):** abre esa página del onepager (tú SÍ puedes; el
agente recibe 403) y pega el texto en el chat. Eso resuelve la duda sin arriesgar nada.
**Alternativa segura:** preguntar por el chat de soporte de Partner Center si un
Custom App para la propia tienda requiere el certificado de empresa.

⚠️ **Riesgo abierto sin resolver:** no se pudo verificar si se puede aprobar sin
empresa registrada (LLC). El panel pide "Company registration certificate" +
"Legal representative's information".

---
## Los pasos (mañana, en orden — SOLO tras aclarar lo de arriba)
- [ ] **1.** Entra al login oficial del Partner Center Console:
      **https://partner-sso.tiktok.com/account/login**
      (confirmado por la doc oficial "About the Partner Center Console").
      Alternativa si esa no carga bien para EE.UU.: **https://partner.us.tiktokshop.com**.
- [ ] **2.** Inicia sesión con tu cuenta de TikTok Shop. Elige registrarte como
      **Seller Developer** (developer de vendedor / para tu propia tienda).
      > Nota: la consola atiende varios "tipos de partner". Si te pide elegir tipo
      > y NO ves claro "Seller / Seller Developer", sácame un screenshot y te digo
      > cuál marcar — no adivines.
- [ ] **3.** Crea una **Custom App** (NO "Public App"). Ponle cualquier nombre,
      ej. "Frio Agent".
- [ ] **4.** En los permisos (scopes) de la app, activa: **Products** (productos)
      y **Orders** (órdenes). Son los únicos que necesitamos para empezar.
- [ ] **5.** Envía la solicitud / app a revisión.
      ⏳ TikTok la revisa. ⚠️ DURACIÓN NO VERIFICADA y las fuentes SE CONTRADICEN:
      el developer guide dice "budget 3+ weeks" (US/UK) pero el FAQ general de
      TikTok dice "several days to two weeks". No se elige la cifra bonita —
      se documentan ambas. Planifica para el escenario largo.
      **Durante esa espera no haces NADA más** — el reloj corre solo.
- [ ] **6.** Cuando la app aparezca, copia el **App Key** y el **App Secret** y
      pásamelos (o súbeme un screenshot). Esos son los primeros datos que necesito.

## Si te atoras en cualquier pantalla
Sácale un **screenshot** o copia el texto y mándamelo aquí mismo — te desatoro
en el momento, con lo que TÚ ves de verdad (no con suposiciones).

## Qué NO tienes que hacer mañana
- ❌ Nada de código.
- ❌ Nada de "access token" todavía — eso viene DESPUÉS de que aprueben la app.
- ❌ No esperes a que termine la revisión para seguir con el proyecto: yo avanzo
  el resto mientras tanto.

## Lo que yo (Frío/dev) hago de mi lado, en paralelo
- Ya dejé la config lista para recibir tus credenciales (app_key, app_secret, etc.).
- Cuando me des App Key + App Secret + (tras aprobación) el access token, y el
  documento del "algoritmo de firma", escribo la conexión real y jalamos tu
  catálogo de verdad — en horas, no semanas.
