# Estrategia de optimización operacional

## 1. Precondiciones

No implementar un optimizador productivo hasta cumplir:

1. A→H y ciclos sucesivos estables;
2. IPR físicamente correcta;
3. modelo calibrado y congelado;
4. validación independiente dentro del dominio;
5. restricciones y costos/beneficios aportados por fuente o usuario.

La sensibilidad actual es exploración A→F, no optimización.

## 2. Qué optimiza Santos

El capítulo 8 no propone maximizar líquido sin costo. Construye una frontera operacional ordenada por gas y analiza el incremento marginal gas/líquido. Para un sistema abierto, Santos usa el criterio económico `dq_gas/dq_oil < 1000`; para el ejemplo con BSW 50%, lo expresa como `dq_gas/dq_liq < 500`. En sistemas con recompresión el umbral cambia con el costo energético local.

Por ello son defendibles dos modos:

### Modo A — Pareto técnico

Maximizar líquido/aceite estabilizado y minimizar gas inyectado, fallback y/o duración, sujeto a restricciones. Entrega frontera de Pareto sin inventar precios.

### Modo B — económico

Maximizar valor neto por tiempo:

`revenue(oil, water handling) − gas/energy cost − penalties`

Requiere precios, costo de compresión/reinyección, tratamiento de agua y horizonte. Esos valores no están en los repositorios: **SOURCE_MISSING**.

No elegir silenciosamente “máxima producción” como objetivo final; puede seleccionar un régimen ineficiente o inseguro.

## 3. Variables de decisión candidatas

Separar operación de diseño:

### Operación

- presión de inyección dentro de capacidad de compresor;
- duración/volumen de gas por ciclo;
- tiempo cerrado/alimentación y frecuencia;
- setpoints de apertura/cierre si son controlables.

### Diseño/instalación

- diámetro/asiento de GLV;
- profundidad de válvula;
- diámetro de tubing.

No mezclar decisiones de workover con controles diarios en una misma recomendación sin modelar sus costos y discreción. BSW, API, presión de reservorio e IPR son escenarios/incertidumbres, no variables manipulables.

## 4. Respuestas y restricciones

Respuestas por régimen estabilizado:

- líquido/aceite por ciclo y por día;
- gas inyectado por ciclo/día;
- duración/frecuencia;
- fallback y eficiencia gas-líquido;
- presiones/velocidades máximas;
- número de ciclos hasta estabilizar.

Restricciones candidatas: presión de compresor/tubing/casing, capacidad de válvulas, frecuencia máxima, dominio de correlaciones, no cavitación/flujo inverso no modelado, balance aceptable y convergencia. Valores numéricos de límites deben venir de instalación, normativa o asesor: **SOURCE_MISSING**.

## 5. Differential Evolution

Es adecuado como candidato porque el mapa decisión→respuesta es no suave por eventos, cambios de régimen y fallos. Ventajas: no requiere gradiente y maneja bounds. Riesgos: muchas simulaciones, variabilidad estocástica y posibilidad de optimizar artefactos numéricos.

Contrato mínimo:

- variables normalizadas y bounds trazables;
- seed y versión SciPy registradas;
- población/iteraciones/convergencia reportadas;
- penalizaciones dominantes para solver fallido o restricción física;
- cache y paralelismo reproducible;
- reevaluar óptimos con tolerancias más estrictas y perturbaciones locales;
- múltiples seeds y baseline (grid/estrategia actual);
- nunca aceptar un óptimo que sale del dominio validado.

## 6. Robustez e incertidumbre

La recomendación debe sobrevivir incertidumbre de PI, presión de reservorio, BSW, propiedades y coeficientes calibrados. Opciones:

- optimización robusta sobre escenarios/ensamble;
- restricción probabilística cuando haya distribuciones justificadas;
- ranking por peor caso o regret;
- Pareto con bandas de incertidumbre.

No asignar distribuciones inventadas. Sin incertidumbre cuantificada, usar escenarios explícitos etiquetados como supuestos.

## 7. Experimentos mínimos

1. Reproducir sensibilidad Santos para volumen de gas, asiento GLV, longitud inicial y relación de presiones.
2. Validar monotonías/localizar cambios de régimen.
3. Construir Pareto gas–líquido y gas–aceite por operación estabilizada.
4. Comparar DE contra grid/Latin hypercube y política base.
5. Reevaluar puntos candidatos con solver estricto.
6. Prueba holdout operacional y escenarios de incertidumbre.
7. Reportar también soluciones inviables/no convergentes.

## 8. Archivos futuros

- `src/gli_optimization/problem.py`
- `src/gli_optimization/objectives.py`
- `src/gli_optimization/constraints.py`
- `src/gli_optimization/differential_evolution.py`
- `src/gli_optimization/pareto.py`
- `src/gli_optimization/report.py`
- `tests/optimization/test_problem_contract.py`
- `tests/optimization/test_reproducible_seed.py`
- `tests/optimization/test_constraint_penalties.py`
- `tests/optimization/test_strict_reevaluation.py`

La salida debe ser una recomendación condicionada al modelo, datos, dominio, costos y restricciones, nunca una “configuración óptima universal”.
