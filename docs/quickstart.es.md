# Guía rápida (español)

`eltoque-python` es un SDK de Python **independiente y no oficial** para la API oficial de tasas
de cambio de elTOQUE. No está desarrollado, patrocinado, respaldado ni soportado por elTOQUE.

> **Las tasas de cambio son referenciales, no oficiales. Fuente: elTOQUE.
> El acceso requiere registro y un token de API propio de cada aplicación.**

## Instalación

```bash
pip install eltoque-python
```

Requiere Python 3.11 o superior.

## Obtener un token

El SDK **no da acceso** a la API. Cada aplicación necesita su propio token:

1. Solicítalo en el formulario oficial: <https://tasas-token.eltoque.com/>
2. Lee los [términos y condiciones de uso](https://eltoque.com/api-tasas-de-eltoque-terminos-y-condiciones-de-uso).
3. Guárdalo en una variable de entorno; nunca en el código ni en Git:

```bash
export ELTOQUE_API_TOKEN="el-token-de-tu-aplicacion"
```

No compartas tu token con terceros ni lo incluyas en código que se ejecute en el navegador.

## Uso síncrono

```python
import os

from eltoque import ElToqueClient

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
    respuesta = client.get_latest_rates()
    print(respuesta.data)  # JSON original del proveedor, sin modificar
```

`get_latest_rates()` devuelve las tasas de las últimas 24 horas desde el momento de la petición.

## Tasas tipadas

`respuesta.data` es siempre el JSON original. `respuesta.rates` es una vista opcional y validada
con la forma confirmada en la API real: códigos de moneda con valores `Decimal`.

```python
import os

from eltoque import ATTRIBUTION, ElToqueClient

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
    tasas = client.get_latest_rates().rates

usd = tasas.rates.get("USD")  # Decimal o None: el conjunto de códigos es abierto
print(usd, tasas.reported_at)
print(ATTRIBUTION)  # "Source: elTOQUE. Exchange rates are indicative, not official."
```

`reported_at` es la hora en que el proveedor calculó la respuesta (no la ventana pedida) y su zona
horaria no está documentada. Si el formato cambia, `respuesta.rates` lanza `ElToqueDecodeError`
y `respuesta.data` sigue funcionando.

## Uso asíncrono

```python
import asyncio
import os

from eltoque import AsyncElToqueClient


async def main() -> None:
    async with AsyncElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
        respuesta = await client.get_latest_rates()
        print(respuesta.data)


asyncio.run(main())
```

## Fechas

```python
import os
from datetime import date, datetime

from eltoque import ElToqueClient

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
    # Un intervalo concreto (menor de 24 horas)
    intervalo = client.get_rates(
        datetime(2022, 10, 27, 0, 0, 0),
        datetime(2022, 10, 27, 23, 59, 59),
    )
    # Atajo: de 00:00:00 a 23:59:59 de un día
    dia = client.get_rates_for_day(date(2022, 10, 27))
    print(intervalo.data, dia.data)
```

Reglas importantes:

- Usa `datetime` **sin zona horaria** (naive). Los valores con zona horaria se rechazan porque la
  API no documenta su zona horaria y el SDK no intenta adivinarla.
- `date_from` debe ser anterior a `date_to` y el intervalo **menor de 24 horas**; si no, la API
  respondería HTTP 400. El SDK lo valida antes de enviar la petición.
- `get_rates_for_day` no garantiza ser un día calendario local completo.
- No encadenes muchas peticiones para reconstruir periodos largos: la extracción masiva de datos
  puede violar los términos de uso.

## Límites y errores 429

Por defecto cada clave permite **60 peticiones por minuto y hasta 10 por segundo** (tu clave puede
tener otros límites). Al excederlos la API responde `429` con la cabecera `Retry-After`.

```python
import os

from eltoque import ElToqueClient, ElToqueError, ElToqueRateLimitError

with ElToqueClient(api_token=os.environ["ELTOQUE_API_TOKEN"]) as client:
    try:
        respuesta = client.get_latest_rates()
    except ElToqueRateLimitError as error:
        print(f"Límite excedido; reintenta en {error.retry_after} s")
    except ElToqueError as error:
        print(f"Falló la petición: {error}")
    else:
        print(respuesta.rate_limit.remaining, "peticiones restantes")
```

Los reintentos están **desactivados** por defecto (`max_retries=0`) y consumen cuota. Con
`max_retries=2`, por ejemplo, se reintenta solo ante 429, 502, 503, 504 y fallos de red,
respetando `Retry-After`. Nunca se reintentan 400, 401 ni 422.

## Qué no sabemos todavía

La documentación oficial **no publica el esquema de la respuesta exitosa**; el modelo `Rates` se
basa en lo observado en la API real (2026-10-23), no en una garantía de elTOQUE. Además, la zona
horaria no está documentada y la API es más permisiva que su documentación (acepta, por ejemplo,
una ventana de exactamente 24 horas). Consulta [api-contract.md](api-contract.md).

## Atribución y aspectos legales

- Al mostrar tasas, indica a **elTOQUE como fuente** y que son **valores referenciales**.
- No modifiques los datos, no compartas tu clave, no revendas ni extraigas datos en masa.
- La licencia MIT cubre solo el código de este SDK, no la API, los datos ni las marcas de elTOQUE.
