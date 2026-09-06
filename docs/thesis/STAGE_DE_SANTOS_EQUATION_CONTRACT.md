# Contrato Santos Stage 3 D→E — Milestone 1.7

Contrato creado antes de modificar el RHS. Fuente primaria: Santos 1997,
páginas impresas 29, 31–46, 47–52, 117 y 131 (PDF: impresa + 19).
Lectura visual directa de las ecuaciones y Tablas 4.1, 5.1, 5.6 y 5.7.
El Perfil Gabriel Torrejon define el alcance académico (conservación,
implementación Python, verificación antes de calibración); no reemplaza Santos.

## Conjunto exacto y convenciones

Tabla 5.1, Stage 3: **4.1.6, .9, .17, .18, .19, .26, .28,
.32, .35, .40, .48, .50, .53**. Coincide con el conjunto solicitado.
Stage 2 eleva la golfada. Stage 3 la produce: su frontera superior queda en
`z_v`, la salida lleva `A_t*v_l`, y 4.1.46 se reemplaza por 4.1.53,
añadiendo `0.3*v_l**2` (K=0.6, sin calibración). Las demás relaciones permanecen.
`h_l` de 4.1.32/.40 se interpreta como desplazamiento cinemático del líquido
para calcular el flujo superficial; NO como una frontera que continúe subiendo
fuera del pozo. Se transporta el componente canónico y se reporta el tope
físico fijo `z_v`. El volumen producido satisface `dV_prod=A_t*v_l`.

Eje positivo ascendente, SI, presión absoluta. `r=D/2`,
`A_B=pi*(r-y)**2`, `A_f=A_t-A_B`, `L=z_v-h_B`.
Todos los estados con memoria se copian del vector canónico de C→D:
`mc,mg,rho_B,Pt1,vB,vf,y,mfilm,hB,hl,vl,Vgi,Vfb,Vprod`.
Las presiones algebraicas heredadas se evalúan como en D−, nunca se ajustan
para disminuir residuos. Se añade Pt2 como estado para integrar 4.1.28
literalmente, presiones/densidades casing, y ledgers de reservorio/GLV.

## Contratos por ecuación

En la tabla, `d` significa derivada temporal. Condiciones en D: identidad
para todas las variables indicadas; casing y Pt2 reciben los valores
algebraicos del terminal C→D. Fronteras comunes: motor cerrado, `P_ts` fijo,
GLV heredada abierta/cerrada y luego enclavada por fuerza cero descendente.
Los signos de transferencia son positivos casing→tubing y reservorio→filme.

| Ec. | Significado / volumen de control | Estados; algebraicas | Residuo Python planificado | Unidades | Frontera / evento |
|---|---|---|---|---|---|
| 4.1.6 | Masa/EOS anular, volumen fijo Vtc | mc,Pc1,Pc2; Ktc=Ztc RTtc/M | `Vtc*(dPc1+dPc2)/(2*Ktc)-dmc` | kg/s | motor=0; GLV interna |
| 4.1.9 | Flujo neto anular | mc; mgs,mgv | `dmc-mgs+mgv`, `mgs=0` | kg/s | cierre motor C heredado |
| 4.1.17 | Momento anular hidrostático | Pc1,Pc2; eta=exp(g*zv/Ktc) | `dPc2-eta*dPc1` | Pa/s | sin fricción/aceleración anular |
| 4.1.18 | EOS gas casing superior | Pc1,rhoc1; Kc1 | `dPc1-Kc1*drhoc1` | Pa/s | valor D− |
| 4.1.19 | EOS gas casing inferior | Pc2,rhoc2; Kc2 | `dPc2-Kc2*drhoc2` | Pa/s | valor D−; alimenta GLV |
| 4.1.26 | Masa burbuja AB*hB | rhoB,hB,y; AB,mgv | `AB*rhoB*dhB+AB*hB*drhoB-2*pi*(r-y)*rhoB*hB*dy-mgv` | kg/s | sin gas superficial antes de E |
| 4.1.28 | Momento burbuja, diferencial publicado | Pt2,Pt1,rhoB,vB,hB; fB | `dPt2-dPt1+(fB*vB**2*hB/(2*D)+hB*g)*drhoB+fB*rhoB*vB*hB*dVB/D+(fB*rhoB*vB**2/(2*D)+rhoB*g)*dhB` | Pa/s | Pt2 inicial de 4.1.27; f local como coeficiente |
| 4.1.32 | Cinemática del líquido | hl,vl | `dhl-vl` | m/s | en producción hl es desplazamiento, tope físico fijo |
| 4.1.35 | Masa filme móvil Af*hB | y,vf,hB,Pt1; qres | `2*pi*(r-y)*hB*dy+Af*vf-qres` | m3/s | qres alimenta filme en Stage 3, p.45 |
| 4.1.40 | Masa golfada | hl,hB,vf; At,AB,Af | `At*dhl-AB*dhB-Af*vf` | m3/s | equivale a .39 con .32/.33; salida At*vl |
| 4.1.48 | EOS burbuja en Pt1 | Pt1,rhoB; Kt1 | `dPt1-Kt1*drhoB` | Pa/s | p.43 rechaza deliberadamente usar media .47 |
| 4.1.50 | Relación empírica de velocidades | vB,vl; a | `dvB-a*dvl` | m/s2 | constante b heredada; .49/.51 |
| 4.1.53 | Momento golfada producida | vl,vf,vB,hB,Pt2; Pts,fl | `L*dvl+vl**2-(Af/At)*vf**2-(AB/At)*vB**2-(Pt2-Pts)/rhoL+g*L+fl*vl**2*L/(2*D)+0.3*vl**2` | m2/s2 | E: hB-zv=0; sin piso físico en L |

La masa de filme se integra geométricamente `dmfilm=rhoL*d(Af*hB)`;
fallback permanece en el filme (p.35), sin sumar un segundo inventario.
`dVres=qres(Pt1)`, `dMtransfer=mgv`, `dmg=mgv`, `dVgi=0`.
No se recorta IPR: `Pwb=Pt1+rhoL*g*(Hw-Hgv)`, `qres=PI*(Pr-Pwb)`.
La derivada de vf se obtiene diferenciando .39; vf llega por identidad.

### Cierres y límites de certificación

El código anterior de C→D usa `_gas_lift_mass_rate = Cd*Av*sqrt(2*rho_c2*(Pc2-Pt1))`.
Esto **no es** Thornhill–Craver 4.1.13/.15 (p.33):
`qgv=.04842*Cd*Av*Pc2/sqrt(dg*Tc2)*sqrt(2*k/(k-1)*(x**(2/k)-x**((k+1)/k)))`,
`mgv=qgv*rho_std`. La continuidad solicitada exige heredar el flujo de D−;
se conserva la mecánica existente y se cuantifica su defecto de fuente.
No se certificará todo A→E por pasar únicamente residuos de balances.
Cambiar solo la correlación después de D introduciría una discontinuidad
que no está prescrita por la fuente. Su reconciliación debe abarcar B→D.

4.1.28 omite `dfB/dt`; se integra la ecuación publicada con fB local y se
audita por separado el defecto algebraico de .27 si fB cambia. No se afirma
equivalencia entre diferenciar .27 con f variable y la ecuación publicada.
Análogamente .6 usa Ttc/Ztc medios: posibles offsets heredados de la
aproximación de casing anterior se reportan, no se proyectan.

## GLV closure relative to E in the Santos base case

**SOURCE_LIMITING_IDEALIZATION** para la frase de p.131: cierre
"inmediatamente antes" de E y ausencia de fase I. No define un delta t ni
autoriza imponer simultaneidad. Tabla 4.1 hace comenzar 4.1 en E y terminarla
al cerrar GLV: 4.1 NO es una fase para un intervalo pre-E con GLV cerrada.
Se descarta B de la pregunta del prompt. Stage 3 termina geométricamente en E.
La p.45 alimenta el filme durante Stage 3; p.52 alimenta una columna inferior
desde el cierre en fase II, cuya geometría presupone una columna de gas de
longitud completa. No hay sistema explícito para dos columnas líquidas
separadas por burbuja con cierre materialmente anterior a E.

Si el cierre resulta pre-E y separado materialmente, se clasifica la
transición **SOURCE_AMBIGUITY**, se registra el estado del cierre y se
detiene allí: no se inventa hl, no se fuerza E. Si E ocurre abierto,
hl inferior es cero porque la afluencia alimentó el filme; se requiere
fase I y se evalúa primero su EOS espacial por identidad. No se deja entrar
Stage 4.2 con GLV abierta. Si cierre y E coinciden a resolución numérica,
hl→0 es un límite documentado, nunca una condición universal del auditor.

## Tratamiento numérico de E

La ecuación física divide por `L=zv-hB`, exactamente. Se integra con Radau
en tiempo y eventos descendentes de fuerza GLV y de dominio
`L-max(1e-6,zv*rtol)=0`. Este segundo evento NO es E: produce
`E_LIMIT_NOT_LOCALIZED`, sin publicar un estado E. La base se bloquea por
fuente mucho antes de ese límite. No se implementó ni se verificó una
continuación unilateral a L=0; la convergencia disponible es la del cierre,
no la de E. Esta limitación queda explícita, sin certificar el tramo faltante.
No se usa `max(L,5)` ni otro largo físico mínimo en el RHS.

## Auditoría del código previo

| Item | M1.6 | Santos / decisión | Impacto |
|---|---|---|---|
| GLV en D | forzada cerrada | REPLACE: identidad C→D | evita discontinuidad de control |
| mgv(D) | cero | REPLACE: flujo heredado; auditar .13/.15 | transferencia interna real; proxy no certificable |
| mc | congelada | REPLACE: .6/.9 | presión anular evoluciona |
| mg | congelada | REPLACE: .26 | inventario evoluciona |
| Pc1,Pc2 | de mc congelada | REPLACE: .6/.17 | presión y fuerza continuas |
| Pt1 | .48 pero sin transferencia | KEEP EOS, REPLACE balance | no sustituir por .47 |
| rhoB | reconstruida en D | REPLACE: identidad canónica | conserva memoria |
| vB | integrado con a*dvl | KEEP | .50 |
| vf | recuperada por .39 en D | REPLACE: identidad, derivada .39 | conserva película |
| y | integrada | KEEP .35 | qres en filme |
| tope/base | tope fijo, base integrada | KEEP; desplazamiento auxiliar explícito | evento E físico |
| vl | Leff=max(L,5), sin pérdida gas correcta | REPLACE: .53 literal y Pt2 de .28 | elimina regularización física |
| qres | dinámico en filme | KEEP hasta cierre | ledger independiente |
| producido | max(At*vl,0) | REPLACE: At*vl firmado | balance sin clipping |

Los resultados y las limitaciones finales se documentan en MILESTONE_1_7_REPORT.md.
