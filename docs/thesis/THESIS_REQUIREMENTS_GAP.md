# Brechas frente al perfil de tesis

Escala: **IMPLEMENTADO** = existe y está cubierto por código/pruebas; **PARCIAL** = existe pero con alcance, trazabilidad o evidencia insuficiente; **FALTANTE** = no existe como capacidad defendible.

## Matriz de objetivos y actividades

| # | Requisito del perfil | Evidencia actual | Estado | Brecha verificable / cierre requerido |
|---:|---|---|---|---|
| 1 | Caracterizar pozo y sistema GLI | Caso Santos parametrizado | PARCIAL | Falta esquema general y procedencia por campo, no solo un caso embebido |
| 2 | Definir geometría y variables | Dataclasses y geometría en SI | PARCIAL | API completa valores con defaults no trazados; faltan perforaciones/instalación genérica |
| 3 | Representar reservorio/IPR | PI constante y `q_res` | PARCIAL CRÍTICO | Usa presión superficial; debe depender de `P_wf(t)` y del modelo IPR documentado |
| 4 | Formular modelo dinámico | Ecuaciones modularizadas A→F | PARCIAL | F→G y G→H ausentes |
| 5 | Declarar supuestos | Notas y docstrings distribuidos | PARCIAL | Falta inventario único: régimen, temperatura, compresibilidad, película, válvulas, pérdidas |
| 6 | Condiciones iniciales | Santos 5.1–5.15 y transferencias A→F | PARCIAL | F/G/H y siguiente ciclo no definidos |
| 7 | Condiciones de frontera | Cierres por etapa A→F | PARCIAL | F/G/H, perforaciones e IPR no cerrados completamente |
| 8 | Flujo transitorio multifásico | Tapón, burbuja, gas y película A→F | PARCIAL | No representa retorno completo de película ni alimentación |
| 9 | Implementar en Python | Backend/API operativo | PARCIAL AVANZADO | El “ciclo” productivo termina en F |
| 10 | Método numérico | Radau, eventos, diagnósticos | PARCIAL | Perfil propone RK4; justificar cambio, documentar tolerancias y convergencia A→H |
| 11 | Estabilidad/convergencia | Pruebas, residuos, auditorías de rigidez | PARCIAL | Sin refinamiento A→H ni convergencia multiciclo |
| 12 | Calibrar con datos | No hay pipeline ni parámetros estimados | FALTANTE | Definir datos, parámetros, bounds, objetivo, identifiabilidad y freeze |
| 13 | Validar con datos/literatura | Comparaciones Santos y Liao parcial | PARCIAL | Es reproducción de referencia; falta conjunto independiente y separación de calibración |
| 14 | RMSE/MAPE y métricas | Residuos internos y errores específicos | FALTANTE | Implementar MAE, RMSE, MAPE seguro, NRMSE y reglas de alineación |
| 15 | Optimización operacional | Ningún optimizador ni objetivo formal | FALTANTE | Completar ciclo, calibrar/validar, después problema acotado y reproducible |
| 16 | Escenarios operacionales | UI de escenarios y matriz parcial | PARCIAL | Dependen de A→F y no demuestran respuesta estabilizada |
| 17 | Sensibilidad | OAT y combinaciones | PARCIAL | Faltan variables Santos, metodología global y métricas multiciclo |
| 18 | Robustez/generalización | Contratos internos y caso base | PARCIAL | Sin pozos independientes, incertidumbre, dominio de aplicabilidad ni pruebas out-of-sample |

## Dictamen por objetivo específico

### Objetivo 1 — caracterización y formulación

Avance sustancial en geometría, propiedades y formulación A→F. No se cumple totalmente porque el objeto de pozo no es genérico/proveniente y la IPR usa una presión físicamente incorrecta.

### Objetivo 2 — implementación, calibración y validación

La implementación A→F es sólida como software. Calibración: 0% como pipeline explícito. Validación: solo reproducción interna/benchmark parcial; no existe validación independiente ni las métricas prometidas.

### Objetivo 3 — optimización

No iniciado en sentido científico. Las sensibilidades no equivalen a optimización. Agregar Differential Evolution ahora optimizaría un objetivo parcial sobre un ciclo incompleto y parámetros no calibrados.

### Objetivo 4 — escenarios, sensibilidad y robustez

Hay una base exploratoria útil, pero todavía describe el primer recorrido A→F. Debe migrar a métricas por ciclo estabilizado e incluir incertidumbre y dominio de datos.

## Brechas de evidencia

### Disponibles

- Fuente primaria Santos local y extractos versionados.
- Perfil de tesis con objetivos, metodología, RMSE/MAPE, calibración, validación y optimización.
- Caso base Santos y referencias digitalizadas.
- 135 pruebas backend aprobadas bajo configuración correcta.
- Build/typecheck frontend aprobados.

### No disponibles o no demostrados

- Dataset de campo real con señales temporales, metadatos y permisos de uso.
- Separación formal calibración/validación.
- Incertidumbres instrumentales y calidad de datos.
- Costo local de gas/energía, valor de líquido y restricciones operativas para objetivo económico.
- Tolerancia fuente para régimen estabilizado.
- Datasheets de válvulas/áreas efectivas y bounds científicamente justificables.
- Evidencia versionada de la configuración de rama de Vercel.

No se deben inventar pozos, mediciones, costos, tolerancias ni intervalos. Cada uno queda como **SOURCE_MISSING** hasta que sea aportado o aprobado metodológicamente.

## Orden de cierre recomendado

1. Corregir contrato de afluencia/IPR y documentar supuestos.
2. Implementar y probar F→G.
3. Implementar y probar G→H.
4. Encadenar A→H y H→A; ciclos sucesivos y estabilización.
5. Crear modelo de datos de pozo y adapters sin cambiar física.
6. Ingerir referencias/datos reales con procedencia.
7. Implementar métricas, alineación y capability levels.
8. Calibrar; congelar parámetros.
9. Validar independientemente.
10. Sensibilidad global/robustez.
11. Optimización y, al final, adaptación de UI/despliegue.
