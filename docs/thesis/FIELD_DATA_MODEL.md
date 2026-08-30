# Modelo de datos para referencias y pozos reales

Objetivo: aceptar múltiples pozos sin introducir `if well_id == ...` en la física. La arquitectura debe ser:

`dataset crudo → lector/adaptador → WellDefinition validado en SI → GLIParameters → mismo motor físico`

## 1. WellDefinition mínimo

`GLIParameters` ya es una buena estructura interna. Se propone envolverla con identidad, reservorio y procedencia:

```python
@dataclass(frozen=True)
class WellDefinition:
    well_id: str
    geometry: WellGeometry
    reservoir: ReservoirDefinition
    fluids: FluidDefinition
    installation: GLIInstallation
    operating: OperatingDefinition
    provenance: ProvenanceManifest
```

### WellGeometry

- profundidad de perforaciones y GLV;
- profundidad/longitud de tubing y casing;
- ID/OD de tubing, ID de casing y áreas anulares;
- datum y convención vertical.

### ReservoirDefinition

- presión estática y fecha/profundidad de referencia;
- temperatura;
- modelo IPR (`linear_pi`, Vogel u otro respaldado);
- PI/parámetros y unidades originales;
- rango de validez.

### FluidDefinition

- API/densidad de aceite, BSW, densidad de agua;
- gravedad específica del gas;
- viscosidades, tensión superficial, PVT/compresibilidad disponibles;
- temperatura y presión asociadas a cada medición.

### GLIInstallation

- tipo, profundidad, puerto/asiento, coeficiente de descarga y setpoints de GLV;
- válvula motora, área/Cv y lógica de control;
- separador/línea superficial si sus pérdidas se modelan.

### OperatingDefinition

- presión superficial de producción;
- presión/volumen/tiempo de inyección;
- frecuencia o temporización de controles;
- restricciones conocidas.

### ProvenanceManifest

Por campo: valor original, unidad, fuente, página/tabla o instrumento, fecha, calidad y transformación. Clasificar cada dato como `MEASURED`, `SOURCE_DEFINED`, `INFERRED`, `CALIBRATED` o `ASSUMED`.

## 2. Estructura de carpetas propuesta

```text
data/
  reference/
    santos_base/
      metadata.json
      well.json
      operating_points.csv
      observations_dynamic.csv
      observations_cycles.csv
  field/
    <well_id>/
      metadata.json
      well.json
      operating_points.csv
      observations_dynamic.csv
      observations_cycles.csv
      quality_flags.csv
```

No crear archivos de pozos ficticios como si fueran observaciones. Para pruebas se usarán fixtures bajo `tests/fixtures/synthetic/`, marcados inequívocamente `SYNTHETIC_TEST_ONLY`.

## 3. metadata.json mínimo

- `schema_version`, `dataset_id`, `well_id`, nombre anonimizado si aplica;
- propietario/licencia/permiso y restricciones de publicación;
- fuente bibliográfica o sistema de adquisición;
- zona horaria, datum, convención de profundidad;
- periodo, frecuencia de muestreo y cobertura;
- unidades originales y política de conversión SI;
- instrumentos, incertidumbre/resolución si se conoce;
- reglas de limpieza y flags;
- propósito permitido: reproducción, calibración o validación;
- partición temporal y hash del archivo fuente.

## 4. Tablas observacionales

### observations_dynamic.csv — nivel A

Columnas largas recomendadas: `timestamp`, `cycle_id`, `variable`, `value`, `unit`, `depth_m`, `quality_flag`, `instrument_id`, `uncertainty`, `source_row`.

Variables candidatas: presión tubing/casing superficie, presión fondo, caudal de gas inyectado, caudal líquido, señal de apertura/cierre, niveles/posición si existen.

### observations_cycles.csv — nivel B

`cycle_id`, inicio/fin, tiempos A…H si son observables, gas inyectado, líquido producido, volumen aportado estimado, duración, presión mínima/máxima, fallback estimado, calidad.

### operating_points.csv — nivel C

Promedios diarios/por campaña: presiones, inyección diaria, líquido/aceite/agua diarios, ciclos por día, BSW, uptime, configuración de válvula.

## 5. Capability levels

- **A — dynamic:** señales temporales suficientes para comparar trayectorias y eventos.
- **B — cycle:** totales y tiempos por ciclo; valida indicadores del ciclo, no estados instantáneos.
- **C — aggregate:** promedios diarios/mensuales; solo permite comparación agregada.
- **NONE:** metadatos insuficientes o calidad no aceptable.

El software debe inferir y reportar el nivel, variables faltantes y métricas permitidas. Un dataset nivel C nunca debe producir la etiqueta “validación transitoria”.

## 6. Adaptadores

Crear lectores separados por formato/fuente, por ejemplo `SantosAdapter`, `FieldCsvAdapter`, sin lógica física. Responsabilidades:

1. validar schema y unidades;
2. convertir a SI una sola vez;
3. comprobar geometría y rangos básicos;
4. resolver alias de columnas;
5. construir `WellDefinition` y `ObservationSet`;
6. emitir un manifiesto de transformaciones y warnings.

El motor solo recibe tipos canónicos. No debe conocer nombres de CSV, unidades de campo ni identificadores de pozos.

## 7. Datos Santos disponibles y faltantes

Disponibles: geometría/base de pozo, presión estática, PI, API, gravedades, BSW, presiones superficial/compresor, temperatura y profundidad de GLV; curvas/tablas seleccionadas ya digitalizadas.

Faltantes o incompletos para un caso totalmente trazado: geometría/datasheet detallado de válvulas, incertidumbres, series crudas, reglas exactas de digitalización y algunos coeficientes/temperaturas usados como defaults. Deben permanecer `SOURCE_MISSING` o `ASSUMED`; no inferirse silenciosamente.

## 8. Pruebas

- round-trip y validación de schemas;
- conversión de cada unidad;
- rechazo de profundidades/diámetros inconsistentes;
- IPR evaluada con `P_wf`, no presión superficial;
- manifests y hashes reproducibles;
- capability level correcto con variables ausentes;
- datos sintéticos no accesibles como dataset de validación real;
- mismo `WellDefinition` produce mismos `GLIParameters` independientemente del formato de origen.
