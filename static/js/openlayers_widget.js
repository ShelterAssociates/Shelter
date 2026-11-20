/* Starts the admin geometry map widgets rendered by component/openlayers.html. */
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".ol-map-widget").forEach(function (div) {
        var data = div.dataset;
        var baseLayer = new ol.layer.Tile({
            source: new ol.source.XYZ({
                attributions: "NASA Worldview",
                maxZoom: 8,
                url: "https://map1{a-c}.vis.earthdata.nasa.gov/wmts-webmerc/" +
                     "BlueMarble_ShadedRelief_Bathymetry/default/%7BTime%7D/" +
                     "GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg"
            })
        });
        var widget = new MapWidget({
            base_layer: baseLayer,
            geom_name: data.geomName,
            id: data.widgetId,
            map_id: data.widgetId + "_map",
            map_options: {},
            map_srid: Number(data.mapSrid),
            name: data.name
        });
        window[data.module] = widget;
        var clear = div.querySelector(".ol-clear-features");
        if (clear) {
            clear.addEventListener("click", function (event) {
                event.preventDefault();
                widget.clearFeatures();
            });
        }
    });
});
