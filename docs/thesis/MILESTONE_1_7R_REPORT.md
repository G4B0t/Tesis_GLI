# Milestone 1.7R — reconciliación fuente B→E

## Dictamen

**BLOCKED_BY_SOURCE**. Se sustituyó el proxy GLV de la ruta científica B→C,
C→D y D→E por una función central de Santos 4.1.13/.15. También se reconcilió
la relación 4.1.27/4.1.28: como la forma diferencial impresa no incluye
`df_B/dt`, el factor `f_B` se evalúa una vez en B y se conserva fijo hasta E.
No se calibró ningún coeficiente.

La trayectoria ya reconciliada todavía cierra la GLV **29.534199902 s** después
de D, cuando quedan **178.700407070 m** de golfada. Por tanto no existe E
físico y no se inicia Stage 4.2 ni ningún tramo posterior.

## Fuente y tratamiento aplicado

- 4.1.13 da el caudal volumétrico GLV; 4.1.14/.15 lo llevan a caudal másico
  mediante densidad a condición estándar declarada.
- Para `Pt1/Pc2` menor que el cociente crítico, se mantiene el máximo de la
  propia expresión: extensión crítica continua, declarada y probada. El caso
  base en D es subcrítico/no estrangulado.
- Las páginas revisadas dicen explícitamente que 4.1.28 se obtiene al
  diferenciar 4.1.27, pero no publican una correlación numérica para `f_B`.
  Se mantiene la correlación heredada únicamente como semilla no calibrada en
  B (`f_B=0.1278397857624769`) y se marca esa especificación como
  `SOURCE_MISSING`; no se afirma certificación completa de fuente.

## Resultado de la cadena reconciliada

Tiempos absolutos desde A: B = 32.640155842 s, C = 59.443011788 s,
D = 514.485952492 s y cierre GLV = 544.020152393 s. La GLV está abierta en D
con `m_dot=0.193529835526 kg/s`. El cierre ocurre antes de E y el terminal es
`SOURCE_AMBIGUITY_GLV_CLOSE_BEFORE_E`.

Respecto a M1.7, D se desplaza por la corrección upstream; el cierre D→GLV
aumenta 0.969373390 s, el remanente baja 2.407548157 m y el caudal GLV en D
baja 0.003788878 kg/s. El remanente continúa siendo material, no una guarda
numérica ni una aproximación de E.

## Verificación independiente

- GLV 4.1.13/.15: pruebas independientes en regímenes subcrítico y crítico.
- Una sola función central está comprobada en los módulos científicos B→C,
  C→D y D→E; el proxy queda sólo en las rutas históricas.
- Identidad canónica D: error absoluto máximo 0.0.
- Deriva de 4.1.27 con `f_B` fijo: 0.000453997 Pa máximo.
- Conservación relativa: gas `3.46598e-16`; líquido `3.14180e-10`.
- Refinamiento `max_step=1/0.5/0.25 s`: cierre D→GLV
  29.534199893 / 29.534199902 / 29.534199902 s; E no aparece en ninguna
  corrida.

El JSON reproducible está en `milestone_1_7R_results.json`; el auditor se
ejecuta con `python -m gli.audit_milestone17r` y no escribe el repositorio.

## Alcance y siguiente evidencia requerida

La transición pre-E con GLV cerrada sigue sin estar especificada de forma
ejecutable en la fuente revisada, y falta la correlación explícita de `f_B`.
Se necesita esa evidencia primaria antes de modelar una topología posterior al
cierre o de fabricar E. No se modificaron los contratos Stage 4.2, E→F,
F→G o G→H, ni se ejecutaron downstream.
