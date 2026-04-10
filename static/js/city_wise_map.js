/*
 * master_map_component.js
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
            '<div class="legend-item"><span class="legend-box yellow-border"></span><span>Now in SRA (Previously surveyed)</span></div>';
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
        console.log("componentData:", componentData);

        const skipStatuses = ["inactive", "sra", "road_widening"];
        if (skipStatuses.includes(componentData.status)) {
            $("#filter-container").empty();
            $("#right-panel").addClass("active");
            $("#factsheet-btn-slot").hide().html("");
            $("#household-search-wrapper").hide();
            $("#sponsor-pinned").hide();
            $("#compochk_refresh").html("");

            // ADD: hide all currently displayed polygons (the yellow SRA slum boundary)
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

    /* ---- Refresh confirm events (attached once via document delegation) ---- */
    /* NOTE: delegated handlers are registered once at the bottom of this file  */

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
            var icon = v1["icon"] || "Not specified";

            panel_component +=
                '<div name="div_group">&nbsp;&nbsp;&nbsp;' +
                '<input name="chk1" class="chk"' +
                ' style="background:' + chkcolor + ';background-color:' + chkcolor + ';"' +
                ' selection="' + k + '"' +
                ' component_type="' + v1["type"] + '"' +
                ' type="checkbox" value="' + k1 + '"' +
                ' onclick="checkSingleGroup(this);">' +
                '<a>&nbsp;' + inner_label + '</a>&nbsp;(' + child_length + ')' +
                ' <img src="' + icon + '"></input></div>';

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

    /* Remove old input entirely and create a fresh one — avoids stale
       references and stacked listeners without breaking the dropdown pointer */
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
        /* Only clear the map highlight, NOT the input value */
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

    /* Outside-click closes dropdown */
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

/* clearHouseholdHighlight — removes map marker only. Does NOT wipe input. */
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

/* fullResetHouseholdSearch — clears map marker AND input value.
   Call this only when switching slum or returning to city level. */
function fullResetHouseholdSearch() {
    clearHouseholdHighlight();
    var si = document.getElementById("household-search-input");
    if (si) si.value = "";
}


/* ── Sponsor pinned section ──────────────────────────────────────────────── */
/*
 * slumId is passed in explicitly so the fetch inside uses the correct
 * value (previously there was a slumId/slumID naming bug here).
 */
function pinSponsorToBottom(slumId) {
    var sponsorPanel = null;

    /* Find the sponsor panel by its collapse name */
    var sponsorCollapse = $("#compochk div.panel-collapse[name='Sponsor']");
    if (sponsorCollapse.length > 0) {
        sponsorPanel = sponsorCollapse.closest("[name='div_group']");
    }

    /* Fallback: label text contains "sponsor" */
    if (!sponsorPanel || sponsorPanel.length === 0) {
        $("#compochk > [name='div_group']").each(function () {
            if ($(this).find("a[name='chk_group']").text().trim().toLowerCase().indexOf("sponsor") !== -1) {
                sponsorPanel = $(this);
                return false;
            }
        });
    }

    /* Fallback: checkbox value contains "sponsor" */
    if (!sponsorPanel || sponsorPanel.length === 0) {
        $("#compochk [name='chk1']").each(function () {
            if ($(this).val().toLowerCase().indexOf("sponsor") !== -1) {
                sponsorPanel = $(this).closest("[name='div_group']").parent().closest("[name='div_group']");
                return false;
            }
        });
    }

    if (!sponsorPanel || sponsorPanel.length === 0) { $("#sponsor-pinned").hide(); return; }

    var cloned = sponsorPanel.clone(true, true);
    sponsorPanel.remove();
    $("#sponsor-checkbox").html("").append(cloned);
    $("#sponsor-pinned").show();

    /* Timeline toggle button — same .action-btn style as factsheet button */
    $("#sponsor-slider").html(
        '<div style="font-size:11px;font-weight:600;margin-top:2px;margin-bottom:6px;color:#2471a3;">' +
        "Explore how your contribution created impact over time.</div>" +
        '<button id="toggleTimeline" class="action-btn">Show Impact Over Time</button>'
    );

    if (slumId) {
        fetch("/component/household-month-dates/?slum_id=" + slumId)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                TIMELINE_DATA = groupByYear(data.monthly_data);
                TIMELINE_YEARS = Object.keys(TIMELINE_DATA).sort(function (a, b) { return a - b; });
                CURRENT_INDEX = -1;

                _sliderStops = buildSliderStops();
                _currentStopIndex = 0;

                var slider = document.getElementById("timelineSlider");
                if (slider) { slider.min = 0; slider.max = 100; slider.step = 1; slider.value = 0; }

                var readout = document.getElementById("sliderReadout");
                if (readout) readout.textContent = "Start";

                renderMapTimeline();
            });
    }
}


/* ── Timeline layer helpers ──────────────────────────────────────────────── */
var _timelineLayers = [];

function groupByYear(data) {
    var result = {};
    data.forEach(function (item) {
        var year = new Date(item.month_end_date).getFullYear();
        if (!result[year]) result[year] = [];
        result[year].push(item);
    });
    return result;
}

function buildSliderStops() {
    var stops = [];
    var totalYears = TIMELINE_YEARS.length;

    stops.push({ type: "start", label: "Start", yearIndex: -1, endMonthIndex: -1 });

    TIMELINE_YEARS.forEach(function (year, yi) {
        var months = TIMELINE_DATA[year] || [];
        var midIdx = Math.floor(months.length / 2);
        var midTotal = months.slice(0, midIdx + 1).reduce(function (s, m) { return s + m.total; }, 0);
        var fullTotal = months.reduce(function (s, m) { return s + m.total; }, 0);
        var isLast = yi === totalYears - 1;

        if (isLast && months.length > 0) {
            var lastMonth = new Date(months[months.length - 1].month_end_date).getMonth();

            if (lastMonth <= 5) {
                /* Case A: ends first half */
                if (yi > 0) stops.push({ type: "mid", label: "Mid " + year, year: year, yearIndex: yi, endMonthIndex: midIdx, total: midTotal });
                stops.push({ type: "year", label: String(year), year: year, yearIndex: yi, endMonthIndex: midIdx, total: midTotal, isMidOnly: true });
            } else if (lastMonth <= 10) {
                /* Case B: ends second half, not December */
                if (yi > 0) stops.push({ type: "mid", label: "Mid " + year, year: year, yearIndex: yi, endMonthIndex: midIdx, total: midTotal });
                stops.push({ type: "year", label: String(year), year: year, yearIndex: yi, endMonthIndex: months.length - 1, total: fullTotal });
                stops.push({ type: "end", label: "End " + year, year: year, yearIndex: yi, endMonthIndex: months.length - 1, total: fullTotal });
            } else {
                /* Case C: complete year */
                if (yi > 0) stops.push({ type: "mid", label: "Mid " + year, year: year, yearIndex: yi, endMonthIndex: midIdx, total: midTotal });
                stops.push({ type: "year", label: String(year), year: year, yearIndex: yi, endMonthIndex: months.length - 1, total: fullTotal });
            }
        } else {
            if (yi > 0) stops.push({ type: "mid", label: "Mid " + year, year: year, yearIndex: yi, endMonthIndex: midIdx, total: midTotal });
            stops.push({ type: "year", label: String(year), year: year, yearIndex: yi, endMonthIndex: months.length - 1, total: fullTotal });
        }
    });

    return stops;
}

function goToTimelineStop(stopIndex, source) {
    _currentStopIndex = stopIndex;
    var stop = _sliderStops[stopIndex];

    if (source !== "slider") {
        var slider = document.getElementById("timelineSlider");
        if (slider) slider.value = _stopIndexToSliderVal(stopIndex);
    }

    var readout = document.getElementById("sliderReadout");
    if (readout) readout.textContent = stop ? stop.label : "—";

    if (!stop || stop.type === "start") {
        clearTimelineLayers();
        CURRENT_INDEX = -1;
    } else {
        highlightMultipleHouses(collectHousesTillMonthGroup(stop.year, stop.endMonthIndex));
        CURRENT_INDEX = stop.yearIndex;
    }

    renderMapTimeline();
}

function buildMonthGroups(year) {
    var months = TIMELINE_DATA[year] || [];
    if (months.length === 0) return [];
    var midIndex = Math.floor(months.length / 2);
    return [{
        label: "Mid " + year,
        total: months.slice(0, midIndex + 1).reduce(function (sum, m) { return sum + m.total; }, 0),
        groupIndex: 0,
        year: year,
        endMonthIndex: midIndex
    }];
}

function renderMapTimeline() {
    var html = "";
    var totalYears = TIMELINE_YEARS.length;
    var activeStop = _sliderStops[_currentStopIndex] || null;
    var activeYearStr = activeStop ? String(activeStop.year) : null;
    var endStopIdx = _sliderStops.findIndex(function (s) { return s.type === "end"; });

    TIMELINE_YEARS.forEach(function (year, i) {
        var isLastYear = i === totalYears - 1;
        var isFirstYear = i === 0;
        var months = TIMELINE_DATA[year] || [];
        var isThisYearActive = activeYearStr === String(year);

        var yearStopIdx = _sliderStops.findIndex(function (s) { return s.type === "year" && String(s.year) === String(year); });
        var yearStop = yearStopIdx !== -1 ? _sliderStops[yearStopIdx] : null;
        var midStopIdx = _sliderStops.findIndex(function (s) { return s.type === "mid" && String(s.year) === String(year); });

        /* Mid pill */
        if (!isFirstYear && isThisYearActive && months.length > 0 && midStopIdx !== -1) {
            var midStop = _sliderStops[midStopIdx];
            var isActive = _currentStopIndex === midStopIdx;
            html += '<span class="timeline-month' + (isActive ? " active" : "") + '" data-stop="' + midStopIdx + '" data-year="' + year + '">' +
                "Mid " + year + "<small>" + midStop.total + "</small></span>" +
                '<span class="timeline-dash">—</span>';
        }

        /* Year pill */
        var isActiveYear = _currentStopIndex === yearStopIdx;
        var isMidOnly = yearStop && yearStop.isMidOnly;
        var yearLabel = isMidOnly ? "Mid " + year : String(year);
        html += '<span class="timeline-year' + (isActiveYear ? " active-year" : "") + '" data-stop="' + yearStopIdx + '" data-year="' + year + '" data-index="' + i + '">' +
            yearLabel + '<small>' + (isActiveYear ? "▲" : "▼") + "</small></span>" +
            '<span class="timeline-dash">—</span>';

        /* End pill (Case B only) */
        if (isLastYear && endStopIdx !== -1) {
            var terminusVisible = (_currentStopIndex === yearStopIdx || _currentStopIndex === endStopIdx);
            if (terminusVisible) {
                var endStop = _sliderStops[endStopIdx];
                var isActive = _currentStopIndex === endStopIdx;
                html += '<span class="timeline-month' + (isActive ? " active" : "") + '" data-stop="' + endStopIdx + '" data-year="' + year + '">' +
                    "End " + year + "<small>" + endStop.total + "</small></span>" +
                    '<span class="timeline-dash">—</span>';
            }
        }
    });

    $("#map-timeline").html(html);
}

function collectHousesTillYear(yearIndex) {
    var houseList = [];
    for (var i = 0; i <= yearIndex; i++) {
        TIMELINE_DATA[TIMELINE_YEARS[i]].forEach(function (m) { houseList.push.apply(houseList, m.house_numbers); });
    }
    return houseList;
}

function collectHousesTillMonthGroup(year, endMonthIndex) {
    var collected = [];
    var yearIndex = TIMELINE_YEARS.indexOf(String(year));
    for (var i = 0; i < yearIndex; i++) {
        TIMELINE_DATA[TIMELINE_YEARS[i]].forEach(function (m) { collected.push.apply(collected, m.house_numbers); });
    }
    var months = TIMELINE_DATA[year] || [];
    for (var i = 0; i <= endMonthIndex; i++) {
        if (months[i]) collected.push.apply(collected, months[i].house_numbers);
    }
    return collected;
}

function highlightMultipleHouses(houseList) {
    clearTimelineLayers();
    var filter_houses = houseList.filter(function (h) { return h in houses; }).map(function (h) { return houses[h]; });
    if (filter_houses.length === 0) return;

    var layer = L.geoJson(filter_houses, {
        style: { color: "#000000", opacity: 0.7, weight: 0.25, fillColor: "#eb349e", fillOpacity: 2 },
        onEachFeature: function (feature, layer) {
            if (feature.properties && feature.properties.name) {
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

function clearTimelineLayers() {
    _timelineLayers.forEach(function (l) { map.removeLayer(l); });
    _timelineLayers = [];
}

function _resetTimeline() {
    clearTimelineLayers();
    _currentStopIndex = 0;
    CURRENT_INDEX = -1;
    var slider = document.getElementById("timelineSlider");
    if (slider) slider.value = 0;
    var readout = document.getElementById("sliderReadout");
    if (readout) readout.textContent = "Start";
    renderMapTimeline();
}


/* ── Delegated event listeners (registered once) ─────────────────────────── */

/* Timeline pill click */
$(document).off("click.timelinePill", ".timeline-year, .timeline-month")
    .on("click.timelinePill", ".timeline-year, .timeline-month", function () {
        var stopIdx = parseInt($(this).data("stop"));
        if (!isNaN(stopIdx)) goToTimelineStop(stopIdx, "pill");
    });

/* Slider input */
$(document).off("input.timelineSlider", "#timelineSlider")
    .on("input.timelineSlider", "#timelineSlider", function () {
        goToTimelineStop(_sliderValToStopIndex(parseInt(this.value)), "slider");
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
        var slumId = global_slum_id;   /* use the module-level variable — no naming bug */

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


/* ── SRA Transformation Slider ───────────────────────────────────────────── */
function buildTransformationSlider(slumId, photosData) {
    var months = Object.keys(photosData);
    var total = months.length;
    if (total === 0) return;

    var overlayA = null;
    var overlayB = null;

    $("#right-panel").removeClass("active");

    /* Build label pills */
    var labelsHtml = months.map(function (m) {
        return '<span style="flex:1;text-align:center;font-size:10px;">' + m + '</span>';
    }).join('');

    /* Populate top overlay container */
    $("#sra-photo-label").text(months[0]);
    $("#sra-photo-desc").text(photosData[months[0]].description || '');
    $("#sra-slider").attr("max", total - 1).val(0);
    $("#sra-slider-labels").html(labelsHtml);
    $("#sra-timeline-container").show();

    /* ── Helper: build a Leaflet imageOverlay from a month key ── */
    function makeLeafletOverlay(month, opacity) {
        var p = photosData[month];
        var c = p.coordinates;

        var bounds = [
            [c.south, c.west],
            [c.north, c.east]
        ];

        var overlay = L.imageOverlay(p.photo_url, bounds, {
            opacity: opacity,
            interactive: false,
            bubblingMouseEvents: false,
            crossOrigin: true,
            className: 'sra-overlay-img'
        });
        overlay.addTo(map);
        return overlay;
    }

    /* Fit Leaflet map to first photo bounds — tighter zoom */
    var fc = photosData[months[0]].coordinates;
    map.fitBounds([
        [fc.south, fc.west],
        [fc.north, fc.east]
    ], { padding: [0, 0], maxZoom: 18 });
    map.setZoom(map.getZoom() - 1);
    /* Initial overlays */
    overlayA = makeLeafletOverlay(months[0], 1);
    overlayB = makeLeafletOverlay(months[Math.min(1, total - 1)], 0);

    /* ── Slider crossfade ── */
    $(document).off("input.sraSlider", "#sra-slider")
        .on("input.sraSlider", "#sra-slider", function () {
            var val = parseFloat(this.value);
            var index = Math.floor(val);
            var fraction = val - index;

            var monthA = months[index];
            var monthB = months[Math.min(index + 1, total - 1)];

            /* Update label */
            var activeMonth = fraction < 0.5 ? monthA : monthB;
            $("#sra-photo-label").text(activeMonth);
            $("#sra-photo-desc").text(photosData[activeMonth].description || '');

            /* Remove old overlays cleanly */
            if (overlayA) { map.removeLayer(overlayA); overlayA = null; }
            if (overlayB) { map.removeLayer(overlayB); overlayB = null; }

            /* Add new overlays at correct opacities */
            overlayA = makeLeafletOverlay(monthA, 1 - fraction);
            overlayB = makeLeafletOverlay(monthB, fraction);
        });

    /* ── Cleanup when leaving this slum ── */
    /*  Store refs so slum_data_fetch / City.click can remove them */
    window._sraOverlayA = overlayA;
    window._sraOverlayB = overlayB;
}