# Matriz de trazabilidad Santos → ecuaciones → código

Fuente primaria: O. G. dos Santos, capítulo 4 (modelo matemático), capítulo 5 (aplicación), capítulo 6 (ciclo estabilizado), capítulo 7 (sensibilidad) y capítulo 8 (optimización). La copia local es mayormente escaneada; la numeración impresa está desplazada aproximadamente 19 páginas respecto del PDF. Las notas versionadas del repositorio cubren principalmente el capítulo 5, páginas impresas 117–144.

## 1. Eventos físicos A–H

| Evento | Definición física de Santos | Condición computacional |
|---|---|---|
| A | abre válvula motora; inicia inyección | `t=0`, control de inyección activo |
| B | abre GLV | equilibrio de fuerza/presión de apertura |
| C | cara superior del tapón alcanza superficie | posición superior = profundidad de válvula/superficie según coordenada |
| D | comienza producción del tapón | frente del tapón entra al tramo productor |
| E | cara inferior del tapón alcanza superficie | base del tapón = superficie |
| F | película alcanza velocidad media cero | `v_f = 0` |
| G | equilibrio final de descompresión en la formulación específica 4.3 | `P_t3−P_ts−rho_g g(H_gv−h_l)=0`; la recuperación de `P_t1` queda diagnóstica |
| H | columna líquida acumulada recupera longitud inicial | `h_l − L_initial = 0`, con cruce creciente |

En el ejemplo de Santos, la fase 4.1 de descompresión no aparece porque la GLV cierra antes de que la base del tapón alcance la superficie. Los segmentos observados son AC, BD, DE, EF, FG y GH (Tablas 5.6–5.7, página impresa 131).

## 2. Matriz por etapa

| Etapa | Fuente/equaciones | Variables y cierres principales | Código actual | Estado |
|---|---|---|---|---|
| A→B, inyección | condiciones 5.1–5.15; 4.1.6, 4.1.10, 4.1.17–19 | presiones casing/tubing, gas inyectado, válvula motora; geometría/EOS | `initial_conditions.py`, `stage1_dynamic.py`, `valves.py` | IMPLEMENTADO |
| B→C, elevación con inyección | Tabla 5.1: 4.1.6, .9, .17–.19, .26, .28, .32, .35, .40, .46, .48, .50 | presiones, densidades, posiciones/velocidades de tapón y burbuja, película, caudal GLV | `stage_bc_common.py` modo Santos | IMPLEMENTADO |
| C→D, elevación tras cierre motor | mismo sistema de etapa 2; cierre GLV como evento interno | estado canónico de 14 componentes; enclavamiento GLV; balances gas/líquido | `stage_cd_common.py` corregido | IMPLEMENTADO |
| D→E, producción | etapa 3; 4.1.53 sustituye relación de elevación correspondiente | salida de tapón, gas y película; volumen producido | `stage_de_dynamic.py` corregido | IMPLEMENTADO |
| E→F, descompresión fase II | Tabla 5.1: 4.1.76, .80, .83, .84, .87, .89, .90 | sistema exacto de siete variables, `V_g=A_B(z_v-h_l)`, evento `v_f=0` | `stage_ef_dynamic.py`, `STAGE_EF_SANTOS_EQUATION_CONTRACT.md` | IMPLEMENTADO; BLOQUEADO EN E POR INCOMPATIBILIDAD D→E/4.1.90 |
| F→G, descompresión fase III | 4.1.89, .94, .97, .107, .108; cierres .24–.25 y .95–.103 | entrada F por identidad física; sin ledger→altura ni media→fondo; evento de equilibrio de momento | `stage_fg_dynamic.py`, `audit_stage_fg.py` | NO EJECUTADO EN CASO BASE — NOT_READY_FOR_GH |
| G→H, alimentación | 4.1.94, .107, .109, con .95 y cierres geométricos/EOS | película descendente y líquido de formación alimentan columna; presión hidrostática; evento longitud inicial | no hay módulo ni evento terminal H integrado | FALTANTE |

## 3. Contrato implementado F→G

Sistema físico de la fase 4.3:

- Balance de película: `2π z_v (r−y) dy/dt + q_f = 0` (4.1.94).
- Cierre laminar de retorno: `q_f = ρ_l g (2πr)y³/(3μ_l)` (4.1.95).
- Densidad media del gas entre fondo y superficie (4.1.96).
- Balance de masa de gas en el núcleo (4.1.97).
- Momento/descarga del gas y cierres de velocidad, fricción y EOS (4.1.98–4.1.103).
- Balance de columna inferior, con afluencia y película: `A_B dh_l/dt − 2π(r−y)h_l dy/dt − q_f − q_res = 0` (4.1.107).
- Cierre diferencial EOS `P_t3–ρ_gt3` (4.1.108).
- Continúa la ecuación de la columna líquida 4.1.89.

El estado implementado es `[ρ_gt3, P_t3, P_t1, h_l, y, V_return, V_res, m_g,out]`, en SI. `A_B`, `A_f`, `q_f`, `ρ_gs`, `ρ_g`, `v_g`, `v_gs`, `ρ_gt1` y los inventarios se calculan algebraicamente con funciones nombradas. Los tres últimos estados son ledgers de procedencia y no sustituyen las cinco variables físicas del sistema Santos.

Condiciones iniciales en F: se transfieren por identidad masa de gas, `y`, película, producido, fallback y entrada acumulada. E→F integra el ledger dinámico `q_res(P_t1)`. Como E→F almacena densidad/presión media del núcleo y Santos 4.3 necesita `ρ_gt3/P_t3` de fondo, el mapa usa 4.1.96 y EOS 4.1.101 conservando exactamente la masa. Esa transformación espacial hace que `P_wb>P_r` al inicio de FG; el caudal bruto negativo se conserva y clasifica como inválido para la IPR productora.

Evento terminal G implementado: `P_t3−P_ts−ρ_g g(z_v−h_l)=0`, dirección `−1`. `P_t1−P_to,initial=0` se registra como diagnóstico no terminal. G no se etiqueta como ciclo completo.

Resultado Milestone 1.5: `t_F=534.028521 s`; la raíz legacy ocurre `101.846418 s` después de F, pero el residual corregido no cruza cero hasta el horizonte ampliado de 10,000 s. En ese horizonte conserva balances (`2.59e-12` gas, `1.14e-13` líquido), pero la IPR presenta flujo inverso inválido al inicio de FG. Dictamen: `NOT_READY_FOR_GH`.

Resultado Milestone 1.6: el RHS fuente de Stage 4.2 y sus residuos independientes
están implementados, pero el E heredado exige `rho_g=40.3394 kg/m3` por masa y
`23.3774 kg/m3` por 4.1.88/4.1.90. Residuo relativo `0.7255765`. No se proyecta
el estado, no se fabrica F y no se ejecuta F→G. Estado A→F:
`NOT_SOURCE_CERTIFIED_A_TO_F`; dictamen global: `NOT_READY_FOR_GH`.

## 4. Contrato mínimo G→H

Santos reemplaza la ecuación dinámica de la columna por:

`dP_t1/dt − ρ_l g dh_l/dt = 0` (4.1.109).

Se conservan 4.1.94, 4.1.95 y 4.1.107. El estado mínimo puede ser `[y, h_l, P_t1]`, más inventarios conservativos y cierres algebraicos. El caudal que incrementa la columna es la suma coherente de afluencia de formación y retorno de película; ningún término puede contarse dos veces.

Condiciones iniciales en G: resultado terminal F→G sin correcciones manuales. Evento H: `h_l = L_initial`. El estado H debe guardar película residual, presiones, masas de gas, volúmenes acumulados, configuración de válvulas y tiempo del ciclo para iniciar el siguiente A.

## 5. Continuidad y balances obligatorios

En cada frontera `X→Y`:

1. La última muestra de X y la primera de Y deben coincidir, salvo variables algebraicas recalculadas con el mismo estado.
2. La concatenación elimina solo la muestra temporal duplicada; nunca elimina inventario.
3. Balance líquido: inicial + afluencia = columna + película + producido + fallback/retención definida.
4. Balance gas: inicial + inyectado = gas retenido + gas producido/ventilado.
5. Cada término se expresa en una base de unidades explícita; gas estándar y gas in situ no se mezclan.
6. Todo clamp, proyección de estado o regularización se contabiliza y se prueba como residuo.

## 6. H→A y ciclos sucesivos

El capítulo 6 define régimen estabilizado cuando el líquido producido por ciclo iguala el volumen suministrado por el reservorio en ese ciclo. El primer ciclo no es representativo porque parte de una columna inicial y deja película/inventarios que se transfieren a ciclos posteriores.

Para H→A se debe transferir, como mínimo: espesor/volumen de película residual por región, altura de columna, presiones y densidades terminales, masas de gas, estado de GLV y válvula motora, y ledgers acumulados reiniciados solo en su componente “por ciclo”. La prueba no debe imponer artificialmente estado inicial = estado final; debe verificar conservación y ejecutar el siguiente A.

La fuente no especifica tolerancia numérica, norma ni número de ciclos consecutivos para declarar convergencia: **SOURCE_MISSING**. Es una decisión metodológica que debe documentarse y aprobarse. Debe incluir simultáneamente convergencia de volumen producido, volumen aportado, duración y vector de estado terminal, no una sola curva.

## 7. Criterio de aceptación científica

Un tramo se considera implementado solo si: reproduce las ecuaciones indicadas; declara estado, algebraicas, IC/BC y evento; conserva masa con residual escalado; tiene pruebas unitarias y de continuidad; y entrega diagnósticos de solver. La coincidencia visual con una figura de Santos es evidencia de reproducción, no validación independiente.
