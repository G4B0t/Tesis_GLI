# Mapa técnico para la futura redacción de tesis — M1.7R

No modifica la tesis DOCX. Secciones sugeridas por tema, sin inventar numeración
del manuscrito final. Madurez numérica no equivale a validación bibliográfica
cuantitativa ni de campo. Estado global: BLOCKED_BY_SOURCE.

| Tema técnico | Fuente | Estado de implementación | Madurez científica | Sección de tesis afectada |
|---|---|---|---|---|
| Producción de golfada: conjunto de 13 ecuaciones | Santos p.45–46, Tabla 5.1 p.117 | Contrato trazado; .46→.53 | SOURCE_VERIFIED | Modelo matemático / etapa 3 |
| Integración Stage 3 hasta cierre | `stage_de_santos.py`, pruebas independientes | 21 componentes, primeros 14 por identidad D; balances verificados solo hasta cierre | NUMERICALLY_VERIFIED | Implementación computacional / resultados parciales |
| GLV abierta en D y cierre dinámico | Santos .13/.15, mecánica .5.13 | Estado y flujo fuente continuos; cierre a 29.5341999 s de D | NUMERICALLY_VERIFIED | Control de válvulas / continuidad de etapas |
| Correlación de caudal GLV | Santos p.33, .13/.15 | Función central fuente para B→C/C→D/D→E; ensayos crítico y subcrítico independientes | SOURCE_VERIFIED | Hipótesis, cierres constitutivos y limitaciones |
| Stage 3→Stage 4, cierre pre-E | Tabla 4.1 p.29; p.45,47,52; Tablas 5.6–5.7 p.131 | Sin transición para separación material; no se fabrica E | BLOCKED | Condiciones de transición / discusión |
| Condición de entrada Stage 4.2 | Santos .83/.88/.90, contrato EF | Gate estricto con altura documentada, presión y densidad por identidad; E base no disponible | BLOCKED | Descompresión fase II / condiciones iniciales |
| Afluencia de reservorio | IPR dinámica centralizada de M1.5; Santos y perfil académico | Sin modificar PI ni recortar signo; reservorio alimenta filme en tramo Stage 3 verificado | NUMERICALLY_VERIFIED | Acoplamiento pozo–reservorio / conservación |
| Método numérico y eventos | .53 y geometría E; elecciones metodológicas explícitas | Radau, cierre descendente y protección de dominio separada del RHS | IMPLEMENTED | Métodos numéricos / localización de eventos |
| Convergencia del cierre | Refinamiento max_step 1/.5/.25 s | Verificada hasta cierre; no extrapolable a E/F/G | NUMERICALLY_VERIFIED | Verificación numérica |
| .27 algebraica frente a .28 diferencial y fricción | Santos p.37–38 y sistema Tabla 5.1 | `f_B` fijo B→E; deriva .27 máxima 0.000454 Pa; correlación numérica de `f_B` no publicada | NUMERICALLY_VERIFIED / SOURCE_MISSING | Cierres de momento / limitaciones metodológicas |
| Métricas de operación/ciclo completo | Definición A→H, contrato API M1.7 | Duración parcial explícita; estimaciones diarias nulas | IMPLEMENTED | Resultados de software / límites de uso |
| Plausibilidad y validación externa | Perfil Gabriel Torrejon y objetivos de validación | No realizada validación de campo ni certificación completa del caso Santos | DRAFT | Validación, discusión y conclusiones futuras |

Puede redactarse ahora: trazabilidad, ecuaciones, convenciones, mapa de estado,
pruebas y alcance del bloqueo. Deben permanecer pendientes: E compatible, F/G
físicos, ciclo A→H, desempeño diario y conclusiones de optimización. Los valores
M1.6 se presentan solo como regresión histórica incompatible. Ninguna fila
alcanza REFERENCE_VALIDATED o FIELD_VALIDATED.
