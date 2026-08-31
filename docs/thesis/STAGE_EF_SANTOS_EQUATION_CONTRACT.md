# Contrato de ecuaciones Santos para E→F (estágio 4.2)

## Alcance y fuente primaria

Este contrato transcribe y fija la implementación de la fase II de
descompresión del método GLI convencional de Santos. La fuente primaria es la
disertación local de Odair Geraldo dos Santos, capítulo 4, páginas impresas
52–57, y capítulo 5, páginas impresas 117 y 131.

La Tabla 4.1 define el estágio 4.2 desde el cierre de la válvula de *gas lift*
hasta `v_f = 0`. La Tabla 5.1 declara siete variables para el sistema:

`h_l, P_t1, P_t3, rho_g, v_f, v_g, y`.

Las Tablas 5.6 y 5.7 asignan al ejemplo base los tramos `E→F = fase II` y
`F→G = fase III`, y dicen explícitamente que la fase I no existe porque la GLV
se cierra inmediatamente antes de que la base de la golfada llegue a la
superficie.

No son variables físicas adicionales del sistema los acumulados de gas
descargado, líquido producido, retorno/fallback o entrada del reservorio. Son
ledgers de procedencia integrados en paralelo.

## Convenciones y geometría

- Eje vertical positivo hacia la superficie.
- `v_f > 0` y `v_g > 0` indican flujo ascendente.
- `y` es el espesor radial de película, en m.
- `r = D/2`, `A_B = pi*(r-y)^2` y `A_f = A_t-A_B`, en m².
- `z_v = H_gv` es la profundidad de la GLV, en m.
- `h_l` es la altura de la columna líquida inferior medida desde la GLV hacia
  arriba, en m; la longitud de gas es `L_g = z_v-h_l`.
- `rho_g` es la densidad media de la columna de gas. Con la aproximación lineal
  de Santos, `rho_g = (rho_gt3+rho_gs)/2` y `v_gs = 2*v_g` (4.1.96 y 4.1.102).
- `P_t1` está a profundidad de GLV; `P_t3` está en el tope de la columna
  líquida; `P_ts` es la frontera superficial fija. Todas son Pa absolutas.
- La GLV está cerrada durante todo E→F: flujo de gas por GLV igual a cero.
- `q_res = PI*(P_r-P_wb)` conserva su signo; `P_wb =
  P_t1+rho_l*g*(H_w-H_gv)`. No se recorta flujo negativo.

## Estado inicial E y frontera F

Santos indica que, desde el cierre de la GLV, el fluido de formación empieza a
acumularse en la columna de producción y que el filme no se incorpora a esa
columna (página impresa 52). Como en el ejemplo base no existe la fase I y E es
simultáneo, a la resolución del modelo, con ese cierre, la condición conservadora
es `h_l(E)=0`. Por 4.1.88, `P_t3(E)=P_t1(E)`.

Las magnitudes con memoria `P_t1`, `m_g`, `v_g`, `v_f`, `y`, película y ledgers
deben llegar por identidad desde el terminal D→E. La densidad media inicial
debe satisfacer simultáneamente:

1. inventario: `rho_g(E)=m_g(E)/(A_B(E)*(z_v-h_l(E)))`;
2. EOS espacial: `rho_g(E)=0.5*(P_t3(E)/K_t3+rho_gs)`, donde
   `K_t3=Z_t3*R*T_t3/M`.

Si ambas relaciones no coinciden dentro de tolerancia escalada, no existe un
estado inicial E que preserve a la vez masa, presión, geometría, hidrostática y
EOS. Se prohíbe proyectar una de ellas. La ruta debe declararse
`NOT_SOURCE_CERTIFIED_A_TO_F`.

F es exclusivamente el cruce descendente `v_f=0`. No se utiliza tolerancia
asintótica ni otro evento sustituto.

## Contratos ecuación por ecuación

### 4.1.76 — masa del filme

- Volumen de control: película anular de longitud `z_v`.
- Variables: `y`, `v_f`; algebraicas: `A_f`, `A_B`.
- Ecuación y representación Python:

  `2*pi*z_v*(r-y)*dy + v_f*A_f = 0`

  `dy = -v_f*A_f/(2*pi*z_v*(r-y))`

- Unidades de cada término: m³/s.
- No contiene `q_res`: Santos fija a cero la alimentación al filme en fase II.

### 4.1.80 — momento del filme

- Volumen de control: película anular completa; interfaz gas–filme solamente en
  `z_v-h_l`.
- Variables: `v_f, y, rho_g, v_g, h_l, P_t1`.
- Algebraicas: factores de fricción `f_f`, `f_g`, áreas y `dy`.
- Residuo implementado, con unidades m³/s²:

  `A_f*(dv_f+g)`
  `+2*pi*(r-y)*(v_f*dy - f_g*rho_g*v_g**2*(z_v-h_l)/(8*rho_l*z_v))`
  `+f_f*v_f**2*pi*r/4`
  `-A_f*(P_t1-P_ts)/(rho_l*z_v) = 0`

- En E se recibe `v_f` de D→E. En F se impone el cruce descendente `v_f=0`.

### 4.1.83 — masa de la columna de gas

- Volumen de control: núcleo de gas `A_B*(z_v-h_l)`.
- Variables: `rho_g, v_g, h_l, y`; algebraicas: `rho_gs`, `v_gs=2*v_g`.
- Residuo, kg/(m² s):

  `(z_v-h_l)*(drho_g - 2*rho_g*dy/(r-y))`
  `-rho_g*dh_l + rho_gs*v_gs = 0`

- El inventario reportado es siempre `m_g=rho_g*A_B*(z_v-h_l)`, nunca
  `rho_g*A_B*z_v`.

### 4.1.84 — momento de la columna de gas

- Volumen de control: núcleo gaseoso entre el tope de la columna líquida y la
  superficie.
- Variables: `P_t3, rho_g, v_g, h_l`.
- Residuo en Pa/s:

  `dP_t3`
  `-(f_g*v_g**2*(z_v-h_l)/(2*D)+(z_v-h_l)*g)*drho_g`
  `-(f_g*rho_g*v_g*(z_v-h_l)/D)*dv_g`
  `+(f_g*rho_g*v_g**2/(2*D)+rho_g*g)*dh_l = 0`

- La implementación resuelve localmente 4.1.83 y 4.1.84 como sistema lineal
  para `drho_g` y `dv_g`, después de sustituir 4.1.90, y registra su condición.
  No se usa una ecuación genérica de agotamiento/Darcy.

### 4.1.87 — masa de la columna líquida inferior

- Volumen de control: columna líquida inferior `V_lower=A_B*h_l`.
- Variables: `h_l, y, P_t1`; algebraica: `q_res(P_t1)`.
- Residuo en m³/s:

  `A_B*dh_l - 2*pi*(r-y)*h_l*dy - q_res = 0`

- Representación:

  `dh_l=(q_res+2*pi*(r-y)*h_l*dy)/A_B`

- El ledger `V_res=integral(q_res dt)` no reemplaza `A_B*h_l`.

### 4.1.88/4.1.89 — acoplamiento hidrostático

- Volumen de control: columna líquida inferior.
- Relación algebraica en Pa:

  `P_t1-P_t3-rho_l*g*h_l = 0`

- Relación diferencial en Pa/s:

  `dP_t1-dP_t3-rho_l*g*dh_l = 0`

- Representación: `dP_t1=dP_t3+rho_l*g*dh_l`.

### 4.1.90 — EOS de la densidad media

- Cierre del gas real en el extremo `t3`, con superficie fija.
- Residuo diferencial en Pa/s:

  `dP_t3-2*(Z_t3*R*T_t3/M)*drho_g = 0`

- Cierre algebraico integrado en Pa:

  `P_t3=K_t3*(2*rho_g-rho_gs)`.

## Ledgers y balance global

- `dV_res/dt=q_res`, con valor inicial recibido de D→E.
- `dV_prod/dt=v_f*A_f` durante E→F.
- `dV_fallback/dt=0` en fase II según la hipótesis explícita de Santos.
- `dm_g,out/dt=rho_gs*(2*v_g)*A_B`.
- Inventario físico líquido: `V_film=A_f*z_v` y `V_lower=A_B*h_l`.
- Balance a reconciliar:

  `V_film + V_lower + V_prod + V_fallback - V_res = constante`.

- Balance de gas:

  `rho_g*A_B*(z_v-h_l) + m_g,out = constante`.

## Auditoría del estado E del caso Santos 50/70/80

En el HEAD previo al hito 1.6, el terminal D→E corregido entrega:

| Magnitud | Valor |
|---|---:|
| `m_g(E)` | 103.6150057 kg |
| `P_t1(E)` | 4.9536310 MPa abs |
| `h_l(E)` por fuente | 0 m |
| `rho_g(E)` por masa/geometría | 40.3394280 kg/m³ |
| `rho_g(E)` por 4.1.88 + EOS | 23.3773629 kg/m³ |
| desajuste relativo | 0.7255765 |

El volumen requerido por la EOS para conservar esa masa excede incluso el
volumen geométrico máximo `A_B*z_v`. Equivalentemente, usar la densidad de masa
en la EOS produciría `P_t3>P_t1`, lo que exigiría `h_l<0`. Por tanto, el estado
E actual no puede inicializar exactamente Stage 4.2 sin alterar una cantidad
con memoria. Esta incompatibilidad es de frontera D→E/E→F y debe bloquear la
certificación de fuente; no autoriza ajuste de coeficientes ni reconstrucción.
