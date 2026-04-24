/*
 * city_wise_map.js
 * Parses and displays: Admin Ward, Electoral Ward, Slum,
 * Component/Filter/Sponsor, and RIM data.
 
 */

/* ── Global state ─────────────────────────────────────────────────────────── */
var length_of_components = {
    "Dambar road": 75140, "Cement/Concrete": 34648, "Interlocking": 24264,
    "Kharanja": 20767, "Kutcha road": 96744, "Existing Drainage Line": 383,
    "Location of Kutcha Open Nali (Gutter)": 5266,
    "Location of Pucca Closed Nali (Gutter)": 5581,
    "Location of Pucca Open Nali (Gutter)": 59665,
    "Location of Nahar": 23136, "Location of Nala": 6907
};

var WARDLEVEL = ["AdministrativeWard", "ElectoralWard", "Slum"];

var parse_data = {};
var map = null;
var arr_poly_disp = [];
var legends = [];
var city = null;
var objBreadcrumb = null;
var houses = null;

/* Component/filter variables */
var zindex = 0;
var global_slum_id = 0;
var lst_sponsor = [];
var parse_component = {};
var globalJsonData = {};

var modelsection = {
    "General": "General information",
    "Toilet": "Status of sanitation (pre SBM)",
    "Water": "Type of water connection",
    "Waste": "Facility of solid waste collection",
    "Drainage": "Drainage/open gutter information",
    "Road": "Road & access information",
    "Gutter": "Gutter information"
};

var TYPE_COMPONENT = { C: "Component", S: "Sponsor", F: "Filter" };

var myCustomColour = "#583470";
var markerHtmlStyles = (
    "background-color:" + myCustomColour + ";width:3rem;height:3rem;display:block;" +
    "left:-1.5rem;top:-1.5rem;position:relative;border-radius:3rem 3rem 0;" +
    "transform:rotate(45deg);border:1px solid #FFFFFF"
);

/* Timeline globals */
var TIMELINE_YEARS = [];
var TIMELINE_DATA = {};
var CURRENT_INDEX = 0;
var legendControl;

/* Slider state */
var _sliderStops = [];
var _currentStopIndex = 0;

/*
 * Timeline highlight colour — set by the API response scope:
 *   scope = 'sponsor' or 'all' (superuser/normal)  → pink  (#eb349e)
 *   scope = 'anonymous'                             → yellow (#FFD700)
 * Default to pink; will be overwritten in initToiletTimeline.
 */
var _timelineHighlightColor = "#eb349e";

function _sliderValToStopIndex(val) {
    if (_sliderStops.length <= 1) return 0;
    return Math.round((val / 100) * (_sliderStops.length - 1));
}
function _stopIndexToSliderVal(idx) {
    if (_sliderStops.length <= 1) return 0;
    return Math.round((idx / (_sliderStops.length - 1)) * 100);
}


/* ── Parser ──────────────────────────────────────────────────────────────── */
var Parser = (function () {
    function Parser(index, data) {
        this.index = index;
        this.data = data;
    }

    Parser.prototype.render = function () {
        var wards = {};
        var w_data = {};
        var ward = this.ward_data();
        wards[this.data.name] = { obj: ward };

        if (this.data.content != null) {
            var _this = this;
            legends.push(this.data.name.trim());
            $.each(this.data.content, function (key, value) {
                var objParse = new Parser(_this.index + 1, value);
                $.extend(w_data, objParse.render());
            });
            legends.pop();
            wards[this.data.name]["content"] = w_data;
        }
        return wards;
    };

    Parser.prototype.ward_data = function () {
        var dataval = $.extend({}, this.data);
        delete dataval["content"];
        dataval["type"] = WARDLEVEL[this.index];
        var details = [];
        $.extend(details, legends);
        dataval["legend"] = details || [];
        var ward = new (eval(WARDLEVEL[this.index]))(dataval);
        ward.setListeners();
        return ward;
    };

    return Parser;
}());


/* ── Map initialisation ──────────────────────────────────────────────────── */
function initMap12() {
    $(".overlay").show();
    var city_id = $("#city_id").val();
    var city_name = $("#city_name").val();

    $.ajax({
        url: "/admin/slummapdisplay/" + city_id + "/",
        type: "GET",
        contenttype: "json",
        success: function (json) {
            var data = json["content"];
            city = new City(city_name);
            $.each(data, function (key, value) {
                var obj_parser = new Parser(0, value);
                $.extend(parse_data, obj_parser.render());
            });
            objBreadcrumb = new Breadcrumbs([]);

            $(document).ready(function () {
                var slumname = $("#slum_name").val();
                if (slumname !== "") {
                    var slum_input = $("#datatable_filter").find("input");
                    slum_input.val(slumname).trigger("keyup");
                    $("#datatable span").get(0).click();
                }
            });

            $(".overlay").hide();
        }
    });
}

function initMap() {
    var center_data = {
        "Navi Mumbai": new L.LatLng(19.09118307623272, 73.0159571631209),
        "Thane": new L.LatLng(19.215441921044757, 72.98368482425371),
        "Sangli": new L.LatLng(16.850235500492538, 74.60914487360401),
        "Kolhapur": new L.LatLng(16.700800029695312, 74.23729060058895),
        "PCMC": new L.LatLng(18.640083, 73.825560),
        "Pune": new L.LatLng(18.51099762698481, 73.86055464212859),
        "Panvel": new L.LatLng(19.051509, 73.109058),
        "Saharanpur": new L.LatLng(29.96813172, 77.54673382),
        "Pune District": new L.LatLng(18.57054718, 74.07657987),
        "Mohanlalganj City": new L.LatLng(26.66998253, 80.98541311),
        "Nilgiri District": new L.LatLng(11.45878141, 76.64049998),
        "Ichalkaranji": new L.LatLng(16.68803567359255, 74.46583551598165),
        "Banthara Town": new L.LatLng(26.68906000, 80.81704000)
    };

    var cityName = $("#city_name").val();
    var pos = center_data[cityName] || new L.LatLng(18.640083, 73.825560);

    map = new L.Map("map", { center: pos, zoom: 12, zoomSnap: 0.25, markerZoomAnimation: false });

    if (["Pune District", "Nilgiri District"].includes(cityName)) {
        map.setZoom(9);
    }

    var mutantLayer = L.gridLayer.googleMutant({ type: "satellite" });
    mutantLayer.addTo(map);
    map.on('layeradd', function (e) {
        if (e.layer._mutant) {
            window._googleMap = e.layer._mutant;
        }
    });
    addLegend(map);
    initMap12();
}

function addLegend(map) {
    legendControl = L.control({ position: "topright" });
    legendControl.onAdd = function () {
        var div = L.DomUtil.create("div", "map-legend");
        div.innerHTML =
            '<div class="legend-item"><span class="legend-box red-border"></span><span>Household data available</span></div>' +
            '<div class="legend-item"><span class="legend-box blue-border"></span><span>Household data not available</span></div>' +
            '<div class="legend-item"><span class="legend-box yellow-border"></span><span>Now in Slum redevlopment (Previously surveyed)</span></div>';
        return div;
    };
    legendControl.addTo(map);
}

function getQueryParam(param) {
    return new URLSearchParams(window.location.search).get(param);
}

function readJSONFile(filePath, callback, param1, param2) {
    return fetch(filePath)
        .then(function (r) { return r.json(); })
        .then(function (data) { callback(data, param1, param2); })
        .catch(function (err) { console.error("Error fetching JSON:", err); });
}


/* ── Slum data fetch ─────────────────────────────────────────────────────── */
function slum_data_fetch(slumId) {
    $("#right-panel").addClass("active");

    /* Clear existing highlight and reset search input when switching slum */
    fullResetHouseholdSearch();

    var compochk = $("#compochk");
    compochk.html(
        '<div style="height:300px;width:100%;display:flex;align-items:center;justify-content:center;">' +
        '<div id="loading-img"></div></div>'
    );

    Promise.all([
        $.ajax({
            url: "/component/get_component/" + slumId,
            type: "GET",
            contenttype: "json",
            headers: { "Force-Refresh-Flag": "0" }
        }),
        $.ajax({ url: "/component/get_kobo_RIM_data/" + slumId, type: "GET", contenttype: "json" })
    ]).then(function (result) {
        global_slum_id = slumId;
        var componentData = result[0];
        const skipStatuses = ["inactive", "sra", "road_widening"];
        if (skipStatuses.includes(componentData.status)) {
            $("#filter-container").empty();
            $("#right-panel").addClass("active");
            $("#factsheet-btn-slot").hide().html("");
            $("#household-search-wrapper").hide();
            $("#sponsor-pinned").hide();
            $("#compochk_refresh").html("");

            $.each(arr_poly_disp, function (k, v) { map.removeLayer(v.shape); });
            arr_poly_disp = [];

            $("#compochk").html(
                '<div style="height:300px;width:100%;display:flex;align-items:center;justify-content:center;">' +
                '<div id="loading-img"></div></div>'
            );

            fetch("/admin/slum-transformation-photos/" + slumId)
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    var photosData = data[String(slumId)];
                    if (!photosData || Object.keys(photosData).length === 0) {
                        $("#compochk").html('<div style="padding:16px;color:#888;font-size:13px;">No transformation photos available.</div>');
                        return;
                    }
                    buildTransformationSlider(slumId, photosData);
                })
                .catch(function () {
                    $("#compochk").html('<div style="padding:16px;color:#888;font-size:13px;">Failed to load photos.</div>');
                });
            return;
        }
        var visible = getQueryParam("mr");
        if (visible === "1") {
            readJSONFile("/admin/translations/?mr=" + visible, generate_filter, slumId, componentData);
        } else {
            generate_filter(globalJsonData, slumId, componentData);
        }

        generate_RIM(result[1]);
    });
}


/* ── RIM modal population ────────────────────────────────────────────────── */
function generate_RIM(result) {
    $("#rim").html("");
    if ("General" in result) {
        try {
            result["General"]["admin_ward"] = objBreadcrumb.val[0];
            result["General"]["slum_name"] = objBreadcrumb.val[2];
        } catch (e) { }
    }

    $.each(result, function (k, v) {
        var modal = $("#myModal").clone();
        modal.find("#modelhdtext").html(modelsection[k]);
        modal.attr("id", k);

        var spstr = "";
        var commentstr = "";
        spstr += '<table class="table table-striped" style="margin-bottom:0;font-size:12px;">';

        if (v instanceof Array) {
            modal.find("div.modal-dialog").addClass("modal-lg");
            var toilet_header = "<thead><tr><th>&nbsp;</th>";
            var toilet_body = "<tbody>";

            for (var i = 0; i < v.length; i++) {
                if (v[i].hasOwnProperty("ctb_name")) {
                    toilet_header += "<th>" + v[i]["ctb_name"] + "</th>";
                    delete v[i]["ctb_name"];
                } else {
                    toilet_header += "<th>CTB" + (i + 1) + "</th>";
                }
            }
            toilet_header += "</tr></thead>";

            if (v.length > 0) {
                var keys_all = [];
                for (var j = 0; j < v.length; j++) {
                    keys_all = keys_all.concat(Object.keys(v[j]));
                }
                var keys_headers = keys_all.filter(function (item, idx) { return keys_all.indexOf(item) === idx; });

                $.each(keys_headers, function (key, val) {
                    toilet_body += '<tr><td style="font-weight:bold;width:200px;">' + val + "</td>";
                    for (var i = 0; i < v.length; i++) {
                        toilet_body += "<td>" + (v[i][val] !== undefined ? v[i][val] : "None") + "</td>";
                    }
                    toilet_body += "</tr>";
                });
            } else {
                toilet_body += "<tr><td>No CTB's</td></tr>";
            }

            spstr += toilet_header + toilet_body;
        } else {
            modal.find("div.modal-dialog").removeClass("modal-lg");
            spstr += "<tbody>";
            $.each(v, function (key, val) {
                if (key.indexOf("comment") !== -1 || key.indexOf("Describe") !== -1) {
                    commentstr += '<tr><td colspan=2><label style="font-weight:bold;">' + key + ": </label> " + val + "</td></tr>";
                } else {
                    spstr += '<tr><td style="font-weight:bold;width:50%;">' + key + "</td><td>" + val + "</td></tr>";
                }
            });
        }

        spstr += commentstr + "</tbody></table>";
        modal.find("#modelbody").html(spstr);
        $("#rim").append(modal);

        $("div.panel-collapse[name='" + modelsection[k] + "']").prepend(
            '<div name="div_group">&nbsp;&nbsp;&nbsp;' +
            '<span><a style="cursor:pointer;color:darkred;" data-toggle="modal" data-target="#' + k + '">View Tabular Data</a></span>' +
            "</div>"
        );
    });
}


/* ── Filter / right panel generation ────────────────────────────────────── */
function generate_filter(globalJsonData, slumId, result) {

    /* ---- Refresh button ---- */
    var compochk_refresh = $("#compochk_refresh");

    fetch("/component/can-refresh-section/")
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data.can_refresh) {
                compochk_refresh.html(
                    '<div style="position:relative;">' +
                    '<button id="refreshComponents" class="btn btn-primary btn-xs"' +
                    ' style="width:100%;margin-bottom:0;font-size:12px;border-radius:4px;padding:4px 8px;">' +
                    "Refresh Components</button>" +
                    '<div class="refresh-confirm-box" id="refreshConfirmBox">' +
                    "<h5>Refresh Components?</h5>" +
                    "<p>Clicking <strong>Yes</strong> will clear cached data and reload fresh from server.</p>" +
                    '<div class="refresh-confirm-actions">' +
                    '<button class="btn btn-default btn-xs" id="refreshConfirmNo">Cancel</button>' +
                    '<button class="btn btn-primary btn-xs" id="refreshConfirmYes">Yes, Refresh</button>' +
                    "</div></div></div>"
                );
            } else {
                compochk_refresh.html("");
            }
        })
        .catch(function () { compochk_refresh.html(""); });

    /* ---- Build component panel ---- */
    var compochk = $("#compochk");
    var counter = 0;
    var panel_component = "";

    $.each(result, function (k, v) {
        counter++;
        var label = Object.keys(globalJsonData).length > 0 ? globalJsonData[k] : k;

        panel_component +=
            '<div name="div_group" class="panel panel-default panel-heading">' +
            '<input class="chk" name="grpchk" type="checkbox" onclick="checkAllGroup(this)">' +
            '&nbsp;&nbsp;<a name="chk_group" data-toggle="collapse" data-parent="#compochk" href="#' + counter + '">' +
            "<b><span>" + label + "</span></b></a><br>";

        panel_component += '<div id="' + counter + '" class="panel-collapse collapse" name="' + k + '">';

        $.each(v, function (k1, v1) {
            var chkcolor = v1["blob"]["polycolor"];
            var inner_label = Object.keys(globalJsonData).length > 0 ? globalJsonData[k1] : k1;
            var child_length = k1 in length_of_components ? length_of_components[k1] + " mtr" : v1["child"].length;
            var icon = v1["icon"] || "";

            panel_component +=
                '<div name="div_group">&nbsp;&nbsp;&nbsp;' +
                '<input name="chk1" class="chk"' +
                ' style="background:' + chkcolor + ';background-color:' + chkcolor + ';"' +
                ' selection="' + k + '"' +
                ' component_type="' + v1["type"] + '"' +
                ' type="checkbox" value="' + k1 + '"' +
                ' onclick="checkSingleGroup(this);">' +
                '<a>&nbsp;' + inner_label + '</a>&nbsp;(' + child_length + ')' +
                (icon ? ' <img src="' + icon + '">' : '') +
                '</div>';

            /* Build house lookup for Structure / Admin Ward Area */
            if (k1 === "Structure" || k1 === "Admin Ward Area") {
                houses = {};
                $.each(v1["child"], function (k2, v2) {
                    v2.shape["properties"] = { name: v2.housenumber };
                    if (k1 === "Admin Ward Area") { v2.shape.properties["Level"] = "Admin"; }
                    houses[v2.housenumber] = v2.shape;
                });
            }

            parse_component[k1] = new (eval(TYPE_COMPONENT[v1.type]))(v1);
        });

        panel_component += "</div></div>";
    });

    compochk.html(panel_component);

    /* Auto-select boundary checkbox */
    setTimeout(function () {
        var autoSelect = null;
        $("[name=chk1]").each(function () {
            var val = $(this).val();
            if (val === "Town boundary" || val === "Slum boundary") {
                autoSelect = $(this);
                return false;
            }
        });
        if (autoSelect && !autoSelect.is(":checked")) { autoSelect.click(); }
    }, 300);

    /* Pin sponsor section */
    setTimeout(function () { pinSponsorToBottom(slumId); }, 400);

    initHouseholdSearch();
}


/* ── Checkbox event handlers ─────────────────────────────────────────────── */
function checkSingleGroup(singlechk) {
    $.each(arr_poly_disp, function (k, v) { map.removeLayer(v.shape); });

    var chkchild = $(singlechk).val();
    if ($(singlechk).is(":checked")) {
        parse_component[chkchild].show();
    } else {
        parse_component[chkchild].hide();
    }

    var flag = $(singlechk).parent().parent().parent().find("[name=chk1]:checked").length > 0;
    $(singlechk).parent().parent().parent().find("[name=grpchk]")[0].checked = flag;
}

function checkAllGroup(grpchk) {
    if ($(grpchk).is(":checked")) {
        $(grpchk).parent().find("[name=chk1]:not(:checked)").click();
        if ($(grpchk).parent().find("div.in").length === 0) {
            $(grpchk).parent().find("a[name=chk_group]").click();
        }
    } else {
        $(grpchk).parent().find("[name=chk1]:checked").click();
        if ($(grpchk).parent().find("div.in").length > 0) {
            $(grpchk).parent().find("a[name=chk_group]").click();
        }
    }
}


/* ── Household search ────────────────────────────────────────────────────── */
function initHouseholdSearch() {
    /* Hide slum polygons while in component view */
    $.each(arr_poly_disp, function (k, v) {
        if (v.type === "Slum") { map.removeLayer(v.shape); }
    });

    var wrapper = document.getElementById("household-search-wrapper");
    if (!wrapper) return;
    wrapper.style.display = "block";

    var oldInput = document.getElementById("household-search-input");
    var dropdown = document.getElementById("household-search-dropdown");
    if (!oldInput || !dropdown) return;

    var searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.id = "household-search-input";
    searchInput.placeholder = "Search household number...";
    searchInput.autocomplete = "off";
    searchInput.style.cssText = "width:100%;padding:6px 10px;border:1px solid #ccc;" +
        "border-radius:4px;font-size:13px;box-sizing:border-box;color:#000;background:#fff;outline:none;";
    oldInput.parentNode.replaceChild(searchInput, oldInput);

    searchInput.addEventListener("input", function () {
        if (window._householdHighlight) {
            window._householdHighlight.closePopup();
            map.removeLayer(window._householdHighlight);
            window._householdHighlight = null;
        }

        var query = this.value.trim().toLowerCase();
        dropdown.innerHTML = "";

        if (!query || !houses || Object.keys(houses).length === 0) {
            dropdown.style.display = "none";
            return;
        }

        var matches = Object.keys(houses)
            .filter(function (h) { return String(h).toLowerCase().indexOf(query) !== -1; })
            .sort(function (a, b) { return String(a).localeCompare(String(b), undefined, { numeric: true }); });

        if (matches.length === 0) { dropdown.style.display = "none"; return; }

        matches.forEach(function (houseNo) {
            var item = document.createElement("div");
            item.textContent = "House: " + houseNo;
            item.style.cssText = "padding:8px 12px;cursor:pointer;font-size:13px;border-bottom:1px solid #eee;";
            item.addEventListener("mouseenter", function () { this.style.background = "#f0f4ff"; });
            item.addEventListener("mouseleave", function () { this.style.background = "white"; });
            item.addEventListener("click", function () {
                searchInput.value = houseNo;
                dropdown.style.display = "none";
                focusHouseOnMap(String(houseNo));
            });
            dropdown.appendChild(item);
        });
        dropdown.style.display = "block";
    });

    document.removeEventListener("click", window._householdOutsideClick);
    window._householdOutsideClick = function (e) {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = "none";
        }
    };
    document.addEventListener("click", window._householdOutsideClick);

    searchInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            var query = this.value.trim();
            if (query) { dropdown.style.display = "none"; focusHouseOnMap(String(query)); }
        }
    });
}

function focusHouseOnMap(houseNo) {
    var shape = houses[houseNo] || houses[parseInt(houseNo)] || houses[String(houseNo)];
    if (!houses || !shape) { alert("House number " + houseNo + " not found."); return; }

    try {
        if (window._householdHighlight) {
            window._householdHighlight.closePopup();
            map.removeLayer(window._householdHighlight);
            window._householdHighlight = null;
        }
        if (window._householdHighlightTimer) {
            clearTimeout(window._householdHighlightTimer);
            window._householdHighlightTimer = null;
        }

        var highlightLayer = L.geoJson(shape, {
            style: { color: "#FFD700", weight: 4, opacity: 1, fillColor: "#FFFF00", fillOpacity: 0.6 },
            onEachFeature: function (feature, layer) {
                layer.bindPopup("House: " + houseNo, { autoPan: true });
                layer.on("mouseover", function () { this.openPopup(); });
                layer.on("mouseout", function () { this.closePopup(); });
                layer.on("click", function () { household_details(houseNo); });
            }
        });
        highlightLayer.addTo(map);
        window._householdHighlight = highlightLayer;
        highlightLayer.eachLayer(function (layer) { layer.openPopup(); });

        var bounds = highlightLayer.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { maxZoom: 19, padding: [40, 40] });
        } else {
            var coords = shape.coordinates;
            if (coords) {
                var latlng = shape.type === "Point"
                    ? L.latLng(coords[1], coords[0])
                    : L.latLng(coords[0][0][1], coords[0][0][0]);
                if (latlng) map.setView(latlng, 19);
            }
        }
    } catch (err) {
        console.error("Error focusing house on map:", err);
    }
}

function clearHouseholdHighlight() {
    if (window._householdHighlight) {
        window._householdHighlight.closePopup();
        map.removeLayer(window._householdHighlight);
        window._householdHighlight = null;
    }
    if (window._householdHighlightTimer) {
        clearTimeout(window._householdHighlightTimer);
        window._householdHighlightTimer = null;
    }
    var dd = document.getElementById("household-search-dropdown");
    if (dd) dd.style.display = "none";
}

function fullResetHouseholdSearch() {
    clearHouseholdHighlight();
    var si = document.getElementById("household-search-input");
    if (si) si.value = "";
}


/* ── Sponsor pinned section ──────────────────────────────────────────────── */
function pinSponsorToBottom(slumId) {
    var sponsorPanel = null;

    var sponsorCollapse = $("#compochk div.panel-collapse[name='Sponsor']");
    if (sponsorCollapse.length > 0) {
        sponsorPanel = sponsorCollapse.closest("[name='div_group']");
    }

    if (!sponsorPanel || sponsorPanel.length === 0) {
        $("#compochk > [name='div_group']").each(function () {
            if ($(this).find("a[name='chk_group']").text().trim().toLowerCase().indexOf("sponsor") !== -1) {
                sponsorPanel = $(this);
                return false;
            }
        });
    }

    if (!sponsorPanel || sponsorPanel.length === 0) {
        $("#compochk [name='chk1']").each(function () {
            if ($(this).val().toLowerCase().indexOf("sponsor") !== -1) {
                sponsorPanel = $(this).closest("[name='div_group']").parent().closest("[name='div_group']");
                return false;
            }
        });
    }

    if (sponsorPanel && sponsorPanel.length > 0) {
        var cloned = sponsorPanel.clone(true, true);
        sponsorPanel.remove();
        $("#sponsor-checkbox").html("").append(cloned);
        $("#sponsor-pinned").show();
    } else {
        $("#sponsor-pinned").hide();
    }

    /* initToiletTimeline is now called for ALL users ── */
    initToiletTimeline(slumId);
}
/* ── CLEAN TOILET TIMELINE ─────────────────────────────────────────────── */

var _timelineRows = [];
var _timelineAllStops = [];
var _timelineStartIndex = 0;
var _timelineActiveIndex = 0;
var _timelineLayers = [];
var _timelineHighlightColor = "#eb349e";

/* ---------- DATE HELPERS ---------- */

function _parseTimelineDate(value) {
    var d = new Date(value);
    return isNaN(d.getTime()) ? null : d;
}

function _cutoffJan(year) {
    return new Date(year, 0, 1, 23, 59, 59, 999);
}

function _cutoffMid(year) {
    return new Date(year, 5, 30, 23, 59, 59, 999);
}

/* ---------- DATA NORMALIZATION ---------- */

function _normalizeTimelineRows(monthlyData) {
    var rows = [];

    (monthlyData || []).forEach(function (item) {
        var d = _parseTimelineDate(item.month_end_date);
        if (!d) return;

        rows.push({
            date: d,
            month: item.month || "",
            month_end_date: item.month_end_date,
            house_numbers: Array.isArray(item.house_numbers) ? item.house_numbers.slice() : [],
            total: typeof item.total === "number" ? item.total : (Array.isArray(item.house_numbers) ? item.house_numbers.length : 0)
        });
    });

    rows.sort(function (a, b) {
        return a.date.getTime() - b.date.getTime();
    });

    return rows;
}

/* ---------- CUMULATIVE HOUSE COLLECTION ---------- */

function _collectHousesTillCutoff(rows, cutoffDate) {
    var seen = {};
    var out = [];

    for (var i = 0; i < rows.length; i++) {
        if (rows[i].date > cutoffDate) break;

        var nums = rows[i].house_numbers || [];
        for (var j = 0; j < nums.length; j++) {
            var h = String(nums[j]);
            if (!seen[h]) {
                seen[h] = true;
                out.push(h);
            }
        }
    }

    return out;
}

/* ---------- STOP BUILDER ---------- */
/*
    Build:
    - Jan YYYY  => cumulative till 31 Dec previous year
    - Mid YYYY  => cumulative till 30 Jun YYYY
    We also build one extra year beyond the last data year so the slider can
    show the next Jan/Mid around the last visible point.
*/
function _buildTimelineStops(rows) {
    if (!rows || rows.length === 0) {
        return { all: [], startIndex: 0 };
    }

    var firstDate = rows[0].date;
    var lastDate = rows[rows.length - 1].date;

    var firstYear = firstDate.getFullYear();
    var lastYear = lastDate.getFullYear();

    var stops = [];
    var y;

    for (y = firstYear; y <= lastYear + 1; y++) {
        var janCutoff = _cutoffJan(y);
        stops.push({
            type: "jan",
            year: y,
            label: "Jan " + y,
            cutoff: janCutoff,
            cutoffTime: janCutoff.getTime()
        });

        var midCutoff = _cutoffMid(y);
        stops.push({
            type: "mid",
            year: y,
            label: "Mid " + y,
            cutoff: midCutoff,
            cutoffTime: midCutoff.getTime()
        });
    }

    stops.sort(function (a, b) {
        return a.cutoffTime - b.cutoffTime;
    });

    for (var i = 0; i < stops.length; i++) {
        stops[i].house_numbers = _collectHousesTillCutoff(rows, stops[i].cutoff);
        stops[i].total = stops[i].house_numbers.length;
    }

    /* First visible node:
       - if first data month is Jan..Jun -> show Jan of that year
       - if first data month is Jul..Dec -> show Mid of that year
    */
    var firstType = (firstDate.getMonth() <= 5) ? "jan" : "mid";
    var startIndex = 0;

    for (var k = 0; k < stops.length; k++) {
        if (stops[k].type === firstType && stops[k].year === firstYear) {
            startIndex = k;
            break;
        }
    }

    /* 🔥 FIX LAST NODE LOGIC */

    var lastDate = rows[rows.length - 1].date;
    var lastMonth = lastDate.getMonth(); // 0–11
    var lastYear = lastDate.getFullYear();

    /* determine final allowed stop */
    var finalType;
    var finalYear;

    if (lastMonth <= 5) {
        // Jan–June → Mid same year
        finalType = "mid";
        finalYear = lastYear;
    } else {
        // July–Dec → Jan next year
        finalType = "jan";
        finalYear = lastYear + 1;
    }

    /* find index of this final stop */
    var finalIndex = stops.findIndex(function (s) {
        return s.type === finalType && s.year === finalYear;
    });

    /* cut extra stops after this */
    if (finalIndex !== -1) {
        stops = stops.slice(0, finalIndex + 1);
    }
    return {
        all: stops,
        startIndex: startIndex
    };
}

/* ---------- MAP LAYERS ---------- */

function clearTimelineLayers() {
    for (var i = 0; i < _timelineLayers.length; i++) {
        map.removeLayer(_timelineLayers[i]);
    }
    _timelineLayers = [];
}

function highlightMultipleHouses(houseList) {
    clearTimelineLayers();

    if (!houseList || !houseList.length || !houses) return;

    var filtered = [];
    var seen = {};

    for (var i = 0; i < houseList.length; i++) {
        var key = String(houseList[i]);
        if (seen[key]) continue;
        seen[key] = true;

        if (houses[key]) {
            filtered.push(houses[key]);
        } else if (houses[parseInt(key, 10)]) {
            filtered.push(houses[parseInt(key, 10)]);
        }
    }

    if (!filtered.length) return;

    var fillCol = _timelineHighlightColor;
    var strokeCol = (fillCol === "#FFD700") ? "#b8860b" : "#000000";

    var layer = L.geoJson(filtered, {
        style: {
            color: strokeCol,
            opacity: 0.8,
            weight: 1,
            fillColor: fillCol,
            fillOpacity: 0.65
        },
        onEachFeature: function (feature, layer) {
            if (feature && feature.properties && feature.properties.name) {
                var name = feature.properties.name;
                layer.bindPopup("House: " + name, { autoPan: true });
                layer.on("mouseover", function () { this.openPopup(); });
                layer.on("mouseout", function () { this.closePopup(); });
                layer.on("click", function () { household_details(name); });
            }
        }
    });

    layer.addTo(map);
    _timelineLayers.push(layer);
}

/* ---------- SLIDER HELPERS ---------- */
function _timelineSliderToIndex(value) {
    if (!_timelineAllStops.length) return 0;

    var maxIndex = _timelineAllStops.length - 1;
    var span = maxIndex - _timelineStartIndex;

    if (span <= 0) return _timelineStartIndex;

    /* 🔥 FIX: use FLOOR instead of ROUND */
    var i = _timelineStartIndex + Math.floor((value / 100) * (span + 1));

    if (i > maxIndex) i = maxIndex;
    if (i < _timelineStartIndex) i = _timelineStartIndex;

    return i;
}

function _timelineIndexToSliderValue(index) {
    if (!_timelineAllStops.length) return 0;

    var maxIndex = _timelineAllStops.length - 1;
    var span = maxIndex - _timelineStartIndex;

    if (span <= 0) return 0;

    return Math.round(((index - _timelineStartIndex) / span) * 100);
}

/* ---------- RENDER ---------- */
function renderMapTimeline() {
    var html = "";

    if (!_timelineAllStops.length) return;

    var active = _timelineActiveIndex;

    /* 🔍 find previous MID */
    var prevMid = -1;
    for (var i = active - 1; i >= 0; i--) {
        if (_timelineAllStops[i].type === "mid") {
            prevMid = i;
            break;
        }
    }

    /* 🔍 find next MID */
    var nextMid = -1;
    for (var j = active + 1; j < _timelineAllStops.length; j++) {
        if (_timelineAllStops[j].type === "mid") {
            nextMid = j;
            break;
        }
    }

    for (var k = _timelineStartIndex; k < _timelineAllStops.length; k++) {

        var stop = _timelineAllStops[k];

        /* ✅ VISIBILITY RULE */
        var show = false;

        // ALWAYS show JAN
        if (stop.type === "jan") show = true;

        // show prev + next MID
        if (k === prevMid || k === nextMid) show = true;

        // 🔥 IMPORTANT: ALWAYS show ACTIVE NODE
        if (k === active) show = true;

        if (!show) continue;

        /* ✅ ACTIVE HIGHLIGHT */
        var isActive = (k === active);
        var activeClass = "";

        if (isActive) {
            activeClass = (stop.type === "mid") ? " active" : " active-year";
        }

        html += '<span class="' +
            (stop.type === "mid" ? "tl-month" : "tl-year") +
            activeClass +
            '" data-stop="' + k + '">' +
            stop.label +
            '<small>' + stop.total + '</small>' +
            '</span>';

        html += '<span class="tl-dash">—</span>';
    }

    /* remove last dash safely */
    if (html.endsWith('—</span>')) {
        html = html.slice(0, -8);
    }

    $("#map-timeline").html(html);
}
/* ---------- NAVIGATION ---------- */

function goToTimelineStop(index, source) {
    if (!_timelineAllStops.length) return;

    var maxIndex = _timelineAllStops.length - 1;

    if (index < _timelineStartIndex) index = _timelineStartIndex;
    if (index > maxIndex) index = maxIndex;

    _timelineActiveIndex = index;
    CURRENT_INDEX = index;

    var stop = _timelineAllStops[index];

    clearTimelineLayers();

    if (stop && stop.house_numbers && stop.house_numbers.length) {
        highlightMultipleHouses(stop.house_numbers);
    }
    var slider = document.getElementById("timelineSlider");

    /* 🔥 IMPORTANT: only update slider if NOT coming from slider */
    if (slider && source !== "slider") {
        slider.value = _timelineIndexToSliderValue(index);
    }

    var readout = document.getElementById("sliderReadout");
    if (readout) {
        readout.textContent = stop ? stop.label : "Start";
    }

    renderMapTimeline();
}

/* ---------- INIT ---------- */

function initToiletTimeline(slumId) {
    if (!slumId) return;

    $("#sponsor-pinned").show();

    $("#timeline-toggle-slot").html(
        '<div style="font-size:11px;font-weight:600;margin-top:2px;margin-bottom:6px;color:#2471a3;">' +
        'Explore construction impact over time.</div>' +
        '<button id="toggleTimeline" class="action-btn">Show Impact Over Time</button>'
    );

    fetch("/component/household-month-dates/?slum_id=" + encodeURIComponent(slumId))
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (!data || !data.monthly_data || data.monthly_data.length === 0) {
                $("#timeline-toggle-slot").hide();
                return;
            }

            $("#timeline-toggle-slot").show();

            var scope = String(data.scope || "").toLowerCase();
            _timelineHighlightColor = (scope === "all" || scope === "superuser") ? "#FFD700" : "#eb349e";

            _timelineRows = _normalizeTimelineRows(data.monthly_data);

            var built = _buildTimelineStops(_timelineRows);
            _timelineAllStops = built.all || [];
            _timelineStartIndex = typeof built.startIndex === "number" ? built.startIndex : 0;

            if (!_timelineAllStops.length) {
                $("#timeline-toggle-slot").hide();
                return;
            }

            _timelineActiveIndex = _timelineStartIndex;

            var slider = document.getElementById("timelineSlider");
            if (slider) {
                slider.min = 0;
                slider.max = 100;
                slider.step = 1;
                slider.value = 0;
            }

            var readout = document.getElementById("sliderReadout");
            if (readout) {
                readout.textContent = _timelineAllStops[_timelineStartIndex].label;
            }

            renderMapTimeline();
            goToTimelineStop(_timelineStartIndex);
        })
        .catch(function () {
            $("#timeline-toggle-slot").hide();
        });
}

/* ---------- RESET ---------- */

function _resetTimeline() {
    clearTimelineLayers();

    if (_timelineAllStops.length) {
        _timelineActiveIndex = _timelineStartIndex;
        CURRENT_INDEX = _timelineStartIndex;

        var slider = document.getElementById("timelineSlider");
        if (slider) slider.value = 0;

        var readout = document.getElementById("sliderReadout");
        if (readout) readout.textContent = _timelineAllStops[_timelineStartIndex].label;
    }

    renderMapTimeline();
}

/* ---------- EVENTS ---------- */

$(document).off("click.timelineWindow click.timelinePill click.timeline", ".tl-year, .tl-month")
    .on("click.timelineWindow", ".tl-year, .tl-month", function () {
        var idx = parseInt($(this).data("stop"), 10);
        if (!isNaN(idx)) {
            goToTimelineStop(idx, "click");
        }
    });

$(document).off("input.timelineWindow input.timelineSlider input.timeline", "#timelineSlider")
    .on("input.timelineWindow", "#timelineSlider", function () {
        var val = parseFloat(this.value) || 0;
        var idx = _timelineSliderToIndex(val);
        goToTimelineStop(idx, "slider");
    });
/* ═══════════════════════════════════════════════════════════════════════════
 *OTP Flow helpers
 *
 *  sendOtpWithFeedback(btn)
 *    - Immediately disables btn and sets text to "Sending OTP…"
 *    - Calls the server (POST /rim/send-otp/)
 *    - On success: shows OTP section + starts 30-s countdown
 *    - On error:   re-enables button with original label
 *
 *  startResendCountdown(btn, seconds)
 *    - Counts down in button text: "Resend OTP in Ns"
 *    - After countdown: re-enables with "Resend OTP"
 * ═══════════════════════════════════════════════════════════════════════════ */

var _otpCountdownTimer = null;  /* module-level so we can clear on re-send */

function startResendCountdown(btn, seconds) {
    if (_otpCountdownTimer) { clearInterval(_otpCountdownTimer); }

    var remaining = seconds;
    btn.disabled = true;
    btn.textContent = "Resend OTP in " + remaining + "s";

    _otpCountdownTimer = setInterval(function () {
        remaining--;
        if (remaining <= 0) {
            clearInterval(_otpCountdownTimer);
            _otpCountdownTimer = null;
            btn.disabled = false;
            btn.textContent = "Resend OTP";
        } else {
            btn.textContent = "Resend OTP in " + remaining + "s";
        }
    }, 1000);
}

function sendOtpWithFeedback(btn) {
    /* ── Immediate visual feedback — no alert ── */
    btn.disabled = true;
    var originalText = btn.textContent;
    btn.textContent = "Sending OTP…";

    var name = document.getElementById("rimName") ? document.getElementById("rimName").value.trim() : "";
    var email = document.getElementById("rimEmail") ? document.getElementById("rimEmail").value.trim() : "";
    var mobile = document.getElementById("rimMobile") ? document.getElementById("rimMobile").value.trim() : "";

    fetch("/rim/send-otp/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": (typeof csrftoken !== "undefined" ? csrftoken : "")
        },
        body: JSON.stringify({ name: name, email: email, mobile: mobile })
    })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data && data.success) {
                /* Show OTP input section — no alert */
                var otpSection = document.getElementById("rimOTPSection");
                if (otpSection) otpSection.style.display = "block";

                /* Start 30-second resend countdown */
                startResendCountdown(btn, 30);
            } else {
                /* Server-side error — restore button */
                btn.disabled = false;
                btn.textContent = originalText;
                var msg = (data && data.error) ? data.error : "Failed to send OTP. Please try again.";
                /* Display error inline rather than alert */
                _showOtpInlineError(msg);
            }
        })
        .catch(function () {
            btn.disabled = false;
            btn.textContent = originalText;
            _showOtpInlineError("Network error. Please try again.");
        });
}

/** Renders a small error message below the Send OTP button (no alert). */
function _showOtpInlineError(msg) {
    var existing = document.getElementById("otp-inline-error");
    if (existing) existing.remove();

    var errDiv = document.createElement("div");
    errDiv.id = "otp-inline-error";
    errDiv.style.cssText = "color:#c0392b;font-size:12px;margin-top:4px;";
    errDiv.textContent = msg;

    var sendBtn = document.getElementById("rimSendOTP");
    if (sendBtn && sendBtn.parentNode) {
        sendBtn.parentNode.insertBefore(errDiv, sendBtn.nextSibling);
    }
}


/* ── Delegated event listeners (registered once) ─────────────────────────── */

/*  Replace direct click handler wiring with the new sendOtpWithFeedback */
$(document).off("click.rimSendOTP", "#rimSendOTP")
    .on("click.rimSendOTP", "#rimSendOTP", function () {
        sendOtpWithFeedback(this);
    });

/* Toggle timeline show/hide */
$(document).off("click.toggleTimeline", "#toggleTimeline")
    .on("click.toggleTimeline", "#toggleTimeline", function () {
        var container = $("#map-timeline-container");
        if (container.is(":visible")) {
            container.hide();
            $(this).text("Show Impact Over Time");
            _resetTimeline();
        } else {
            container.show();
            $(this).text("Hide Impact Over Time");
        }
    });

/* Hide timeline when Structure checkbox is unchecked */
$(document).off("click.structureWatch", "[name=chk1]")
    .on("click.structureWatch", "[name=chk1]", function () {
        if ($(this).val() === "Structure" && !$(this).is(":checked")) {
            var container = $("#map-timeline-container");
            if (container.is(":visible")) {
                container.hide();
                $("#toggleTimeline").text("Show Impact Over Time");
                _resetTimeline();
            }
        }
    });

/* Refresh confirm: open */
$(document).off("click.refreshOpen", "#refreshComponents")
    .on("click.refreshOpen", "#refreshComponents", function (e) {
        e.stopPropagation();
        $("#refreshConfirmBox").toggleClass("show");
    });

/* Refresh confirm: cancel */
$(document).off("click.refreshCancel", "#refreshConfirmNo")
    .on("click.refreshCancel", "#refreshConfirmNo", function (e) {
        e.stopPropagation();
        $("#refreshConfirmBox").removeClass("show");
    });

/* Refresh confirm: outside click */
$(document).off("click.refreshOutside")
    .on("click.refreshOutside", function (e) {
        if (!$(e.target).closest("#compochk_refresh").length) {
            $("#refreshConfirmBox").removeClass("show");
        }
    });

/* Refresh confirm: yes — force refresh */
$(document).off("click.refreshYes", "#refreshConfirmYes")
    .on("click.refreshYes", "#refreshConfirmYes", function (e) {
        e.stopPropagation();
        $("#refreshConfirmBox").removeClass("show");

        var btn = $("#refreshComponents");
        var slumId = global_slum_id;

        btn.prop("disabled", true).text("Refreshing...");
        fullResetHouseholdSearch();
        $("#compochk").html(
            '<div style="height:300px;width:100%;display:flex;align-items:center;justify-content:center;">' +
            '<div id="loading-img"></div></div>'
        );

        $.ajax({
            url: "/component/get_component/" + slumId,
            type: "GET",
            headers: { "Force-Refresh-Flag": "1" },
            success: function (result) {
                btn.prop("disabled", false).text("Refresh Components");

                Promise.all([
                    Promise.resolve(result),
                    $.ajax({ url: "/component/get_kobo_RIM_data/" + slumId, type: "GET", contenttype: "json" })
                ]).then(function (data) {
                    global_slum_id = slumId;
                    var visible = getQueryParam("mr");
                    if (visible === "1") {
                        readJSONFile("/admin/translations/?mr=" + visible, generate_filter, slumId, data[0]);
                    } else {
                        generate_filter(globalJsonData, slumId, data[0]);
                    }
                    generate_RIM(data[1]);
                });
            },
            error: function () {
                btn.prop("disabled", false).text("Refresh Components");
                $("#compochk").html(
                    '<div style="padding:10px;color:red;font-size:13px;">Failed to refresh. Please try again.</div>'
                );
            }
        });
    });


/* ── Spinner helpers ── */
function showSpinner() {
    if ($("#sra-map-spinner").length === 0) {
        $(".leaflet-container").css("position", "relative").append(
            '<div id="sra-map-spinner" style="' +
            'position:absolute;top:0;left:0;width:100%;height:100%;' +
            'background:rgba(0,0,0,0.35);z-index:9999;' +
            'display:flex;align-items:center;justify-content:center;">' +
            '<svg width="56" height="56" viewBox="0 0 56 56" xmlns="http://www.w3.org/2000/svg">' +
            '<circle cx="28" cy="28" r="22"' +
            ' fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="5"/>' +
            '<circle cx="28" cy="28" r="22"' +
            ' fill="none" stroke="#ffffff" stroke-width="5"' +
            ' stroke-linecap="round"' +
            ' stroke-dasharray="35 100"' +
            ' style="animation:sra-spin 0.9s cubic-bezier(0.4,0,0.2,1) infinite;' +
            'transform-origin:28px 28px;"/>' +
            '</svg>' +
            '</div>'
        );
    }
    if ($("#sra-spin-style").length === 0) {
        $("head").append(
            '<style id="sra-spin-style">' +
            '@keyframes sra-spin{to{transform:rotate(360deg)}}' +
            '</style>'
        );
    }
}

/* ── SRA Transformation Slider ───────────────────────────────────────────── */

/*
 * DEV ONLY — set to 0 before deploying to production.
 */
var DEV_IMAGE_DELAY = 0;

function buildTransformationSlider(slumId, photosData) {
    var months = Object.keys(photosData);
    var total = months.length;
    if (total === 0) return;

    var overlayA = null;
    var overlayB = null;
    var loadingCount = 0;

    $("#right-panel").removeClass("active");

    function hideSpinner() {
        $("#sra-map-spinner").remove();
    }

    var labelsHtml = months.map(function (m) {
        return '<span style="flex:1;text-align:center;font-size:10px;">' + m + '</span>';
    }).join('');

    $("#sra-photo-label").text(months[0]);
    $("#sra-photo-desc").text(photosData[months[0]].description || '');
    $("#sra-slider").attr("max", total - 1).val(0);
    $("#sra-slider-labels").html(labelsHtml);
    /* CHANGE 3: generic id "photo-timeline-container" used in HTML */
    $("#photo-timeline-container").show();

    function makeLeafletOverlay(month, opacity, onLoaded) {
        var p = photosData[month];
        var c = p.coordinates;

        var bounds = [
            [c.south, c.west],
            [c.north, c.east]
        ];

        var overlay = L.imageOverlay("about:blank", bounds, {
            opacity: 0,
            interactive: false,
            bubblingMouseEvents: false,
            crossOrigin: true,
            className: 'map-overlay-img'
        });

        overlay.addTo(map);

        loadingCount++;
        showSpinner();

        function attachLoadEvents(targetOpacity) {
            overlay.once('load', function () {
                overlay.setOpacity(targetOpacity);
                loadingCount--;
                if (loadingCount <= 0) { loadingCount = 0; hideSpinner(); }
                if (typeof onLoaded === 'function') onLoaded();
            });
            overlay.once('error', function () {
                loadingCount--;
                if (loadingCount <= 0) { loadingCount = 0; hideSpinner(); }
            });
        }

        if (DEV_IMAGE_DELAY > 0) {
            setTimeout(function () {
                overlay.setUrl(p.photo_url);
                attachLoadEvents(opacity);
            }, DEV_IMAGE_DELAY);
        } else {
            overlay.setUrl(p.photo_url);
            attachLoadEvents(opacity);
        }

        return overlay;
    }

    var fc = photosData[months[0]].coordinates;
    map.fitBounds([
        [fc.south, fc.west],
        [fc.north, fc.east]
    ], { padding: [0, 0], maxZoom: 18 });
    map.setZoom(map.getZoom() - 1);

    overlayA = makeLeafletOverlay(months[0], 1);
    overlayB = makeLeafletOverlay(months[Math.min(1, total - 1)], 0);

    $(document).off("input.sraSlider", "#sra-slider")
        .on("input.sraSlider", "#sra-slider", function () {
            var val = parseFloat(this.value);
            var index = Math.floor(val);
            var fraction = val - index;

            var monthA = months[index];
            var monthB = months[Math.min(index + 1, total - 1)];

            var activeMonth = fraction < 0.5 ? monthA : monthB;
            $("#sra-photo-label").text(activeMonth);
            $("#sra-photo-desc").text(photosData[activeMonth].description || '');

            if (overlayA) { map.removeLayer(overlayA); overlayA = null; }
            if (overlayB) { map.removeLayer(overlayB); overlayB = null; }

            overlayA = makeLeafletOverlay(monthA, 1 - fraction);
            overlayB = makeLeafletOverlay(monthB, fraction);

            window._sraOverlayA = overlayA;
            window._sraOverlayB = overlayB;
        });

    window._sraOverlayA = overlayA;
    window._sraOverlayB = overlayB;
}
