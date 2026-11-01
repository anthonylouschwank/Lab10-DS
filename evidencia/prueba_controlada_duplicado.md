# Prueba controlada: duplicado

1. Problema introducido en una copia de la fuente: se repitio una fila de turistas (misma clave anio-mes-via-frontera-pais-agrupacion-tipo).
2. Ejecucion con la copia: `20261101T113653-a51e91`, estado **fallida**; control `c_unicidad` = critico.
   Causa registrada: ControlCritico: Fallaron controles criticos: c_unicidad (2 filas con clave repetida (2 en tipos usados); clave ['anio', 'mes', 'via', 'frontera', 'pais', 'agrupacion', 'tipo'])
3. Version vigente antes del fallo: `20261101T113642-993761`; despues del fallo: `20261101T113642-993761`. Archivos de la version aprobada sin cambios: si.
4. Copia corregida y nueva ejecucion: `20261101T113653-87a4ab`, estado **publicada**; version vigente final `20261101T113653-87a4ab`.

Resultado: el pipeline detecto el problema, conservo la version aprobada y se recupero.
