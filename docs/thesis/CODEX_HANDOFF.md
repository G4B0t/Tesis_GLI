# Handoff — M1.7R

- Branch: `feature/gli-thesis-completion`.
- HEAD de inicio: `bdbe5fe1b45ab56ea9d4a6247d05069e5e7502eb`.
- No se hizo commit, push, merge, cambio de rama, GitHub ni Stage 4.2.
- Dictamen: `BLOCKED_BY_SOURCE`.

## Hecho

- Centralizada la masa GLV Santos 4.1.13/.15 en `valves.py` para la ruta
  científica B→C, C→D y D→E; el proxy sólo permanece como referencia histórica.
- Aplicada extensión crítica continua y pruebas independientes de ambos
  regímenes.
- Congelado `f_B` desde B hasta E para que 4.1.28 sea consistente con 4.1.27.
- Añadido auditor reproducible M1.7R, JSON, informe, matriz de trazabilidad,
  mapa de escritura y pruebas independientes.

## Resultado disponible

- D = 514.485952492 s; GLV abierta en D = 0.193529835526 kg/s.
- Cierre GLV = 29.534199902 s tras D; quedan 178.700407070 m de golfada.
- E no existe; downstream no se ejecutó.
- `f_B=0.1278397857624769`; deriva .27 = 0.000453997 Pa.

## Bloqueo

Santos revisado no publica la correlación numérica de `f_B` y no especifica
una transición ejecutable para el intervalo material entre cierre GLV y E.
No calibrar ni fabricar E. Para continuar hace falta localizar evidencia
primaria de ambos cierres o una instrucción científica explícita y aprobada.

## Validación pendiente antes de commit

Ejecutar Black/Ruff sólo sobre Python modificado desde el HEAD indicado,
después prueba enfocada y una sola corrida completa de pytest. Luego revisar
el diff y pedir autorización explícita antes de commit/push.
