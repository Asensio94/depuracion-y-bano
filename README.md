# Depuración y baño

¿A dónde va lo que tiras? Esta web marca las aglomeraciones urbanas que, según lo que la propia España informa a la Agencia Europea de Medio Ambiente, no recogen o no depuran sus aguas residuales como pide la Directiva 91/271/CEE. Para cada una dice qué le falta: colector, tratamiento secundario o tratamiento más riguroso. Después sigue cada vertido río abajo hasta las zonas de baño y enseña su clasificación. Web: <https://asensio94.github.io/depuracion-y-bano/>.

En 2018 el Tribunal de Justicia de la UE condenó a España a pagar multa por las depuradoras que seguía sin construir (asunto C-205/17): 12 millones de euros de una vez y 10,95 millones por cada semestre de retraso.

## Cómo funciona

1. **Lo que España declara.** De Discodata, el servicio SQL de la AEMA, se descarga el último informe de España sobre la directiva (Waterbase UWWTD). Contiene las aglomeraciones, las depuradoras, qué parte de la carga de cada aglomeración va a cada depuradora, los puntos de vertido y el programa de obras del artículo 17. Hoy es el informe de 2022, con datos a 31 de diciembre de 2022, entregado el 30 de junio de 2024.
2. **Las reglas de la directiva.** A cada aglomeración se le aplican los artículos 3, 4 y 5 ([`compliance.py`](wastewater/compliance.py)):
   - **Colector**: al menos el 98 % de la carga debe ir al colector o a un sistema individual, y no más del 2 % puede verterse sin tratar.
   - **Tratamiento secundario**: obligatorio desde 2.000 h-e si vierte a aguas continentales o estuarios, y desde 10.000 h-e si vierte al mar.
   - **Tratamiento más riguroso** (eliminar nitrógeno o fósforo): obligatorio desde 10.000 h-e en zona sensible.
   - **Rendimiento**: si la depuradora tiene el tratamiento pero sus controles no cumplen, la carencia es de rendimiento.

   Lo que pide la refundición de 2024 (Directiva 2024/3019) se enseña aparte: a las depuradoras de más de 150.000 h-e, eliminar nitrógeno y fósforo en 2039 y tratamiento cuaternario en 2045.
3. **Las zonas de baño.** Del catálogo de la AEMA se toma la última publicación de «Status of bathing water», hoy la temporada 2025, publicada el 2 de junio de 2026. Se guardan las cuatro últimas temporadas de España. De Discodata se toma además el registro de zonas, con la masa de agua de cada una.
4. **El camino del agua** ([`link.py`](wastewater/link.py)). Cada punto de vertido se une a las zonas de baño de tres maneras:
   - **Río abajo**: el vertido y la zona están a menos de 2 km de la red HydroRIVERS, y siguiendo la red desde el vertido se llega a la zona en menos de 30 km.
   - **Por la desembocadura**: el río llega al mar en menos de 30 km y la zona de costa o de transición está a menos de 5 km de la desembocadura.
   - **Misma masa de agua**: en la costa, los estuarios y los embalses, el vertido y la zona declaran la misma masa de agua y están a menos de 5 km.
5. **La página y las señales.** Se publican un HTML autocontenido con mapa y tablas y `docs/signals.json` para [Estado de las IBA](https://asensio94.github.io/estado-iba/). Las señales son de dos tipos: `wastewater`, una por aglomeración con carencias, y `bathing_water`, una por zona insuficiente.
6. **El bot.** Cada lunes comprueba si hay un informe o una clasificación nuevos ([`weekly.yml`](.github/workflows/weekly.yml)). Solo entonces descarga, enlaza, publica y hace commit en `main`. GitHub Pages sirve `main:/docs`.

## Contraste

- **Sentencia C-205/17.** España seguía pagando multa en 2022 por cuatro aglomeraciones: Barbate, Matalascañas, Alhaurín el Grande y Güímar. Las cuatro salen aquí con carencias. Ninguna de las nueve que ya se daban por resueltas aparece con carencias: Tarifa, Nerja, Gijón-Este, Estepona, Noreste (Valle Guerra), Benicarló, Peñíscola, Vigo y Santiago. La página recalcula este contraste con cada informe.
- **Zonas de baño.** Hay 2.296 zonas en 2025: 1.989 excelentes, 205 buenas, 39 suficientes, 48 insuficientes y 15 sin clasificar. Coinciden con la publicación de la AEMA: el 97,3 % llega al menos a «suficiente», la misma cifra que da el informe de Sanidad de 2025.
- **Zonas insuficientes sin vertido enlazado.** 31 de las 48 no tienen ningún vertido de aglomeración enlazado. Se repitió el enlace con un recorrido de 300 km en lugar de 30 km. Aun así, casi todas son ríos de interior sin ninguna aglomeración del informe aguas arriba (Jerte, Bullaque, Órbigo…). Ahí la carga vendrá de pueblos de menos de 2.000 h-e o de la ganadería.

## Límites

- Es un indicio, no un veredicto. La Comisión evalúa con plazos, excepciones y aclaraciones que no están en el informe, y su evaluación no se publica como datos abiertos.
- Solo entran las aglomeraciones de 2.000 h-e o más, porque las pequeñas no se informan. Según el [Nomenclátor del INE](https://www.ine.es/nomen2/index.do) de 2025, 1,7 millones de personas viven en diseminado y 6,4 millones en núcleos de menos de 2.000 habitantes; no hay datos abiertos nacionales sobre cómo depuran. La EIEL del Ministerio de Política Territorial lo recoge por núcleo, pero solo unas 19 provincias la publican con datos y su licencia es CC BY-NC-SA.
- El informe llega con dos años de retraso.
- No hay un campo para el tratamiento cuaternario. Se aproxima con la ozonización declarada.
- HydroRIVERS (unos 500 m de resolución) no tiene los arroyos pequeños, y un punto puede caer en el tramo vecino. En la costa la distancia es en línea recta y no tiene en cuenta las corrientes.
- No entran los vertidos industriales ni los alivios de tormenta.

## Pendiente

- **Censo Nacional de Vertidos (MITECO).** Tiene los vertidos autorizados, también los industriales, pero su descarga está protegida por un captcha (ALTCHA). No se automatiza; habría que pedir un acceso abierto.
- **Náyade (Sanidad).** Tiene las fechas de temporada, los puntos de muestreo y los perfiles de cada zona de baño. Su web funciona con formularios de sesión. Queda para una versión 2.

## Uso

```bash
pip install -r requirements.txt
python -m wastewater.cli fetch    # informe UWWTD y zonas de baño (AEMA)
python -m wastewater.cli link     # descarga HydroRIVERS a .cache/ (68 MB) y enlaza vertidos con zonas
python -m wastewater.cli page     # docs/index.html y docs/signals.json
python -m wastewater.cli all      # las tres
python -m wastewater.cli check    # sale con 0 si alguna fuente tiene una versión nueva
python -m pytest -q
```

## Datos que se guardan

| Fichero | Contenido |
|---|---|
| `data/uwwtd/agglomerations.json` | Aglomeraciones: carga, % recogido, % en sistemas individuales, % sin tratar, punto |
| `data/uwwtd/plants.json` | Depuradoras: tratamiento, resultado de los controles, punto |
| `data/uwwtd/plant_agglomerations.json` | Qué parte de cada aglomeración llega a cada depuradora |
| `data/uwwtd/discharges.json` | Puntos de vertido: tipo de agua, zona sensible, masa de agua, punto |
| `data/uwwtd/programme.json` | Programa del artículo 17: motivo, fecha prevista e inversión |
| `data/uwwtd/report.json` | Año, fecha de situación y fecha de entrega del informe |
| `data/bathing/status.json` | Clasificación de cada zona de baño en las cuatro últimas temporadas |
| `data/bathing/zones.json` | Registro de zonas de baño con su masa de agua |
| `data/bathing/release.json` | Publicación de la AEMA de la que salen las clasificaciones |
| `data/links.json` | Enlaces vertido → zona de baño: método y km |
| `data/versions.json` | Versiones de las fuentes ya publicadas (para el bot) |
| `docs/index.html` | La web |
| `docs/signals.json` | Señales para Estado de las IBA |

Una línea por registro, ordenadas por código: un informe nuevo se ve como un diff limpio.

## Fuentes y licencias

- [Waterbase UWWTD](https://www.eea.europa.eu/en/datahub/datahubitem-view/6244937d-1c2c-47f5-bdf1-33ca01ff1715) y [estado de las aguas de baño 2025](https://sdi.eea.europa.eu/catalogue/srv/eng/catalog.search#/metadata/070d9baa-448d-4168-8514-7dadb3ad876d), Agencia Europea de Medio Ambiente. Reutilización libre citando la fuente.
- [HydroRIVERS v1.0](https://www.hydrosheds.org/products/hydrorivers): Lehner, B., Grill, G. (2013), *Hydrological Processes* 27(15): 2171–2186. Licencia HydroSHEDS, que permite el uso no comercial y comercial citando la fuente. Solo se publican los enlaces derivados, no la red.
- Municipios: IGN, empaquetados por [es-atlas](https://github.com/martgnz/es-atlas).
- Mapa base: © colaboradores de OpenStreetMap.
- Código: MIT. Datos propios (`data/links.json`, `docs/signals.json`): CC BY 4.0.

Forma parte de un conjunto de proyectos hermanos: [Observatorio de alegaciones](https://asensio94.github.io/observatorio-alegaciones/), [Vigía de incendios](https://asensio94.github.io/vigia-incendios/), [Centinela Natura](https://asensio94.github.io/centinela-natura/), [Vigilancia de humedales](https://asensio94.github.io/vigilancia-humedales/), [Sub Nocte](https://asensio94.github.io/sub-nocte/), [Riesgo de tendidos para aves](https://asensio94.github.io/riesgo-tendidos-aves/), [Grafo de promotores](https://asensio94.github.io/grafo-promotores/), [Cartera de las cotizadas](https://asensio94.github.io/cartera-cotizadas/), [Cuaderno de campo](https://asensio94.github.io/cuaderno-campo/), [Caudal ecológico](https://asensio94.github.io/caudal-ecologico/) y [Estado de las IBA](https://asensio94.github.io/estado-iba/).
