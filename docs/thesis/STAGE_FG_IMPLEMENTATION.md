# Implementación Santos F→G — reconciliación Milestone 1.5

Estado: **IMPLEMENTED / NOT_READY_FOR_GH**. Alcance exclusivo: Santos Model I,
etapa 4.3. No contiene G→H ni multiciclo.

## Ecuaciones

La implementación conserva 4.1.89, 4.1.94, 4.1.97, 4.1.107 y 4.1.108;
4.1.24–25 y 4.1.95–4.1.103 aportan geometría, retorno de película, EOS,
momento y velocidades. El estado SI es

`[rho_gt3, P_t3, P_t1, h_l, y, V_return, V_res, m_g,out]`.

`q_res` dejó de ser constante. Cada RHS evalúa
`q_r=PI(P_r-P_wb)`, `P_wb=P_t1+rho_l g(H_w-H_gv)`, mediante
`gli.reservoir`. El signo bruto se conserva.

## Mapa F

Masa de gas, película y ledgers se transfieren por identidad. E→F representa
presión/densidad media; 4.3 requiere el extremo inferior, por lo que 4.1.96 y
4.1.101 transforman la representación conservando masa. Esta transformación
eleva `P_t1/P_wb` lo suficiente para producir `P_wb>P_r` al inicio de FG. El
resultado se clasifica como IPR inválida, no se recorta.

## Evento G corregido

El único evento terminal es

`R_G=P_t3-P_ts-rho_g g(H_gv-h_l)=0`, dirección `-1`.

Es el límite `v_g=v_gs=0` de 4.1.98–4.1.102. El anterior
`P_t1-P_to,initial=0` sigue como evento no terminal para diagnóstico.

## Experimento base

Radau, `rtol=1e-8`, `atol=1e-10`. La raíz legacy aparece a 101.846418 s
después de F, cuando el residual corregido aún vale aproximadamente +2.713
MPa. El residual corregido no cruza cero a 1200 s (+12.9118 Pa) ni a 10,000 s
(+1.49808e-5 Pa). No se encontró raíz múltiple ni primera raíz corregida.

La IPR comienza en `-2.10549e-4 m3/s` y vuelve a signo productor cerca de
32.737 s. A 10,000 s los balances normalizados son aproximadamente `2.59e-12`
gas y `1.14e-13` líquido. La ausencia de G y la IPR inválida son bloqueos
físicos, no fallos de conservación.

## Decisión

No se fuerza raíz, no se cambia fricción, no se sustituye el evento legacy y no
se inicia G→H desde el horizonte de seguridad. Véanse
`G_EVENT_RECONCILIATION.md`, `RESERVOIR_INFLOW_MODEL.md` y
`MILESTONE_1_5_REPORT.md`.
