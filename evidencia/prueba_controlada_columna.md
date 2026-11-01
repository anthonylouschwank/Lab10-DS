# Prueba controlada: columna

1. Problema introducido en una copia de la fuente: se elimino la columna indispensable `Viajero`.
2. Ejecucion con la copia: `20261101T113642-74246e`, estado **fallida**; control `a_columnas_tipos` = critico.
   Causa registrada: ControlCritico: Fallaron controles criticos: a_columnas_tipos (Faltan columnas indispensables: ['Viajero'])
3. Version vigente antes del fallo: `20261101T113614-7a0ca0`; despues del fallo: `20261101T113614-7a0ca0`. Archivos de la version aprobada sin cambios: si.
4. Copia corregida y nueva ejecucion: `20261101T113642-993761`, estado **publicada**; version vigente final `20261101T113642-993761`.

Resultado: el pipeline detecto el problema, conservo la version aprobada y se recupero.
