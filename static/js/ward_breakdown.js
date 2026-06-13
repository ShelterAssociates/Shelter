var _wb = {
    wardHouseMap: {},
    wardIds: [],
    wardShapes: {},
    highlightLayers: [],
    wardOverlayLayers: [],
    activeWardId: null,
    panelOpen: false,
    loadedSlumId: null,
    slumBounds: null
};

function _escHtml(s) {
    return String(s == null ? "" : s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function _normalizeWardKey(value) {
    return String(value == null ? "" : value).trim().toLowerCase();
}

function _getCheckedFilterSet() {
    var checked = {};
    var nodes = document.querySelectorAll("[name=chk1]:checked");
    var i;
    for (i = 0; i < nodes.length; i++) {
        checked[String(nodes[i].value)] = true;
    }
    return checked;
}

function _wbSetToggleVisible(visible) {
    var wrap = document.getElementById("wb-toggle-wrap");
    if (wrap) {
        wrap.style.display = visible ? "block" : "none";
    }
}

function _wbSetStripVisible(visible) {
    var strip = document.getElementById("wb-ward-strip");
    if (strip) {
        strip.style.display = visible ? "flex" : "none";
    }
}

function _wbSetLoadingVisible(visible) {
    var loading = document.getElementById("wb-loading-wrap");
    var toggle = document.getElementById("wb-toggle-btn");

    if (loading) {
        loading.style.display = visible ? "block" : "none";
    }
    if (toggle) {
        toggle.disabled = !!visible;
    }
}

function _wbSetReadyVisible(visible) {
    var ready = document.getElementById("wb-ready-wrap");
    if (ready) {
        ready.style.display = visible ? "block" : "none";
    }
}

function _wbSyncToggleButton() {
    var btn = document.getElementById("wb-toggle-btn");
    if (!btn) { return; }
    btn.textContent = _wb.panelOpen ? "Hide ward selector" : "Show ward selector";
}

// Full _wbClearHighlights — used ONLY for complete reset (ward reset / slum change)
function _wbClearHighlights() {
    _wbClearOverlaysOnly();

    // Remove ward-scoped filter layers and restore full layers for checked filters
    if (window._wardScopedLayers) {
        $.each(window._wardScopedLayers, function (componentName, layer) {
            if (map && layer) {
                try { map.removeLayer(layer); } catch (e) { }
            }
        });
        window._wardScopedLayers = {};
    }

    // Restore full layers for all checked filters
    $("[name=chk1]:checked").each(function () {
        var componentName = $(this).val();
        if (parse_component[componentName]) {
            parse_component[componentName].show();
        }
    });
}

function _wbReset() {
    _wbClearHighlights();
    $("[name=chk1]:checked").each(function () {
        var componentName = $(this).val();
        if (parse_component[componentName]) {
            parse_component[componentName].show();
        }
    });
    _wb.wardHouseMap = {};
    _wb.wardIds = [];
    _wb.wardShapes = {};
    _wb.activeWardId = null;
    _wb.panelOpen = false;
    _wb.loadedSlumId = null;
    _wb.slumBounds = null;
}

function _wbFindAdminWardComponent() {
    var sections = Object.keys(currentSlumComponentData || {});
    var s;
    var sectionItems;
    var keys;
    var i;
    var itemData;
    var sectionName;
    var itemName;

    for (s = 0; s < sections.length; s++) {
        sectionItems = currentSlumComponentData[sections[s]] || {};
        keys = Object.keys(sectionItems);
        for (i = 0; i < keys.length; i++) {
            itemData = sectionItems[keys[i]];
            if (!itemData || itemData.type !== "C") { continue; }

            sectionName = _normalizeWardKey(keys[i]);
            itemName = _normalizeWardKey(itemData.name || keys[i]);
            if (sectionName.indexOf("admin ward") !== -1 || itemName.indexOf("admin ward") !== -1) {
                return itemData;
            }
        }
    }

    return null;
}

function _buildWardShapesFromComponentData() {
    _wb.wardShapes = {};
    var wardComponent = _wbFindAdminWardComponent();
    var child;
    var i;

    if (!wardComponent || !wardComponent.child) { return; }

    for (i = 0; i < wardComponent.child.length; i++) {
        child = wardComponent.child[i];
        if (!child || child.housenumber === undefined || child.shape === undefined) { continue; }
        _wb.wardShapes[String(child.housenumber)] = child.shape;
    }
}

function _wbComputeSlumBounds() {
    var merged = null;
    var wardId;
    var shape;
    var layer;
    var bounds;

    if (!window.L || !L.geoJson) {
        _wb.slumBounds = null;
        return;
    }

    for (wardId in _wb.wardShapes) {
        if (!_wb.wardShapes.hasOwnProperty(wardId)) { continue; }
        shape = _wb.wardShapes[wardId];
        if (!shape) { continue; }

        try {
            layer = L.geoJson(shape);
            bounds = layer.getBounds ? layer.getBounds() : null;
            if (!bounds || !bounds.isValid || !bounds.isValid()) { continue; }
            if (!merged) {
                merged = bounds;
            } else {
                merged.extend(bounds);
            }
        } catch (e) { }
    }

    _wb.slumBounds = merged;
}

function _wbComputeCountsForWard(wardId) {
    var wardSet = _wb.wardHouseMap[String(wardId)] || {};
    var wardShape = _wb.wardShapes[String(wardId)] || null;  // ← ward boundary polygon
    var result = {};
    var sectionKeys = Object.keys(currentSlumComponentData || {});
    var sectionIndex, sectionName, sectionItems, itemKeys, itemIndex;
    var itemName, itemData, houseIndex, houseNo;

    for (sectionIndex = 0; sectionIndex < sectionKeys.length; sectionIndex++) {
        sectionName = sectionKeys[sectionIndex];
        sectionItems = currentSlumComponentData[sectionName] || {};
        itemKeys = Object.keys(sectionItems);

        for (itemIndex = 0; itemIndex < itemKeys.length; itemIndex++) {
            itemName = String(itemKeys[itemIndex]);
            itemData = sectionItems[itemKeys[itemIndex]];
            if (!itemData) { continue; }

            var key = sectionName + "||" + itemName;
            result[key] = 0;

            if (itemData.type === "C") {
                // ── Component type: spatial check against ward boundary ──
                if (!wardShape) {
                    // No ward shape available, fall back to total count
                    result[key] = (itemData.child || []).length;
                    continue;
                }

                var children = itemData.child || [];
                for (houseIndex = 0; houseIndex < children.length; houseIndex++) {
                    var childItem = children[houseIndex];
                    if (!childItem || !childItem.shape) continue;

                    // Skip Admin boundary markers
                    if (childItem.shape.properties && childItem.shape.properties.Level === "Admin") {
                        continue;
                    }

                    var centroid = _getGeometryCentroid(childItem.shape);
                    if (!centroid) continue;

                    if (_polygonContainsPoint(wardShape, centroid.lat, centroid.lng)) {
                        result[key] += 1;
                    }
                }

            } else {
                // ── Filter/Sponsor type: match via wardSet house numbers ──
                var childList = itemData.child || [];
                for (houseIndex = 0; houseIndex < childList.length; houseIndex++) {
                    houseNo = String(childList[houseIndex]);
                    if (Object.prototype.hasOwnProperty.call(wardSet, houseNo)) {
                        result[key] += 1;
                    }
                }
            }
        }
    }

    return result;
}

function _wbComputeTotalCounts() {
    var result = {};
    var sectionKeys = Object.keys(currentSlumComponentData || {});
    var sectionIndex;
    var sectionName;
    var sectionItems;
    var itemKeys;
    var itemIndex;
    var itemName;
    var itemData;

    for (sectionIndex = 0; sectionIndex < sectionKeys.length; sectionIndex++) {
        sectionName = sectionKeys[sectionIndex];
        sectionItems = currentSlumComponentData[sectionName] || {};
        itemKeys = Object.keys(sectionItems);

        for (itemIndex = 0; itemIndex < itemKeys.length; itemIndex++) {
            itemName = String(itemKeys[itemIndex]);
            itemData = sectionItems[itemKeys[itemIndex]];
            if (!itemData || itemData.type === "C") { continue; }
            result[sectionName + "||" + itemName] = (itemData.child || []).length;
        }
    }

    return result;
}

function _wbGetWardHouseSet() {
    if (!_wb.activeWardId) { return null; }
    return _wb.wardHouseMap[String(_wb.activeWardId)] || null;
}

function _wbGetScopedHouseCount() {
    var wardSet = _wbGetWardHouseSet();
    if (!wardSet) { return 0; }
    return Object.keys(wardSet).length;
}

function _wbRenderWardOverlay() {
    var wardId;
    var shape;
    var layer;
    var bounds;

    _wbClearOverlaysOnly();
    if (!map || !window.L || !L.geoJson) { return; }
    if (!_wb.activeWardId) { return; }

    for (wardId in _wb.wardShapes) {
        if (!_wb.wardShapes.hasOwnProperty(wardId)) { continue; }
        shape = _wb.wardShapes[wardId];
        if (!shape) { continue; }

        try {
            layer = L.geoJson(shape, {
                style: String(_wb.activeWardId) === String(wardId) ? {
                    color: "#7acb6f",
                    weight: 5,
                    opacity: 1,
                    fillColor: "#ffffff",
                    fillOpacity: 0,
                } : {
                    color: "transparent",
                    weight: 0,
                    opacity: 0,
                    fillOpacity: 0
                }
            });
            layer.addTo(map);
            _wb.wardOverlayLayers.push(layer);
        } catch (e) {
            console.warn("Ward overlay render failed:", e);
        }
    }

    if (_wb.activeWardId && _wb.wardShapes[String(_wb.activeWardId)]) {
        try {
            layer = L.geoJson(_wb.wardShapes[String(_wb.activeWardId)], {
                style: {
                    color: "#7acb6f",
                    weight: 3,
                    opacity: 1,
                    fillColor: "#ffffff",
                    fillOpacity: 0,
                    dashArray: "4,4"
                }
            });
            layer.addTo(map);
            _wb.highlightLayers.push(layer);
            bounds = layer.getBounds ? layer.getBounds() : null;
            if (bounds && bounds.isValid && bounds.isValid()) {
                map.fitBounds(bounds, { padding: [30, 30], maxZoom: 17 });
            }
        } catch (err) {
            console.warn("Selected ward overlay failed:", err);
        }
    }
}
function _wbUpdateFilterCounts() {
    var spanNodes = document.querySelectorAll(".wb-item-count");
    var counts = _wb.activeWardId ? _wbComputeCountsForWard(_wb.activeWardId) : _wbComputeTotalCounts();
    var i, span, filterName, sectionName, count, totalCount, itemType;

    for (i = 0; i < spanNodes.length; i++) {
        span = spanNodes[i];
        filterName = span.getAttribute("data-item-name") || "";
        sectionName = span.getAttribute("data-section-name") || "";
        totalCount = span.getAttribute("data-total-count") || "0";
        itemType = span.getAttribute("data-item-type") || "";

        if (_wb.activeWardId && itemType !== "C" &&
            (filterName === "Structure" || filterName === "HouseBaseLayer")) {
            // Filter-type structure: count from wardSet
            count = _wbGetScopedHouseCount();
        } else if (counts.hasOwnProperty(sectionName + "||" + filterName)) {
            // Covers both F/S types AND C types (now spatially computed)
            count = counts[sectionName + "||" + filterName];
        } else {
            count = parseInt(totalCount, 10) || 0;
        }

        span.textContent = "(" + count + ")";
        span.setAttribute("data-current-count", String(count));
    }

    _wbUpdateActiveLabel();
}

function _wbUpdateActiveLabel() {
    var label = document.getElementById("wb-active-label");
    if (!label) { return; }

    if (_wb.activeWardId) {
        label.textContent = "Ward " + _wb.activeWardId + " selected";
    } else {
        label.textContent = "City view";
    }
}

function _wbHighlightWard(wardId) {
    _wb.activeWardId = String(wardId);
    _wbRenderWardOverlay();
}

function _wbRenderWardStrip() {
    var strip = document.getElementById("wb-ward-strip");
    var html = "";
    var i;
    var wardId;

    if (!strip) { return; }

    if (_wb.wardIds.length === 0) {
        strip.innerHTML = '<div style="font-size:12px;color:#6b7c93;">No ward data loaded.</div>';
        return;
    }

    for (i = 0; i < _wb.wardIds.length; i++) {
        wardId = String(_wb.wardIds[i]);
        html += '<button type="button" class="wb-ward-chip' +
            (String(_wb.activeWardId) === wardId ? ' is-active' : '') +
            '" data-wid="' + _escHtml(wardId) + '">' +
            'Ward ' + _escHtml(wardId) +
            '</button>';
    }

    strip.innerHTML = html;

    var buttons = strip.querySelectorAll(".wb-ward-chip");
    for (i = 0; i < buttons.length; i++) {
        buttons[i].addEventListener("click", _onWardChipClick);
    }

    _wbUpdateActiveLabel();
    _wbRenderWardOverlay(); // safe now — uses _wbClearOverlaysOnly internally
}


function _wbEnsureDOM() {
    var existing = document.getElementById("wb-toggle-wrap");
    var refresh = document.getElementById("compochk_refresh");
    var compochk = document.getElementById("compochk");
    var html;

    if (existing) { return; }

    html =
        '<div id="wb-toggle-wrap" style="display:none; padding:6px 10px 6px;' +
        ' border-top:1px solid #dce8f1; background:#f4f8fc;">' +
        '<div style="font-size:11px; font-weight:600; color:#2471a3; margin-bottom:4px;">' +
        'Admin ward breakdown' +
        '</div>' +
        '<div id="wb-loading-wrap" style="display:none; margin:6px 0 8px;">' +
        '<div style="height:6px; width:100%; border-radius:999px; overflow:hidden; background:#d9e8f5;">' +
        '<div style="height:100%; width:42%; border-radius:999px; background:linear-gradient(90deg, #2471a3 0%, #5dade2 50%, #2471a3 100%); animation:wb-loading-slide 1.1s ease-in-out infinite; background-size:200% 100%;"></div>' +
        '</div>' +
        '<div style="margin-top:4px; font-size:11px; color:#5d6d7e;">Loading ward breakdown...</div>' +
        '</div>' +
        '<div id="wb-ready-wrap" style="display:none;">' +
        '<div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">' +
        '<button id="wb-toggle-btn" type="button" style="background:#fff; border:1px solid #c8d8ea;' +
        ' border-radius:4px; padding:5px 10px; font-size:12px; cursor:pointer; color:#1a5276; font-weight:600;">' +
        'Show ward selector' +
        '</button>' +
        '<button id="wb-cityreset-btn" type="button" title="Reset to full city view"' +
        ' style="background:#fff; border:1px solid #c8d8ea; border-radius:4px; padding:5px 8px;' +
        ' font-size:12px; cursor:pointer; color:#1a5276;">' +
        '↩ City view' +
        '</button>' +
        '<span id="wb-active-label" style="font-size:12px; font-weight:600; color:#1a5276;"></span>' +
        '</div>' +
        '<div id="wb-ward-strip" style="display:none; gap:6px; flex-wrap:wrap; margin-top:6px;"></div>' +
        '</div>' +
        '</div>';

    if (refresh && refresh.parentNode) {
        refresh.insertAdjacentHTML("afterend", html);
    } else if (compochk && compochk.parentNode) {
        compochk.insertAdjacentHTML("beforebegin", html);
    }

    var toggleBtn = document.getElementById("wb-toggle-btn");
    var cityBtn = document.getElementById("wb-cityreset-btn");

    if (toggleBtn && !toggleBtn._wbBound) {
        toggleBtn._wbBound = true;
        toggleBtn.addEventListener("click", function () {
            _wb.panelOpen = !_wb.panelOpen;
            _wbSetStripVisible(_wb.panelOpen);
            if (_wb.panelOpen) {
                _wbRenderWardOverlay();
            }
            _wbSyncToggleButton();
        });
    }

    if (cityBtn && !cityBtn._wbBound) {
        cityBtn._wbBound = true;
        cityBtn.addEventListener("click", function () {
            _wb.activeWardId = null;
            _wbClearHighlights(); // removes scoped layers only

            // Explicitly restore full city layers for all checked filters
            $("[name=chk1]:checked").each(function () {
                var componentName = $(this).val();
                if (parse_component[componentName]) {
                    parse_component[componentName].show();
                }
            });

            if (map && _wb.slumBounds && _wb.slumBounds.isValid && _wb.slumBounds.isValid()) {
                map.fitBounds(_wb.slumBounds, { padding: [20, 20] });
            }
            _wbRenderWardStrip();
            _wbUpdateFilterCounts();
        });
    }

    if ($("#wb-loading-style").length === 0) {
        $("head").append(
            '<style id="wb-loading-style">' +
            '@keyframes wb-loading-slide{0%{transform:translateX(-60%)}50%{transform:translateX(110%)}100%{transform:translateX(-60%)}}' +
            '</style>'
        );
    }

    _wbSyncToggleButton();
}

function _onWardChipClick() {
    var wid = this.getAttribute("data-wid");
    if (!wid) { return; }

    _wb.activeWardId = String(wid);

    // Step 1: Remove ward boundary overlays only
    _wbClearOverlaysOnly();

    // Step 2: Re-scope all checked filters to new ward
    _rescopeCheckedComponentsToWard();

    // Step 3: Re-draw ward boundary strip + overlay
    _wbRenderWardStrip();
    _wbUpdateFilterCounts();
}

function _wbNormalizeWardResponse(data) {
    if (!data) { return {}; }
    if (data.ward_data && typeof data.ward_data === "object") {
        return data.ward_data;
    }
    return data;
}

function initWardBreakdownPanel(slumId) {
    var wardData;
    var keys;
    var i;
    var wardId;
    var houses;

    _wbReset();
    _wb.loadedSlumId = String(slumId);
    _wbEnsureDOM();
    _wbSetToggleVisible(false);
    _wbSetReadyVisible(false);
    _wbSetStripVisible(false);
    _wbUpdateActiveLabel();
    _buildWardShapesFromComponentData();
    _wbComputeSlumBounds();

    if (slumId === undefined || slumId === null || String(slumId) === "") {
        _wbSetLoadingVisible(false);
        return;
    }

    _wbSetToggleVisible(true);
    _wbSetLoadingVisible(true);

    fetch("/component/get-ward-wise-data/?slum_id=" + encodeURIComponent(String(slumId)))
        .then(function (res) { return res.json(); })
        .then(function (data) {
            var normalized;
            var j;

            if (String(_wb.loadedSlumId) !== String(slumId)) { return; }
            normalized = _wbNormalizeWardResponse(data);
            keys = Object.keys(normalized || {});
            if (!keys.length) {
                _wbSetLoadingVisible(false);
                _wbSetReadyVisible(true);
                _wbSetStripVisible(true);
                _wbRenderWardStrip();
                console.warn("Ward breakdown counts response was empty for slum", slumId);
                return;
            }

            _wb.wardIds = [];
            _wb.wardHouseMap = {};
            for (i = 0; i < keys.length; i++) {
                wardId = String(keys[i]);
                houses = normalized[keys[i]] || [];
                _wb.wardIds.push(wardId);
                _wb.wardHouseMap[wardId] = {};
                for (j = 0; j < houses.length; j++) {
                    _wb.wardHouseMap[wardId][String(houses[j])] = true;
                }
            }

            _wbSetToggleVisible(true);
            _wbSetLoadingVisible(false);
            _wbSetReadyVisible(true);
            _wbRenderWardStrip();
            _wbUpdateFilterCounts();
        })
        .catch(function (err) {
            if (String(_wb.loadedSlumId) !== String(slumId)) { return; }
            _wbSetLoadingVisible(false);
            _wbSetReadyVisible(true);
            console.warn("Failed to load ward breakdown counts for slum " + slumId + ":", err);
        });
}

function refreshWardBreakdownCounts() {
    if (_wb.wardIds.length === 0) { return; }
    _wbUpdateFilterCounts();
}

function resetWardBreakdownPanel() {
    _wbReset();
    _wbSetLoadingVisible(false);
    var wrap = document.getElementById("wb-toggle-wrap");
    if (wrap) {
        wrap.style.display = "none";
    }
}


function _showComponentForActiveWard(componentName) {
    if (!window._wardScopedLayers) window._wardScopedLayers = {};

    // Remove any previous ward-scoped layer for this component
    if (window._wardScopedLayers[componentName]) {
        map.removeLayer(window._wardScopedLayers[componentName]);
        delete window._wardScopedLayers[componentName];
    }

    var wardSet = _wbGetWardHouseSet();
    var component = parse_component[componentName];
    if (!component || !wardSet) {
        if (component) component.show();
        return;
    }

    var itemData = null;
    $.each(currentSlumComponentData || {}, function (sectionName, sectionItems) {
        if (itemData) return false;
        $.each(sectionItems || {}, function (itemName, data) {
            if (itemName === componentName) {
                itemData = data;
                return false;
            }
        });
    });

    if (!itemData) {
        component.show();
        return;
    }

    var type = itemData.type;

    if (type === "C") {
        var wardShape = _wb.wardShapes[String(_wb.activeWardId)] || null;
        var filteredShapes = [];

        $.each(itemData.child || [], function (_, childItem) {
            if (!childItem || childItem.shape === undefined) return;

            var isAdmin = childItem.shape.properties &&
                childItem.shape.properties.Level === "Admin";

            if (isAdmin) {
                // always include admin boundary
                filteredShapes.push(childItem.shape);
                return;
            }

            // For non-admin: use spatial containment if ward shape available,
            // otherwise fall back to wardSet house number match
            if (wardShape) {
                var centroid = _getGeometryCentroid(childItem.shape);
                if (centroid && _polygonContainsPoint(wardShape, centroid.lat, centroid.lng)) {
                    filteredShapes.push(childItem.shape);
                }
            } else {
                var key = String(
                    childItem.housenumber !== undefined ? childItem.housenumber : ""
                ).split(".")[0].trim();
                if (wardSet.hasOwnProperty(key)) {
                    filteredShapes.push(childItem.shape);
                }
            }
        });

        if (!filteredShapes.length) return;

        var styleArgs = component.style_geo_geometry(filteredShapes[0]);
        var layer = L.geoJson(filteredShapes, styleArgs);
        layer.addTo(map);
        window._wardScopedLayers[componentName] = layer;

    } else {
        // Filter/Sponsor type: child is array of house numbers
        var filteredHouseShapes = [];
        $.each(itemData.child || [], function (_, houseNo) {
            var key = String(houseNo).split(".")[0].trim();
            if (!wardSet.hasOwnProperty(key)) return;
            var shape = houses[key] || houses[parseInt(key, 10)] || houses[String(key)];
            if (shape) filteredHouseShapes.push(shape);
        });

        if (!filteredHouseShapes.length) return;

        var styleArgs = component.style_geo_geometry(filteredHouseShapes[0]);
        var layer = L.geoJson(filteredHouseShapes, styleArgs);
        layer.addTo(map);
        window._wardScopedLayers[componentName] = layer;
    }
}

function _rescopeCheckedComponentsToWard() {
    if (!window._wardScopedLayers) window._wardScopedLayers = {};

    // Remove previous ward-scoped layers from map
    $.each(window._wardScopedLayers, function (componentName, layer) {
        if (map && layer) {
            try { map.removeLayer(layer); } catch (e) { }
        }
    });
    window._wardScopedLayers = {};

    // For every checked filter: hide full layer, show ward-scoped version
    $("[name=chk1]:checked").each(function () {
        var componentName = $(this).val();
        if (!parse_component[componentName]) return;

        // Always hide the full pre-built layer
        parse_component[componentName].hide();

        if (_wb.activeWardId) {
            _showComponentForActiveWard(componentName);
        } else {
            // No ward — restore full layer
            parse_component[componentName].show();
        }
    });
}

// Only clears ward boundary highlight overlays — never touches filter layers
function _wbClearOverlaysOnly() {
    var i;
    for (i = 0; i < _wb.highlightLayers.length; i++) {
        if (map && _wb.highlightLayers[i]) {
            try { map.removeLayer(_wb.highlightLayers[i]); } catch (e) { }
        }
    }
    _wb.highlightLayers = [];

    for (i = 0; i < _wb.wardOverlayLayers.length; i++) {
        if (map && _wb.wardOverlayLayers[i]) {
            try { map.removeLayer(_wb.wardOverlayLayers[i]); } catch (e) { }
        }
    }
    _wb.wardOverlayLayers = [];
}
