# Plan simple: registrarte como developer en TikTok Shop (para ejecutar mañana)

**Tiempo estimado:** 15–20 minutos. **No hay código. Es llenar un formulario.**
**Requisito previo:** tener una tienda TikTok Shop activada → ✅ YA lo cumples.

Fuente: documentación oficial de TikTok (Developer.md, TikTok_Shop_developer_guide.md).
Somos "Seller Developer" → Custom App → autorización directa 1:1 a TU tienda.

---

## Antes de empezar, ten a la mano
- [ ] Tu login de TikTok Shop (el mismo con el que entras al Seller Center).
- [ ] Nada más — los datos del negocio ya están ligados a tu tienda.

## Los pasos (mañana, en orden)
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
      ⏳ TikTok la revisa (~3 semanas en EE.UU. por el chequeo legal/compliance).
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
