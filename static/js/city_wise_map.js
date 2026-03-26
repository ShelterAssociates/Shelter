/*
*  Library to parse and display below elements,
*   1. Admin ward
*   2. Electoral ward
*   3. Slum
*   4. Component/Filter/Sponsor
*   5. RIM data
*/
//Admin, Electoral, Slum map variables
let length_of_components = { "Dambar road": 75140, "Cement/Concrete": 34648, "Interlocking": 24264, "Kharanja": 20767, "Kutcha road": 96744, "Existing Drainage Line": 383, "Location of Kutcha Open Nali (Gutter)": 5266, "Location of Pucca Closed Nali (Gutter)": 5581, "Location of Pucca Open Nali (Gutter)": 59665, "Location of Nahar": 23136, "Location of Nala": 6907 };
let WARDLEVEL = ["AdministrativeWard",
    "ElectoralWard",
    "Slum"];
let parse_data = {};
let map = null;
let arr_poly_disp = [];
let legends = [];
let city = null;
let objBreadcrumb = null;
let houses = null;
//Components/filter variables
let zindex = 0;
let global_slum_id = 0;
let lst_sponsor = [];
let parse_component = {};
let globalJsonData = {};
let modelsection = {
    "General": "General information",
    "Toilet": "Status of sanitation (pre SBM)",
    "Water": "Type of water connection",
    "Waste": "Facility of solid waste collection",
    "Drainage": "Drainage/open gutter information",
    "Road": "Road & access information",
    "Gutter": "Gutter information"
};
let TYPE_COMPONENT = {
    'C': 'Component',
    'S': 'Sponsor',
    'F': 'Filter'
};
var myCustomColour = '#583470'
var markerHtmlStyles = 'background-color: myCustomColour;width: 3rem;height: 3rem;display: block;left: -1.5rem;top: -1.5rem;position: relative;border-radius: 3rem 3rem 0;transform: rotate(45deg);border: 1px solid #FFFFFF';
let TIMELINE_YEARS = [];
let TIMELINE_DATA = {};
let CURRENT_INDEX = 0;

//Parser to Initiates the objects depending on admin, elect, slum
var Parser = (function () {
    function Parser(index, data) {
        this.index = index;
        this.data = data;
    }
    //Render through each and every level and return above class objects
    Parser.prototype.render = function () {

        let wards = {};
        let w_data = {}
        let ward = this.ward_data();
        wards[this.data.name] = { "obj": ward, /*"name":this.data.name,*/ /*"content":{}*/ }
            ;
        if (this.data.content != undefined && this.data.content != null) {
            let _this = this;
            legends.push((this.data.name).trim());
            $.each(this.data.content, function (key, value) {

                let objParse = new Parser(_this.index + 1, value);
                let ward = objParse.render();

                $.extend(w_data, ward);
            });
            legends.pop();
            wards[this.data.name]["content"] = w_data;
        }

        return wards;
    }
    // Some custom setup before creating above objects
    Parser.prototype.ward_data = function () {
        let dataval = $.extend({}, this.data);
        delete dataval['content'];
        dataval['type'] = WARDLEVEL[this.index];
        var details = [];
        $.extend(details, legends);
        dataval['legend'] = details || [];
        let ward = new (eval(WARDLEVEL[this.index]))(dataval);
        ward.setListeners();
        return ward;
    }
    return Parser;
}());

function initMap12() {

    $(".overlay").show();
    var city_id = $("#city_id").val();
    var city_name = $("#city_name").val();
    $.ajax({
        url: "/admin/slummapdisplay/" + city_id + "/",
        type: "GET",
        contenttype: "json",
        success: function (json) {
            let data = json['content'];
            city = new City(city_name);
            $.each(data, function (key, value) {
                let obj_parser = new Parser(0, value);
                let ward = obj_parser.render();
                $.extend(parse_data, ward);
            });
            objBreadcrumb = new Breadcrumbs([]);

            //slum name is put in the search box and enter is fired, the irt search result is loaded
            $(document).ready(function () {
                var slumname = $('#slum_name').val();
                if (slumname != "") {
                    var slum_input = $("#datatable_filter").find("input");
                    slum_input.val(slumname);
                    slum_input.keyup();
                    $("#datatable span").get(0).click();
                }
            });

            $(".overlay").hide();
        }
    });
}

function initMap() {
    let center_data = {
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
        "Ichalkaranji": new L.LatLng(16.68803567359255879, 74.46583551598165229),
        "Banthara Town": new L.LatLng(26.6890600000000, 80.81704000000000)
    };
    var pos = new L.LatLng(18.640083, 73.825560);
    if ($('#city_name').val() in center_data) {
        pos = center_data[$('#city_name').val()];
    }

    map = new L.Map('map', {
        center: pos,
        zoom: 12,
        zoomSnap: 0.25,
        markerZoomAnimation: false
    });
    // Changing Zoom level for Pune District.
    const cityArray = ['Pune District', 'Nilgiri District']
    if (cityArray.includes($('#city_name').val())) {
        map.setZoom(9);
    };
    var ggl = L.gridLayer.googleMutant({ type: 'satellite' }).addTo(map);
    initMap12();
}

function getQueryParam(param) {
    const params = new URLSearchParams(window.location.search);
    return params.get(param);
}


function readJSONFile(filePath, callback, param1, param2) {
    return fetch(filePath)
        .then(response => response.json())
        .then(data => {
            callback(data, param1, param2);  // Assign the JSON response to a global variable
        })
        .catch(error => {
            console.error('Error fetching JSON data:', error);
        });
}

function slum_data_fetch(slumId) {
    $("#right-panel").addClass("active");

    // Clear any existing household highlight when switching slum
    if (window._householdHighlight) {
        window._householdHighlight.closePopup();
        map.removeLayer(window._householdHighlight);
        window._householdHighlight = null;
    }

    // Render refresh button in right panel
    // Render refresh button in right panel
    let compochk_refresh = $("#compochk_refresh");

    fetch('/component/can-refresh-section/')
        .then(res => res.json())
        .then(data => {

            if (data.can_refresh) {
                compochk_refresh.html(`
                <div style="position:relative;">
                    <button id="refreshComponents"
                        class="btn btn-primary btn-xs"
                        style="width:100%;
                               margin-bottom:0px;
                               font-size:12px;
                               border-radius:4px;
                               padding:4px 8px;">
                        Refresh Components
                    </button>

                    <div class="refresh-confirm-box" id="refreshConfirmBox">
                        <h5>Refresh Components?</h5>
                        <p>
                            Clicking <strong>Yes</strong> will clear cached data
                            and reload fresh from server.
                        </p>
                        <div class="refresh-confirm-actions">
                            <button class="btn btn-default btn-xs" id="refreshConfirmNo">Cancel</button>
                            <button class="btn btn-primary btn-xs" id="refreshConfirmYes">Yes, Refresh</button>
                        </div>
                    </div>
                </div>
            `);
            } else {
                compochk_refresh.html(""); // ❌ hide if no permission
            }

        })
        .catch(err => {
            compochk_refresh.html(""); // fail safe → hide
        });

    // Show confirm box below button
    $(document).off("click", "#refreshComponents").on("click", "#refreshComponents", function (e) {
        e.stopPropagation();
        $("#refreshConfirmBox").toggleClass("show");
    });

    // Close on cancel
    $(document).off("click", "#refreshConfirmNo").on("click", "#refreshConfirmNo", function (e) {
        e.stopPropagation();
        $("#refreshConfirmBox").removeClass("show");
    });

    // Close on outside click
    $(document).off("click.refreshOutside").on("click.refreshOutside", function (e) {
        if (!$(e.target).closest('#compochk_refresh').length) {
            $("#refreshConfirmBox").removeClass("show");
        }
    });

    // Yes — do the refresh
    $(document).off("click", "#refreshConfirmYes").on("click", "#refreshConfirmYes", function (e) {
        e.stopPropagation();
        $("#refreshConfirmBox").removeClass("show");

        let btn = $("#refreshComponents");
        btn.prop("disabled", true).text("Refreshing...");

        // Clear search box
        var searchInput = document.getElementById('household-search-input');
        if (searchInput) searchInput.value = '';
        var dropdown = document.getElementById('household-search-dropdown');
        if (dropdown) dropdown.style.display = 'none';

        // Clear household highlight
        if (window._householdHighlight) {
            window._householdHighlight.closePopup();
            map.removeLayer(window._householdHighlight);
            window._householdHighlight = null;
        }

        // Show loading in compochk
        $("#compochk").html('<div style="height:300px;width:100%;display:flex;align-items:center;justify-content:center;"><div id="loading-img"></div></div>');

        // Call API with force refresh flag
        $.ajax({
            url: `/component/get_component/${slumId}`,
            type: "GET",
            headers: {
                "Force-Refresh-Flag": "1"
            },
            success: function (result) {
                btn.prop("disabled", false).text("Refresh Components");

                Promise.all([
                    Promise.resolve(result),
                    $.ajax({
                        url: '/component/get_kobo_RIM_data/' + slumId,
                        type: "GET",
                        contenttype: "json"
                    })
                ]).then(function (data) {
                    global_slum_id = slumId;
                    const visible = getQueryParam('mr');
                    if (visible == '1') {
                        readJSONFile(`/admin/translations/?mr=${visible}`, generate_filter, slumId, data[0]);
                    } else {
                        generate_filter(globalJsonData, slumId, data[0]);
                    }
                    generate_RIM(data[1]);
                });
            },
            error: function () {
                btn.prop("disabled", false).text("Refresh Components");
                $("#compochk").html('<div style="padding:10px;color:red;font-size:13px;">Failed to refresh. Please try again.</div>');
            }
        });
    });
    // Initial load
    let compochk = $("#compochk");
    compochk.html('<div style="height:300px;width:100%;display:flex;align-items:center;justify-content:center;"><div id="loading-img"></div></div>');

    var ajax_calls = [
        $.ajax({
            url: '/component/get_component/' + slumId,
            type: "GET",
            contenttype: "json",
            headers: {
                "Force-Refresh-Flag": "0"
            }
        }),
        $.ajax({
            url: '/component/get_kobo_RIM_data/' + slumId,
            type: "GET",
            contenttype: "json"
        })
    ];

    Promise.all(ajax_calls).then(function (result) {
        global_slum_id = slumId;
        const visible = getQueryParam('mr');
        if (visible == '1') {
            readJSONFile(`/admin/translations/?mr=${visible}`, generate_filter, slumId, result[0]);
        } else {
            generate_filter(globalJsonData, slumId, result[0]);
        }
        generate_RIM(result[1]);
    });
}

//Populate RIM data modal pop-up's as per section wise.
function generate_RIM(result) {
    $("#rim").html('');
    if ('General' in result) {
        try {
            result['General']['admin_ward'] = objBreadcrumb.val[0];
            result['General']['slum_name'] = objBreadcrumb.val[2];
        } catch (e) { }
    }
    $.each(result, function (k, v) {
        let modal = $("#myModal").clone();
        modal.find('#modelhdtext').html(modelsection[k]);
        modal.attr({ 'id': k });
        let spstr = "";
        let commentstr = "";
        spstr += '<table class="table table-striped"  style="margin-bottom:0px;font-size: 12px;">';

        if (v instanceof Array) {
            modal.find('div.modal-dialog').addClass("modal-lg");
            let toilet_header = "<thead><tr><th>&nbsp;</th>";
            let toilet_body = "<tbody>";
            for (i = 0; i < v.length; i++) {
                if (v[i].hasOwnProperty("ctb_name")) {
                    toilet_header += "<th> " + v[i]["ctb_name"] + "</th>";
                    delete v[i]["ctb_name"]
                } else {
                    toilet_header += "<th> CTB" + (i + 1) + "</th>";
                };
            }
            toilet_header += "</tr></thead>";
            if (v.length > 0) {
                // Making a array cosisting all keys which available in toilet data.
                keys_headers2 = Object.keys(v[0]);
                for (j = 1; j < v.length; j++) {
                    keys_headers1 = Object.keys(v[j]);
                    keys_headers2 = keys_headers2.concat(keys_headers1);
                }
                // Removing duplicates from  all keys_headers2 which available in toilet data.
                function removeDuplicates(arr) {
                    return arr.filter((item,
                        index) => arr.indexOf(item) === index);
                }
                keys_headers = removeDuplicates(keys_headers2);
                $.each(keys_headers.slice(0, keys_headers.length), function (key, val) {
                    toilet_body += '<tr><td style="font-weight:bold;width:200px;">' + val + '</td>';
                    for (i = 0; i < v.length; i++) {
                        value = v[i][val];
                        if (value == undefined)
                            value = "None";
                        toilet_body += '<td>' + value + '</td>';
                    }
                    toilet_body += '</tr>';
                });
            }
            else {
                toilet_body += '<tr><td>No CTB\'s</td></tr>';
            }
            spstr += toilet_header + toilet_body;
        }
        else {
            modal.find('div.modal-dialog').removeClass('modal-lg');
            spstr += "<tbody>";
            $.each(v, function (key, val) {
                if (key.indexOf("comment") != -1 || key.indexOf("Describe") != -1) {
                    commentstr += '<tr><td  colspan=2><label style="font-weight:bold;">' + key + ': </label> ' + val + '</td></tr>';
                } else {
                    spstr += '<tr><td style="font-weight:bold;width:50%;">' + key + '</td><td>' + val + '</td></tr>';
                }

            });
        }
        spstr += commentstr + '</tbody></table>';
        modal.find('#modelbody').html(spstr);
        $("#rim").append(modal);

        $("div.panel-collapse[name='" + modelsection[k] + "']").prepend('<div name="div_group" >' + '&nbsp;&nbsp;&nbsp;' + '<span><a style="cursor:pointer;color:darkred;" data-toggle="modal" data-target="#' + k + '">View Tabular Data</a><span>' + '</div>');
    });
}
// Generates right filter
function generate_filter(globalJsonData, slumID, result) {
    let compochk = $("#compochk");
    let counter = 0;
    let panel_component = "";
    $.each(result, function (k, v) {
        counter = counter + 1;
        panel_component_value = Object.keys(globalJsonData).length > 0 ? globalJsonData[k] : k;
        panel_component += '<div name="div_group" class=" panel  panel-default panel-heading"> ' +
            '<input class="chk" name="grpchk" type="checkbox" onclick="checkAllGroup(this)"></input>&nbsp;&nbsp;<a name="chk_group" data-toggle="collapse" data-parent="#compochk" href="#' + counter + '"><b><span>' + panel_component_value + '</span></b></a>' +
            '</br>'

        panel_component += '<div id="' + counter + '" class="panel-collapse collapse" name="' + k + '">';
        $.each(v, function (k1, v1) {
            let chkcolor = v1['blob']['polycolor'];
            inner_panel_component_value = Object.keys(globalJsonData).length > 0 ? globalJsonData[k1] : k1;
            let child_length = null;
            if (k1 in length_of_components) {
                child_length = length_of_components[k1] + " mtr";
            } else {
                child_length = v1['child'].length;
            };
            let icon = v1['icon'] ?? "Not specified";
            panel_component += '<div name="div_group" >' + '&nbsp;&nbsp;&nbsp;' +
                '<input name="chk1" class="chk" style="background:' + chkcolor + ';background-color:' + chkcolor + '; " selection="' + k + '" component_type="' + v1['type'] + '" type="checkbox" value="' + k1 + '" onclick="checkSingleGroup(this);" >' +
                '<a>&nbsp;' + inner_panel_component_value + '</a>&nbsp;(' + child_length + ') <img src="' + icon + '">' +
                '</input>' +
                '</div>';
            if (k1 == "Structure" || k1 == 'Admin Ward Area') {
                houses = {};
                $.each(v1['child'], function (k2, v2) {
                    v2.shape['properties'] = {};
                    v2.shape.properties['name'] = v2.housenumber;
                    if (k1 == 'Admin Ward Area') {
                        v2.shape.properties['Level'] = 'Admin';
                    }
                    houses[v2.housenumber] = v2.shape;
                });
            }
            let obj = eval('new ' + TYPE_COMPONENT[v1.type] + '(v1)');
            parse_component[k1] = obj;
        });

        panel_component += '</div></div>';
    });
    compochk.html(panel_component);
    setTimeout(function () {
        var autoSelect = null;

        // Try to find 'Town boundary' checkbox first
        $('[name=chk1]').each(function () {
            var val = $(this).val();
            if (
                val === 'Town boundary' ||
                val === 'Slum boundary'
            ) {
                autoSelect = $(this);
                return false; // break loop
            }
        });

        if (autoSelect && !autoSelect.is(':checked')) {
            autoSelect.click();
        }

    }, 300); // small delay to ensure DOM is ready
    // ← ADD THIS
    setTimeout(function () {
        pinSponsorToBottom();
    }, 400);
    initHouseholdSearch();
}


//Event handler for checkbox selection for the filter ON / OFF
function checkSingleGroup(singlechk) {
    /*if(arr_poly_disp.length > 0){
        arr_poly_disp[0].setMap(null);
        arr_poly_disp = [];
    } */
    $.each(arr_poly_disp, function (k, v) {
        //v.setMap(null);
        map.removeLayer(v.shape);
    });

    var chkchild = $(singlechk).val();
    var section = $(singlechk).attr('selection');
    var component_type = $(singlechk).attr('component_type');
    if ($(singlechk).is(':checked')) {
        parse_component[chkchild].show();
    }
    else {
        parse_component[chkchild].hide();
    }
    let flag = false;
    if ($(singlechk).parent().parent().parent().find('[name=chk1]:checked').length > 0)
        flag = true;
    $(singlechk).parent().parent().parent().find('[name=grpchk]')[0].checked = flag;
    //    map.setZoom(l+1);
}

// ============================================================
// HOUSEHOLD SEARCH - focuses map on selected household
// ============================================================
function initHouseholdSearch() {
    $.each(arr_poly_disp, function (k, v) {
        if (v.type === 'Slum') {
            map.removeLayer(v.shape);
        }
    });
    var searchInput = document.getElementById('household-search-input');
    var dropdown = document.getElementById('household-search-dropdown');
    var wrapper = document.getElementById('household-search-wrapper');

    if (!searchInput) return;

    wrapper.style.display = 'block';

    // Clone and replace to remove all previously stacked listeners
    var newInput = searchInput.cloneNode(true);
    searchInput.parentNode.replaceChild(newInput, searchInput);
    searchInput = newInput;

    searchInput.addEventListener('input', function () {

        // Clear highlight immediately when typing starts
        if (window._householdHighlight) {
            window._householdHighlight.closePopup();
            map.removeLayer(window._householdHighlight);
            window._householdHighlight = null;
        }
        if (window._householdHighlightTimer) {
            clearTimeout(window._householdHighlightTimer);
            window._householdHighlightTimer = null;
        }

        var query = this.value.trim().toLowerCase();
        dropdown.innerHTML = '';

        if (!query || !houses || Object.keys(houses).length === 0) {
            dropdown.style.display = 'none';
            return;
        }

        var matches = Object.keys(houses).filter(function (houseNo) {
            return String(houseNo).toLowerCase().indexOf(query) !== -1;
        });

        if (matches.length === 0) {
            dropdown.style.display = 'none';
            return;
        }

        matches.sort(function (a, b) {
            return String(a).localeCompare(String(b), undefined, { numeric: true });
        });

        matches.forEach(function (houseNo) {
            var item = document.createElement('div');
            item.textContent = 'House: ' + houseNo;
            item.style.cssText = 'padding:8px 12px; cursor:pointer; font-size:13px; border-bottom:1px solid #eee;';

            item.addEventListener('mouseenter', function () {
                this.style.background = '#f0f4ff';
            });
            item.addEventListener('mouseleave', function () {
                this.style.background = 'white';
            });

            item.addEventListener('click', function () {
                searchInput.value = houseNo;
                dropdown.style.display = 'none';
                focusHouseOnMap(String(houseNo));
            });

            dropdown.appendChild(item);
        });

        dropdown.style.display = 'block';
    });

    // Remove old outside click listener and attach fresh one
    document.removeEventListener('click', window._householdOutsideClick);
    window._householdOutsideClick = function (e) {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    };
    document.addEventListener('click', window._householdOutsideClick);

    searchInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            var query = this.value.trim();
            if (query) {
                dropdown.style.display = 'none';
                focusHouseOnMap(String(query));
            }
        }
    });
}

// Focus the map on a given house number
function focusHouseOnMap(houseNo) {
    // Try both string and number lookup
    var shape = houses[houseNo] || houses[parseInt(houseNo)] || houses[String(houseNo)];

    if (!houses || !shape) {
        alert('House number ' + houseNo + ' not found.');
        return;
    }

    try {
        // Draw a temporary highlight layer
        var highlightStyle = {
            color: '#FFD700',
            weight: 4,
            opacity: 1,
            fillColor: '#FFFF00',
            fillOpacity: 0.6
        };

        // Remove previous highlight if any
        if (window._householdHighlight) {
            window._householdHighlight.closePopup();
            map.removeLayer(window._householdHighlight);
            window._householdHighlight = null;
        }

        // Clear previous auto-remove timer if any
        if (window._householdHighlightTimer) {
            clearTimeout(window._householdHighlightTimer);
            window._householdHighlightTimer = null;
        }

        var highlightLayer = L.geoJson(shape, {
            style: highlightStyle,
            onEachFeature: function (feature, layer) {
                // Show house number on hover
                layer.bindPopup('House: ' + houseNo, { autoPan: true });

                layer.on('mouseover', function () {
                    this.openPopup();
                });
                layer.on('mouseout', function () {
                    this.closePopup();
                });

                // Show household details on click
                layer.on('click', function () {
                    household_details(houseNo);
                });
            }
        });

        highlightLayer.addTo(map);
        window._householdHighlight = highlightLayer;

        // Open popup immediately on search
        highlightLayer.eachLayer(function (layer) {
            layer.openPopup();
        });

        // Fit map to the house bounds
        var bounds = highlightLayer.getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds, { maxZoom: 19, padding: [40, 40] });
        } else {
            // Fallback for Point geometry
            var coords = shape.coordinates;
            if (coords) {
                var latlng;
                if (shape.type === 'Point') {
                    latlng = L.latLng(coords[1], coords[0]);
                } else if (shape.type === 'Polygon') {
                    latlng = L.latLng(coords[0][0][1], coords[0][0][0]);
                }
                if (latlng) map.setView(latlng, 19);
            }
        }

        // highlight stays until next search or Structure checkbox interaction

    } catch (err) {
        console.error('Error focusing house on map:', err);
    }
}

// ============================================================
// HELPER - clear household highlight (reused in multiple places)
// ============================================================
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
    var searchInput = document.getElementById('household-search-input');
    if (searchInput) searchInput.value = '';
    var dropdown = document.getElementById('household-search-dropdown');
    if (dropdown) dropdown.style.display = 'none';
}

// ============================================================
// CHECKBOX HANDLERS
// ============================================================
function checkAllGroup(grpchk) {
    if ($(grpchk).is(':checked')) {
        $(grpchk).parent().find('[name=chk1]:not(:checked)').click();
        if ($(grpchk).parent().find('div.in').length == 0)
            $(grpchk).parent().find('a[name=chk_group]').click();
    }
    else {
        $(grpchk).parent().find('[name=chk1]:checked').click();
        if ($(grpchk).parent().find('div.in').length > 0)
            $(grpchk).parent().find('a[name=chk_group]').click();
    }
}



function pinSponsorToBottom() {

    var sponsorPanel = null;

    // Method 1
    var sponsorCollapse = $("#compochk div.panel-collapse[name='Sponsor']");
    if (sponsorCollapse.length > 0) {
        sponsorPanel = sponsorCollapse.closest("[name='div_group']");
    }

    // Method 2
    if (!sponsorPanel || sponsorPanel.length === 0) {
        $("#compochk > [name='div_group']").each(function () {
            var labelText = $(this).find("a[name='chk_group']").text().trim().toLowerCase();
            if (labelText.indexOf("sponsor") !== -1) {
                sponsorPanel = $(this);
                return false;
            }
        });
    }

    // Method 3
    if (!sponsorPanel || sponsorPanel.length === 0) {
        $("#compochk [name='chk1']").each(function () {
            if ($(this).val().toLowerCase().indexOf("sponsor") !== -1) {
                sponsorPanel = $(this).closest("[name='div_group']").parent().closest("[name='div_group']");
                return false;
            }
        });
    }

    // ❌ Not found
    if (!sponsorPanel || sponsorPanel.length === 0) {
        $("#sponsor-pinned").hide();
        return;
    }

    // ✅ MOVE ONLY TO sponsor-checkbox
    var cloned = sponsorPanel.clone(true, true);
    sponsorPanel.remove();

    $("#sponsor-checkbox").html("").append(cloned);

    $("#sponsor-pinned").show();
    $("#sponsor-slider").html(`
    <div style="
        font-size:11px;
        font-weight:600;
        margin-top:2px;
        margin-bottom:6px;
        color:#2471a3;
    ">
        Explore how your contribution created impact over time.
    </div>

    <button id="toggleTimeline" style="
        width:100%;
        padding:6px;
        background:#2471a3;
        color:white;
        border:none;
        border-radius:4px;
        cursor:pointer;
        font-size:12px;
        font-weight:600;
    ">
        Show Impact Over Time 
    </button>
`);
    if (global_slum_id) {
        fetch(`/component/household-month-dates/?slum_id=${global_slum_id}`)
            .then(res => res.json())
            .then(data => {
                TIMELINE_DATA = groupByYear(data.monthly_data);
                TIMELINE_YEARS = Object.keys(TIMELINE_DATA).sort((a, b) => a - b);
                CURRENT_INDEX = -1;
                renderMapTimeline(); // renders into #map-timeline (hidden)
            });
    }
}


// ============================================================
// Sponsor slider 
// ============================================================
let _timelineLayers = [];




// ================= GROUP DATA =================
function groupByYear(data) {

    const result = {};

    data.forEach(item => {
        const year = new Date(item.month_end_date).getFullYear();
        if (!result[year]) result[year] = [];
        result[year].push(item);
    });

    return result;
}


// ================= BUILD MONTH GROUPS =================
function buildMonthGroups(year) {

    let months = TIMELINE_DATA[year] || [];
    if (months.length === 0) return [];

    let midIndex = Math.floor(months.length / 2);
    let total = months.slice(0, midIndex + 1)
        .reduce((sum, m) => sum + m.total, 0);

    return [{
        label: `Mid ${year}`,
        total: total,
        groupIndex: 0,
        year: year,
        endMonthIndex: midIndex
    }];
}


// ================= RENDER =================
function renderMapTimeline() {

    let html = "";
    let totalYears = TIMELINE_YEARS.length;

    TIMELINE_YEARS.forEach((year, i) => {

        let isActive = i === CURRENT_INDEX;
        let isLastYear = i === totalYears - 1;
        let isFirstYear = i === 0;

        // ✅ FIRST YEAR — if data starts in second half, show Mid BEFORE year pill
        if (isFirstYear) {

            let months = TIMELINE_DATA[year] || [];

            if (months.length > 0) {

                let firstDate = new Date(months[0].month_end_date);
                let firstMonthNum = firstDate.getMonth(); // 0=Jan 11=Dec

                if (firstMonthNum >= 6) {

                    let midEndIndex = Math.floor(months.length / 2);
                    let midTotal = months.slice(0, midEndIndex + 1)
                        .reduce((sum, m) => sum + m.total, 0);

                    html += `
                        <span class="timeline-month"
                              data-year="${year}"
                              data-group-index="0"
                              data-end-month-index="${midEndIndex}">
                            Mid ${year}
                            <small>${midTotal}</small>
                        </span>
                        <span class="timeline-dash">—</span>
                    `;
                }
            }
        }

        // ✅ YEAR PILL
        html += `
            <span class="timeline-year ${isActive ? 'active-year' : ''}"
                  data-year="${year}"
                  data-index="${i}">
                ${year}
                <small>${isActive ? '▲' : '▼'}</small>
            </span>
            <span class="timeline-dash">—</span>
        `;

        // ✅ MID PILL — only between years, not after last year
        if (isActive && !isLastYear) {

            let monthGroups = buildMonthGroups(year);

            monthGroups.forEach(g => {
                html += `
                    <span class="timeline-month"
                          data-year="${g.year}"
                          data-group-index="${g.groupIndex}"
                          data-end-month-index="${g.endMonthIndex}">
                        ${g.label}
                        <small>${g.total}</small>
                    </span>
                    <span class="timeline-dash">—</span>
                `;
            });
        }

        // ✅ LAST YEAR — if ongoing year and past July, show Mid as endpoint
        if (isLastYear) {

            let months = TIMELINE_DATA[year] || [];

            if (months.length > 0) {

                let lastDate = new Date(months[months.length - 1].month_end_date);
                let lastMonth = lastDate.getMonth();

                let midEndIndex = Math.floor(months.length / 2);
                let midTotal = months.slice(0, midEndIndex + 1)
                    .reduce((sum, m) => sum + m.total, 0);

                let fullTotal = months
                    .reduce((sum, m) => sum + m.total, 0);

                // ✅ BEFORE JULY → show MID
                if (lastMonth <= 5) {
                    html += `
                <span class="timeline-month"
                      data-year="${year}"
                      data-group-index="0"
                      data-end-month-index="${midEndIndex}">
                    Mid ${year}
                    <small>${midTotal}</small>
                </span>
                <span class="timeline-dash">—</span>
            `;
                }

                // ✅ AFTER JUNE → show END
                else {
                    html += `
                <span class="timeline-month"
                      data-year="${year}"
                      data-group-index="1"
                      data-end-month-index="${months.length - 1}">
                    End ${year}
                    <small>${fullTotal}</small>
                </span>
                <span class="timeline-dash">—</span>
            `;
                }
            }
        }
    });

    $("#map-timeline").html(html);
}


// ================= COLLECT HOUSES TILL YEAR =================
function collectHousesTillYear(yearIndex) {

    let houseList = [];

    for (let i = 0; i <= yearIndex; i++) {
        let y = TIMELINE_YEARS[i];
        TIMELINE_DATA[y].forEach(m => {
            houseList.push(...m.house_numbers);
        });
    }

    return houseList;
}


// ================= COLLECT HOUSES TILL MONTH GROUP =================
function collectHousesTillMonthGroup(year, endMonthIndex) {

    let collected = [];
    let yearIndex = TIMELINE_YEARS.indexOf(String(year));

    for (let i = 0; i < yearIndex; i++) {
        let y = TIMELINE_YEARS[i];
        TIMELINE_DATA[y].forEach(m => {
            collected.push(...m.house_numbers);
        });
    }

    let months = TIMELINE_DATA[year] || [];
    for (let i = 0; i <= endMonthIndex; i++) {
        if (months[i]) collected.push(...months[i].house_numbers);
    }

    return collected;
}


// ================= YEAR CLICK =================
$(document).off("click", ".timeline-year").on("click", ".timeline-year", function () {

    let year = String($(this).data("year"));
    let index = parseInt($(this).data("index"));

    if (CURRENT_INDEX === index) {

        CURRENT_INDEX = -1;

        if (index <= 1) {
            clearTimelineLayers();
        } else {
            let h = collectHousesTillYear(index - 2);
            highlightMultipleHouses(h);
        }

    } else {

        CURRENT_INDEX = index;

        if (index === 0) {
            clearTimelineLayers();
        } else {
            let h = collectHousesTillYear(index - 1);
            highlightMultipleHouses(h);
        }
    }

    renderMapTimeline();
});


// ================= MONTH CLICK =================
$(document).off("click", ".timeline-month").on("click", ".timeline-month", function () {

    $(".timeline-month").removeClass("active");
    $(this).addClass("active");

    let year = String($(this).data("year"));
    let endMonthIndex = parseInt($(this).data("end-month-index"));

    let collected = collectHousesTillMonthGroup(year, endMonthIndex);
    highlightMultipleHouses(collected);
});


// ================= MAP HIGHLIGHT =================
function highlightMultipleHouses(houseList) {

    clearTimelineLayers();

    let filter_houses = [];

    houseList.forEach(function (houseNo) {
        if (houseNo in houses) {
            filter_houses.push(houses[houseNo]);
        }
    });

    if (filter_houses.length === 0) return;

    let layer = L.geoJson(filter_houses, {
        style: {
            color: "#000000",
            opacity: 0.7,
            weight: 0.25,
            fillColor: "#eb349e",
            fillOpacity: 2
        },
        onEachFeature: function (feature, layer) {
            if (feature.properties && feature.properties.name) {
                let name = feature.properties.name;
                layer.bindPopup("House: " + name, { autoPan: true });
                layer.on('mouseover', function () { this.openPopup(); });
                layer.on('mouseout', function () { this.closePopup(); });
                layer.on('click', function () { household_details(name); });
            }
        }
    });

    layer.addTo(map);
    _timelineLayers.push(layer);
}


// ================= CLEAR TIMELINE LAYERS =================
function clearTimelineLayers() {

    _timelineLayers.forEach(function (layer) {
        map.removeLayer(layer);
    });

    _timelineLayers = [];
}


// ================= TOGGLE BUTTON =================
$(document).off("click", "#toggleTimeline").on("click", "#toggleTimeline", function () {
    let container = $("#map-timeline-container");

    if (container.is(":visible")) {
        container.hide();
        $(this).text("Show Impact Over Time");
        clearTimelineLayers();
        CURRENT_INDEX = -1;
    } else {
        // Data already loaded — just show
        container.show();
        $(this).text("Hide Impact Over Time");
    }
});


// ================= STRUCTURE CHECKBOX WATCH =================
$(document).off("click.structureWatch", '[name=chk1]')
    .on("click.structureWatch", '[name=chk1]', function () {

        if ($(this).val() === 'Structure' && !$(this).is(':checked')) {

            let container = $("#map-timeline-container");

            if (container.is(":visible")) {
                container.hide();
                $("#toggleTimeline").text("Show Timeline");
                clearTimelineLayers();
                CURRENT_INDEX = -1;
            }
        }
    });


