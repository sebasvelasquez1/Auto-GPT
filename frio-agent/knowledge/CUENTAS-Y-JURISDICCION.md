# Topología de cuentas de IntoSpirit — restricción estructural del proyecto

**Fuente: el propio usuario (dueño del proyecto), 2026-09-16.** Dato declarado por él,
no verificado de forma independiente por Frío (no hay forma de verificarlo desde aquí;
se confirmará al conectar cada cuenta). Se registra tal cual, porque cambia decisiones
técnicas reales.

## El hecho

TikTok Shop **solo opera en Estados Unidos** para el caso del usuario. Su cuenta
personal de TikTok es de **Colombia**, así que **no** podía abrir el Shop con ella.
Creó una estructura aparte: **tiene empresa** y abrió el TikTok Shop con una cuenta
distinta de la personal.

Por lo tanto hay **al menos tres identidades separadas**, y confundirlas rompe el
proyecto:

| Identidad | Qué es | Sirve para |
|---|---|---|
| Cuenta personal de TikTok (Colombia) | La del usuario como persona | **Nada del proyecto.** Aprobar con esta es el error a evitar. |
| Cuenta / Seller Center de TikTok Shop (EE. UU., empresa) | Dueña de la tienda y el catálogo | Conexión de Shop (catálogo + ventas) — pendiente |
| TikTok Ads Manager de la empresa de EE. UU. | Cuenta de anuncios | Conexión de Ads vía MCP — **esta es la que se autoriza** |

El usuario confirmó (2026-09-16) que **ya tiene TikTok Ads Manager** para la empresa de
EE. UU.

## Consecuencias técnicas (ya implementadas, no solo anotadas)

1. **La autorización del MCP de Ads debe hacerse con el login de la empresa de EE. UU.**,
   no con el personal. Si el navegador tiene sesión abierta con la cuenta personal, hay
   que usar ventana privada o cerrar sesión primero — si no, TikTok autoriza la cuenta
   equivocada sin avisar.

2. **Una concesión de MCP cubre TODAS las cuentas de anuncios que ese login alcanza.**
   No es "una cuenta, un token". Por eso se añadió un candado duro:
   `FRIO_TIKTOK_ADS_ADVERTISER_ID` fija **la única** cuenta de anuncios en la que Frío
   puede operar, y `guardrails.require_pinned_ad_account` **lanza un error** (no un
   aviso que se pueda ignorar) si:
   - una acción en vivo apunta a otra cuenta, o
   - se intenta una acción en vivo **sin** cuenta fijada.

   Se eligió `raise` en vez del patrón `GuardrailVerdict` del resto del módulo
   precisamente porque un veredicto se puede leer e ignorar; gastar en la cuenta
   equivocada es dinero real en el lugar equivocado. Ver `tests/test_ad_account_pin.py`.

3. **Shop y Ads son dos conexiones independientes**, con credenciales distintas. La de
   Ads (MCP) no da acceso al catálogo ni a las ventas, y viceversa. Conectar una no
   conecta la otra.

## Lo que sigue sin resolver

- El `advertiser_id` real de la cuenta de anuncios de EE. UU.: se obtiene al completar
  la autorización (o desde TikTok Ads Manager). **Hasta que esté fijado, ninguna acción
  de anuncios en vivo puede ejecutarse** — el candado lo impide por diseño.
- La ambigüedad de elegibilidad del lado Shop (dos documentos oficiales de TikTok que se
  contradicen, ver `investigacion/2026-09-conexion-tiktok-shop-ads-consolidado.md` §1)
  **posiblemente ya no aplique**: el usuario dice tener empresa y el Shop ya abierto. Se
  confirma al intentar el registro real, no antes.
