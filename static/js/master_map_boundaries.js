/*
 * master_map_boundaries.js
 * Handles drawing of Admin Ward, Electoral Ward, and Slum polygons.
 */

var __extends = (this && this.__extends) || function (d, b) {
    for (var p in b) if (b.hasOwnProperty(p)) d[p] = b[p];
    function __() { this.constructor = d; }
    d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
};

/* ── Polygon base class ──────────────────────────────────────────────────── */
var Polygon = (function () {
    function Polygon(obj_data) {
        this.type = obj_data.type;
        this.name = obj_data.name.trim();
        this.info = obj_data.info;
        this.legend = obj_data.legend;
        this.id = obj_data.id;
        this.officeAddress = obj_data.wardOfficeAddress || "";
        this.officerName = obj_data.wardOfficerName || "";
        this.officerTel = obj_data.wardOfficeTel || "";

        var slum_bgColor = "#A3A3FF";
        var slum_borderColor = "#3232FF";
        if (obj_data.associated) {
            slum_bgColor = "#FFA3A3";
            slum_borderColor = "#FF0000";
        }
        if (obj_data.current_status === "sra") {
            slum_bgColor = "#fbff00";
            slum_borderColor = "#ffd000";
        }
        this.bgColor = obj_data.bgColor || slum_bgColor;
        this.borderColor = obj_data.borderColor || slum_borderColor;

        /* shape setter triggers drawPolygon */
        this.shape = obj_data.lat;
    }

    Object.defineProperty(Polygon.prototype, "shape", {
        get: function () { return this._shape; },
        set: function (shape) { this._shape = this.drawPolygon(shape); },
        enumerable: true,
        configurable: true
    });

    Polygon.prototype.drawPolygon = function (bounds) {
        var poly_options = {
            color: this.borderColor,
            opacity: 0.7,
            weight: 2,
            fillColor: this.bgColor,
            fillOpacity: 0.4,
            name: this.name
        };
        var Poly = L.geoJson(bounds, { style: poly_options });
        var return_poly;
        Poly.eachLayer(function (layer) { return_poly = layer; });
        return return_poly;
    };

    Polygon.prototype.setListeners = function () {
        var shapename = this.name;
        if (this.type === "Slum") {
            shapename = "Slum : " + this.name;
        }
        this.shape.bindPopup(shapename, { autoPan: true });
        this.shape.on({
            mouseover: function () { this.openPopup(); },
            mouseout: function () { this.closePopup(); }
        });
    };

    Polygon.prototype.show = function () {
        map.addLayer(this.shape);
        if (this.type === "Slum") { this.shape.bringToFront(); }
        arr_poly_disp.push(this);
    };

    Polygon.prototype.hide = function () {
        map.removeLayer(this.shape);
    };

    Polygon.prototype.hideAll = function () {
        $.each(arr_poly_disp, function (k, v) { map.removeLayer(v.shape); });
        arr_poly_disp = [];
        zIndex = 0;
    };

    Polygon.prototype.event_onClick = function () {
        this.hideAll();
        objBreadcrumb.push(this.name);

        /* Header */
        var myheader = $("#maphead");
        myheader.html('<h4>' + this.name + '</h4>');
        myheader.find("h4").css("padding-top", "15px");

        /* Info */
        $("#mapdesc").html(this.info);

        /* Ward details */
        var wdhd = "";
        var wdadd = "";
        var wdname = "";

        if (this.officeAddress !== "") {
            wdhd = "<div><b>Details: </b></div>";

            wdadd = "<div class='row'><div class='col-md-2' style='margin-left:25px'><b>Address :</b> </div>";
            wdadd += "<div class='col-md-9'>" + (this.officeAddress ? this.officeAddress.trim() : " - ") + "</div></div>";

            wdname = "<div class='row'><div class='row' style='margin-left:25px'>";
            wdname += "<div class='col-md-2'><b>Name :</b></div>";
            wdname += "<div class='col-md-10'>" + (this.officerName || " - ") + "</div></div>";
            wdname += "<div class='row' style='margin-left:25px'>";
            wdname += "<div class='col-md-2'><b>Contact :</b></div>";
            wdname += "<div class='col-md-10'>" + (this.officerTel || " - ") + "</div></div></div>";
        }

        $("#wdhead").html(wdhd);
        $("#wdaddress").html(wdadd);
        $("#wdofficer").html(wdname);
    };

    return Polygon;
}());


/* ── Slum ────────────────────────────────────────────────────────────────── */
var Slum = (function (_super) {
    __extends(Slum, _super);

    function Slum(obj_data) {
        this.slumId = obj_data.id;
        _super.call(this, obj_data);
        _super.prototype.show.call(this);
        /* NOTE: we do NOT check factsheet availability at construction time.
           Doing so for every slum fires hundreds of API requests on page load.
           Instead we check on-demand when this slum becomes active. */
    }

    /* Called when a slum becomes active (click or direct URL).
       activeSlumId is the slumId at the moment of activation — passed in
       so we never race against the async global_slum_id assignment. */
    Slum.prototype._loadFactsheetBtn = function (activeSlumId) {
        var _this = this;
        /* Clear any previously shown button immediately */
        $("#factsheet-btn-slot").hide().html("");

        fetch("/admin/api/rim_factsheet_available/" + this.slumId + "/")
            .then(function (res) { return res.json(); })
            .then(function (data) {
                /* Only render if this slum is still the one that triggered
                   the load (guards against fast slum-switching) */
                if (data.available === true &&
                    String(activeSlumId) === String(_this.slumId)) {
                    _this._showFactsheetBtn();
                }
            })
            .catch(function (err) {
                console.error("Factsheet availability check failed:", err);
            });
    };

    /* Renders the "View Factsheet" button using the shared .action-btn class */
    Slum.prototype._showFactsheetBtn = function () {
        var slumId = this.slumId;
        $("#factsheet-btn-slot").html(
            "<button class='action-btn' onclick='Slum.prototype.factsheet_click(this," + slumId + ")'>" +
            "View Factsheet" +
            "</button>"
        ).show();
    };

    Slum.prototype.factsheet_click = function (element, slum_id) {
        $("#rimPreviewModal").fadeIn();

        $("#rimDownloadBtn")
            .prop("disabled", true)
            .css("opacity", "0.6")
            .text("Generating PDF...")
            .removeAttr("data-slum-id");

        $("#rimPreviewBody").html(
            '<div style="display:flex;align-items:center;justify-content:center;height:607px;">' +
            '<div style="text-align:center;">' +
            '<div class="custom-spinner"></div>' +
            '<div style="margin-top:15px;font-weight:bold;">Loading preview &amp; generating PDF...</div>' +
            '</div></div>'
        );

        /* Preview */
        fetch("/reports/preview-rim-factsheet/" + slum_id + "/")
            .then(function (res) { return res.text(); })
            .then(function (html) { $("#rimPreviewBody").html(html); })
            .catch(function (err) {
                console.error(err);
                $("#rimPreviewBody").html(
                    '<div style="padding:40px;text-align:center;color:red;">Failed to load preview</div>'
                );
            });

        /* PDF generation */
        fetch("/reports/api/rim_factsheet_generation/" + slum_id + "/")
            .then(function (res) {
                if (res.status === 405) { throw new Error("Please fill RIM form or sync data."); }
                if (res.status === 406) { throw new Error("RIM data not found."); }
                if (res.status !== 202) { throw new Error("PDF generation failed."); }
                $("#rimDownloadBtn")
                    .prop("disabled", false)
                    .css("opacity", "1")
                    .text("Download PDF")
                    .attr("data-slum-id", slum_id);
            })
            .catch(function (err) {
                console.error(err);
                alert(err.message);
            });
    };

    Slum.prototype.setListeners = function () {
        _super.prototype.setListeners.call(this);
        var _this = this;

        this.shape.on({
            click: function (event) {
                /* Hide legend when entering slum view */
                if (legendControl) { map.removeControl(legendControl); }

                if (objBreadcrumb.val.length < 2) {
                    /* Navigate via datatable */
                    $("#datatable_filter").find("input").val(_this.name).trigger("keyup");
                    $("#datatable").find("tbody>tr>td>div>span:contains(" + _this.name + ")").trigger("click");
                } else {
                    if (event !== undefined) { slum_data_fetch(_this.slumId); }
                }

                _super.prototype.event_onClick.call(_this);
                _super.prototype.show.call(_this);
                map.fitBounds(_this.shape.getBounds());

                /* Check factsheet availability on-demand and show button.
                   global_slum_id is set by slum_data_fetch (called just above)
                   so the String comparison in _loadFactsheetBtn will match.
                   Skip entirely for SRA / inactive / road_widening slums —
                   those statuses hide the whole right panel already. */
                var skipStatuses = ["inactive", "sra", "road_widening"];
                fetch("/component/get_component/" + _this.slumId, {
                    headers: { "Force-Refresh-Flag": "0" }
                })
                    .then(function (r) { return r.json(); })
                    .then(function (cd) {
                        if (skipStatuses.includes(cd.status)) {
                            /* Ensure right panel, factsheet and sponsor shadow are all hidden */
                            $("#right-panel").removeClass("active");
                            $("#factsheet-btn-slot").hide().html("");
                            $("#household-search-wrapper").hide();
                            $("#sponsor-pinned").hide();
                            $("#compochk_refresh").html("");
                            $("#compochk").html("");
                        } else {
                            _this._loadFactsheetBtn(_this.slumId);
                        }
                    })
                    .catch(function () {
                        /* On error fall back to normal behaviour */
                        _this._loadFactsheetBtn(_this.slumId);
                    });
            }
        });
    };

    return Slum;
}(Polygon));


/* ── ElectoralWard ───────────────────────────────────────────────────────── */
var ElectoralWard = (function (_super) {
    __extends(ElectoralWard, _super);

    function ElectoralWard(obj_data) {
        _super.call(this, obj_data);
    }

    ElectoralWard.prototype.setListeners = function () {
        _super.prototype.setListeners.call(this);
        var _this = this;

        this.shape.on({
            click: function () {
                _super.prototype.event_onClick.call(_this);
                _super.prototype.show.call(_this);
                $.each(
                    parse_data[objBreadcrumb.val[0]]["content"][_this.name]["content"],
                    function (k, v) { v.obj.show(); }
                );
                map.fitBounds(_this.shape.getBounds());
            }
        });
    };

    return ElectoralWard;
}(Polygon));


/* ── AdministrativeWard ──────────────────────────────────────────────────── */
var AdministrativeWard = (function (_super) {
    __extends(AdministrativeWard, _super);

    function AdministrativeWard(obj_data) {
        _super.call(this, obj_data);
        _super.prototype.show.call(this);
    }

    AdministrativeWard.prototype.setListeners = function () {
        _super.prototype.setListeners.call(this);
        var _this = this;

        this.shape.on({
            click: function () {
                _super.prototype.event_onClick.call(_this);
                $.each(parse_data[_this.name]["content"], function (k, v) {
                    v.obj.show();
                    $.each(v["content"], function (key, val) { val.obj.show(); });
                });
                map.fitBounds(_this.shape.getBounds());
            }
        });
    };

    return AdministrativeWard;
}(Polygon));


/* ── City (dummy top-level object) ──────────────────────────────────────── */
var City = (function () {
    function City(name) {
        this.name = name;
        this.shape = { click: this.click };
    }

    City.prototype.click = function () {
        $("#right-panel").removeClass("active");
        $("#factsheet-btn-slot").hide().html("");
        $("#compochk").html("");
        $("#household-search-wrapper").hide();
        $("#sponsor-pinned").hide();
        $(".overlay").show();

        $.each(arr_poly_disp, function (k, v) { map.removeLayer(v.shape); });
        arr_poly_disp = [];

        $.each(parse_data, function (key, value) {
            value.obj.show();
            $.each(value["content"], function (k1, v1) {
                $.each(v1["content"], function (k2, v2) { v2.obj.show(); });
            });
        });

        map.setZoom(12);
        $("#maphead").html("");
        $("#mapdesc").html("");
        $("#wdhead").html("");
        $("#wdaddress").html("");
        $("#wdofficer").html("");
        $(".overlay").hide();
    };

    return City;
}());


/* ── RIM Modal: close on X or backdrop click ─────────────────────────────── */
$(document).on("click", ".rim-close", function () {
    $("#rimPreviewModal").hide();
    $("#rimPreviewBody").html("");
    $("#rimDownloadForm").removeClass("show").hide();
    $("#rimOTPSection").hide();
});

$(document).on("click", "#rimPreviewModal", function (e) {
    if (e.target.id === "rimPreviewModal") {
        $("#rimPreviewModal").hide();
        $("#rimPreviewBody").html("");
        $("#rimDownloadForm").removeClass("show").hide();
        $("#rimOTPSection").hide();
    }
});


/* ── Download PDF button: toggle OTP form ────────────────────────────────── */
$(document).on("click", "#rimDownloadBtn", function () {
    var slumId = $(this).attr("data-slum-id");
    if (!slumId || $(this).prop("disabled")) return;
    $("#rimDownloadForm").toggleClass("show").attr("data-slum-id", slumId);
});

$(document).on("click", "#rimFormClose", function () {
    $("#rimDownloadForm").removeClass("show");
});

$(document).on("click", function (e) {
    if (!$(e.target).closest("#rimDownloadForm, #rimDownloadBtn").length) {
        $("#rimDownloadForm").removeClass("show");
    }
});


/* ── Send OTP ─────────────────────────────────────────────────────────────── */
$(document).on("click", "#rimSendOTP", function () {
    var name = $("#rimName").val().trim();
    var email = $("#rimEmail").val().trim();
    var mobile = $("#rimMobile").val().trim();

    if (!name) { alert("Please enter your name"); return; }
    if (!email) { alert("Please enter email"); return; }
    if (!mobile || mobile.length !== 10) { alert("Enter valid 10 digit mobile number"); return; }

    fetch("/helpers/api/send-otp/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
        body: JSON.stringify({ email: email, mobile: mobile, task: "FACTSHEET_DOWNLOAD" })
    })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data.status === "otp_sent") {
                alert("OTP sent to your email");
                $("#rimOTPSection").show();
            } else if (data.status === "wait") {
                alert(data.message);
            } else {
                alert("Failed to send OTP");
            }
        });
});


/* ── Verify OTP and trigger download ─────────────────────────────────────── */
$(document).on("click", "#rimVerifyOTP", function () {
    var otp = $("#rimOTP").val().trim();
    var name = $("#rimName").val().trim();
    var email = $("#rimEmail").val().trim();
    var mobile = $("#rimMobile").val().trim();
    var slumId = $("#rimDownloadForm").attr("data-slum-id");

    if (!otp) { alert("Please enter OTP"); return; }

    fetch("/helpers/api/verify-otp/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
        body: JSON.stringify({ name: name, email: email, mobile: mobile, otp: otp, task: "FACTSHEET_DOWNLOAD" })
    })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data.status === "verified") {
                window.location.href = "/reports/api/rim_factsheet_pdf_fetch/" + slumId + "/";
            } else if (data.status === "blocked") {
                alert("Too many attempts. Please request a new OTP.");
            } else {
                alert("Invalid OTP");
            }
        });
});