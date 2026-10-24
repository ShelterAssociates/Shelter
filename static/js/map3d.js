/* 3D view of the Structure layer: MapLibre fill-extrusion over Esri imagery.
   Loaded only for users allowed by the backend (canView3D); the footprints come
   from /component/get_3d_view_data/, which re-checks the permission. */

var HOUSE_HEIGHT_M = 6;
var HOUSE_COLOR_DEFAULT = "#add8e6";
var HOUSE_INSET = 0.88;
/* Esri has no imagery past this zoom in many areas ("Map data not available");
   beyond it MapLibre stretches the last real tile instead of requesting more. */
var IMAGERY_MAX_NATIVE_ZOOM = 17;
var MAP_MAX_ZOOM_3D = 21;
var LABEL_MIN_ZOOM = 17;
var map3d = null;
var view3dOpen = false;
var view3dHouses = [];
var view3dPolygons = null;
var view3dLabels = null;

/* The switch is on the page from the start; it stays disabled (with a spinner while
   a slum's houses are loading) until there are houses to show. */
function render3DViewToggle(loading) {
    var hasHouses = typeof maplibregl !== "undefined" && houses && Object.keys(houses).length > 0;
    if (!hasHouses) { close3DView(); }
    $("#view3dToggle")
        .prop("checked", view3dOpen)
        .prop("disabled", !hasHouses || !!loading)
        .attr("title", hasHouses || loading ? "" : "Select a slum to use the 3D view");
    $("#view3d-spinner").toggle(!!loading);
}

$(function () { render3DViewToggle(false); });

/* Shrinks every ring toward the outer ring's centre so neighbouring houses show a gap. */
function insetPolygon(rings) {
    var outer = rings[0], cx = 0, cy = 0;
    outer.forEach(function (c) { cx += c[0]; cy += c[1]; });
    cx /= outer.length;
    cy /= outer.length;
    return rings.map(function (ring) {
        return ring.map(function (c) {
            return [cx + (c[0] - cx) * HOUSE_INSET, cy + (c[1] - cy) * HOUSE_INSET];
        });
    });
}

/* Structure's own 2D fill colour (light blue), the base colour of every house. */
function baseColor3D() {
    var name = Object.keys(parse_component).find(_isStructureLayerName);
    return (name && parse_component[name].chkcolor) || HOUSE_COLOR_DEFAULT;
}

function houseKey3D(value) {
    return String(value).split(".")[0].trim();
}

/* house number -> colour from the ticked Filter/Sponsor layers (e.g. type of structure occupancy). */
function filterColors3D() {
    var checked = {};
    $("[name=chk1]:checked").each(function () { checked[$(this).val()] = true; });
    var colors = {};
    Object.keys(parse_component).forEach(function (name) {
        var layer = parse_component[name];
        if (!checked[name] || layer.type === "C") { return; }
        var color = (layer.fillflag ? layer.chkcolor : layer.chklinecolor) || layer.chkcolor;
        (layer._rawChild || []).forEach(function (houseno) { colors[houseKey3D(houseno)] = color; });
    });
    return colors;
}

/* Structure ticked: every house, in the base colour. Structure off: only the houses
   coloured by a ticked Filter/Sponsor layer, as in 2D where filters draw on their own. */
function recolor3D() {
    var source = map3d && map3d.getSource("houses");
    if (!source) { return; }
    var box = $("[name=chk1]").filter(function () { return _isStructureLayerName($(this).val()); });
    var structureOn = box.length === 0 || box.is(":checked");
    var colors = filterColors3D(), base = baseColor3D(), shown = {};
    view3dPolygons.features.forEach(function (f) {
        var key = houseKey3D(f.properties.name);
        f.properties.color = colors[key] || base;
        f.properties.show = structureOn || key in colors;
        shown[f.properties.name] = f.properties.show;
    });
    view3dLabels.features.forEach(function (f) { f.properties.show = shown[f.properties.name]; });
    source.setData(view3dPolygons);
    map3d.getSource("house-labels").setData(view3dLabels);
}

function labelPoint3D(shape) {
    var ring = shape.type === "Polygon" ? shape.coordinates[0] : shape.coordinates[0][0];
    var bounds = new maplibregl.LngLatBounds();
    ring.forEach(function (c) { bounds.extend(c); });
    return bounds.getCenter().toArray();
}

function houseFeatures3D() {
    var polygons = [], labels = [], base = baseColor3D();
    view3dHouses.forEach(function (house) {
        var shape = house.shape;
        polygons.push({
            type: "Feature",
            properties: { name: house.housenumber, color: base },
            geometry: {
                type: shape.type,
                coordinates: shape.type === "Polygon"
                    ? insetPolygon(shape.coordinates)
                    : shape.coordinates.map(insetPolygon)
            }
        });
        labels.push({
            type: "Feature",
            properties: { name: house.housenumber },
            geometry: { type: "Point", coordinates: labelPoint3D(shape) }
        });
    });
    return {
        polygons: { type: "FeatureCollection", features: polygons },
        labels: { type: "FeatureCollection", features: labels }
    };
}

function boundsOf3D(collection) {
    var bounds = new maplibregl.LngLatBounds();
    function extend(coords) {
        if (typeof coords[0] === "number") { bounds.extend(coords); return; }
        coords.forEach(extend);
    }
    collection.features.forEach(function (f) { extend(f.geometry.coordinates); });
    return bounds;
}

var AREA_HEIGHT_M = HOUSE_HEIGHT_M + 2;
var ICON_SIZE_PX = 24;
var iconScales3D = {};

/* Same rule as 2D: a layer's own fillflag, and boundary/ward-area layers are outline only. */
function isOutlineLayer3D(name, layer) {
    return !layer.fillflag || /boundary|ward area/i.test(name);
}

/* Loads a layer's pin icon once; until it is ready its points fall back to circles. */
function loadIcon3D(url) {
    if (url in iconScales3D) { return; }
    iconScales3D[url] = 0;
    map3d.loadImage(url).then(function (res) {
        map3d.addImage(url, res.data);
        iconScales3D[url] = ICON_SIZE_PX / res.data.width;
        refresh3DLayers();
    }).catch(function () {});
}

/* Every ticked Component (C) layer: polygons, lines and points, styled as in 2D. */
function extraFeatures3D() {
    var checked = {};
    $("[name=chk1]:checked").each(function () { checked[$(this).val()] = true; });
    var features = [];
    Object.keys(parse_component).forEach(function (name) {
        var layer = parse_component[name];
        if (!checked[name] || layer.type !== "C" || _isStructureLayerName(name)) { return; }
        var outline = isOutlineLayer3D(name, layer);
        var width = parseFloat(layer.chklinewidth) || 1;
        if (layer.icon) { loadIcon3D(layer.icon); }
        (layer._rawChild || []).forEach(function (item) {
            var shape = item && item.shape;
            if (!shape) { return; }
            var props = { layer: name, color: layer.chklinecolor, fill: layer.chkcolor, width: width };
            if (shape.type === "Point" || shape.type === "MultiPoint") {
                props.kind = "point";
                if (layer.icon && iconScales3D[layer.icon]) {
                    props.icon = layer.icon;
                    props.iconScale = iconScales3D[layer.icon];
                }
            } else if (shape.type === "Polygon" || shape.type === "MultiPolygon") {
                props.kind = outline ? "outline" : "area";
            } else {
                props.kind = "line";
            }
            features.push({ type: "Feature", properties: props, geometry: shape });
        });
    });
    return { type: "FeatureCollection", features: features };
}

function refresh3DLayers() {
    var source = view3dOpen && map3d && map3d.getSource("extras");
    if (source) { source.setData(extraFeatures3D()); }
    recolor3D();
}

function init3DMap() {
    map3d = new maplibregl.Map({
        container: "map3d",
        maxZoom: MAP_MAX_ZOOM_3D,
        style: {
            version: 8,
            glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
            sources: {
                imagery: {
                    type: "raster",
                    tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
                    tileSize: 256,
                    maxzoom: IMAGERY_MAX_NATIVE_ZOOM,
                    attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics"
                }
            },
            layers: [{ id: "imagery", type: "raster", source: "imagery" }]
        },
        pitch: 60,
        bearing: -20,
        maxPitch: 75
    });
    map3d.addControl(new maplibregl.NavigationControl({ visualizePitch: true }));
    map3d.on("load", function () {
        var data = houseFeatures3D();
        view3dPolygons = data.polygons;
        view3dLabels = data.labels;
        map3d.addSource("houses", { type: "geojson", data: view3dPolygons });
        map3d.addSource("house-labels", { type: "geojson", data: view3dLabels });
        map3d.addSource("extras", { type: "geojson", data: extraFeatures3D() });
        map3d.addLayer({
            id: "houses-3d",
            type: "fill-extrusion",
            source: "houses",
            filter: ["==", ["get", "show"], true],
            paint: {
                "fill-extrusion-color": ["get", "color"],
                "fill-extrusion-height": HOUSE_HEIGHT_M,
                "fill-extrusion-opacity": 0.9
            }
        });
        map3d.addLayer({
            id: "houses-labels",
            type: "symbol",
            source: "house-labels",
            minzoom: LABEL_MIN_ZOOM,
            filter: ["==", ["get", "show"], true],
            layout: {
                "text-field": ["get", "name"],
                "text-font": ["Open Sans Regular"],
                "text-size": 11,
                "text-pitch-alignment": "viewport"
            },
            paint: { "text-color": "#ffffff", "text-halo-color": "#000000", "text-halo-width": 1.5 }
        });
        map3d.addLayer({
            id: "areas-3d",
            type: "fill-extrusion",
            source: "extras",
            filter: ["==", ["get", "kind"], "area"],
            paint: {
                "fill-extrusion-color": ["get", "fill"],
                "fill-extrusion-height": AREA_HEIGHT_M,
                "fill-extrusion-opacity": 0.9
            }
        });
        map3d.addLayer({
            id: "lines-3d",
            type: "line",
            source: "extras",
            filter: ["in", ["get", "kind"], ["literal", ["line", "outline"]]],
            paint: { "line-color": ["get", "color"], "line-width": ["get", "width"] }
        });
        map3d.addLayer({
            id: "points-3d",
            type: "circle",
            source: "extras",
            filter: ["all", ["==", ["get", "kind"], "point"], ["!", ["has", "icon"]]],
            paint: {
                "circle-color": ["get", "color"],
                "circle-radius": 6,
                "circle-stroke-color": "#ffffff",
                "circle-stroke-width": 2,
                "circle-pitch-alignment": "viewport"
            }
        });
        map3d.addLayer({
            id: "icons-3d",
            type: "symbol",
            source: "extras",
            filter: ["all", ["==", ["get", "kind"], "point"], ["has", "icon"]],
            layout: {
                "icon-image": ["get", "icon"],
                "icon-size": ["get", "iconScale"],
                "icon-allow-overlap": true,
                "icon-pitch-alignment": "viewport"
            }
        });
        map3d.on("click", "houses-3d", function (e) {
            household_details(e.features[0].properties.name);
        });
        map3d.on("mouseenter", "houses-3d", function () { map3d.getCanvas().style.cursor = "pointer"; });
        map3d.on("mouseleave", "houses-3d", function () { map3d.getCanvas().style.cursor = ""; });
        recolor3D();
        fit3DMap();
    });
}

function fit3DMap() {
    if (view3dPolygons && view3dPolygons.features.length) {
        map3d.fitBounds(boundsOf3D(view3dPolygons), { padding: 40, pitch: 60, bearing: -20, duration: 0 });
    }
}

/* Footprints are fetched from the permission-checked backend endpoint on every open. */
function open3DView() {
    var slumId = global_slum_id;
    $("#view3dToggle").prop("disabled", true);
    $("#view3d-spinner").show();
    $.getJSON("/component/get_3d_view_data/" + encodeURIComponent(slumId))
        .done(function (json) {
            if (String(global_slum_id) !== String(slumId)) { return; }
            view3dHouses = json.houses || [];
            view3dOpen = true;
            $("#map").hide();
            $("#map3d").show();
            $("#map3d-note").show();
            $("#map3d-help").show().find("a[data-lang=en]").click();
            if (!map3d) {
                init3DMap();
            } else {
                map3d.resize();
                var data = houseFeatures3D();
                view3dPolygons = data.polygons;
                view3dLabels = data.labels;
                refresh3DLayers();
                fit3DMap();
            }
            render3DViewToggle(false);
        })
        .fail(function (xhr) {
            alert(xhr.status === 403 ? "You do not have access to the 3D view." : "Could not load the 3D view.");
            render3DViewToggle(false);
        });
}

function close3DView() {
    if (!view3dOpen) { return; }
    view3dOpen = false;
    view3dHouses = [];
    $("#map3d").hide();
    $("#map3d-help").hide();
    $("#map3d-note").hide();
    $("#map").show();
    if (map) { map.invalidateSize(); }
}

$(document).on("change", "#view3dToggle", function () {
    if (this.checked) {
        open3DView();
    } else {
        close3DView();
    }
});

$(document).on("click", "[name=chk1]", function () {
    setTimeout(refresh3DLayers, 0);
});

$(document).on("click", "#map3d-help-close", function () {
    $("#map3d-help").hide();
});

/* One language choice for the helper and the note. */
$(document).on("click", "#map3d-help .help-langs a, #map3d-note .help-langs a", function () {
    var lang = $(this).data("lang");
    $("#map3d-help, #map3d-note").each(function () {
        $(this).find(".help-langs a").removeClass("is-active").filter("[data-lang=" + lang + "]").addClass("is-active");
        $(this).find(".help-text").removeClass("is-active").filter("[data-lang=" + lang + "]").addClass("is-active");
    });
});
