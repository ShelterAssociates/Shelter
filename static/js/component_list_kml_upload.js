$(document).ready(function () {

    let selectedSlumId = null;
    const $slumSelect = $("select[name='slum_name']");
    const $searchInput = $("#componentSearchInput");

    // -----------------------------
    // Update the title with slum name
    // -----------------------------
    function updateComponentListTitle() {
        const slumName = $slumSelect.find("option:selected").text().trim();
        if (slumName) {
            $("#componentListTitle").text(`Components List (Slum: ${slumName})`);
        } else {
            $("#componentListTitle").text("Components List");
        }
    }

    // -----------------------------
    // Render component list
    // -----------------------------
    function renderComponents(components) {
        $("#componentList").empty();

        if (!components || components.length === 0) {
            $("#componentList").append(
                '<p class="ku-list-muted">Please upload a KML first — it will be seen here, or refresh once.</p>'
            );
            return;
        }

        components.forEach(function (comp) {
            const metric = comp.metric;
            const metricHtml = metric
                ? `<span class="ku-metric-badge ${metric.source}">${metric.value} ${metric.unit}${metric.source === "manual" ? " (manual)" : " (auto)"}</span>`
                : "";
            const metricBtnHtml = metric
                ? `<button class="ku-metric-btn set-metric" type="button" data-current-value="${metric.value}" data-current-unit="${metric.unit}">${metric.source === "manual" ? "Edit" : "Add"} metric</button>`
                : "";
            $("#componentList").append(`
                <div class="ku-component-row component-item" data-component-name="${comp.name}">
                    <div class="ku-component-row-main">
                        <div>${comp.name}</div>
                        ${metricHtml}
                    </div>
                    <div class="ku-component-row-actions">
                        ${metricBtnHtml}
                        <button class="ku-delete-btn delete-component" type="button">
                            <svg viewBox="0 0 24 24" width="11" height="11" stroke="currentColor" stroke-width="2.5" fill="none"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>Delete
                        </button>
                    </div>
                </div>
            `);
        });

        applyComponentSearch();
    }

    // -----------------------------
    // Search / filter the loaded component list
    // -----------------------------
    function applyComponentSearch() {
        const query = $searchInput.val().trim().toLowerCase();
        const $rows = $("#componentList .component-item");

        $("#componentSearchEmpty").remove();
        if (!query) {
            $rows.show();
            return;
        }

        let visibleCount = 0;
        $rows.each(function () {
            const name = ($(this).data("component-name") || "").toString().toLowerCase();
            const match = name.indexOf(query) !== -1;
            $(this).toggle(match);
            if (match) visibleCount++;
        });

        if ($rows.length && visibleCount === 0) {
            $("#componentList").append('<div class="ku-component-empty" id="componentSearchEmpty">No components match your search.</div>');
        }
    }

    $searchInput.on("input", applyComponentSearch);

    // -----------------------------
    // Load components from server for selected slum
    // -----------------------------
    function loadComponentList() {
        const sid = $slumSelect.val();

        if (!sid) {
            $("#componentList").html('<p class="ku-list-muted">Please select a slum.</p>');
            return;
        }

        $("#componentList").html(
            '<div class="ku-list-loading"><span class="ku-list-spinner"></span>Loading components...</div>'
        );

        $.ajax({
            url: "/component/get_component_list/",
            data: { object_id: sid },
            dataType: "json",
            cache: false,
            success: function (components) {
                renderComponents(components);
            },
            error: function () {
                alert("Failed to fetch components.");
            }
        });
    }

    // -----------------------------
    // When slum is selected
    // -----------------------------
    $(document).on("change", "select[name='slum_name']", function () {
        selectedSlumId = $(this).val();

        $searchInput.val("");
        updateComponentListTitle();
        loadComponentList();
    });

    // -----------------------------
    // Delete component (custom on-page modal)
    // -----------------------------
    const $modalOverlay = $("#kmlDeleteModalOverlay");
    const $modalStepInput = $modalOverlay.find(".kml-modal-step-input");
    const $modalLoading = $modalOverlay.find(".kml-modal-loading");
    const $modalResult = $modalOverlay.find(".kml-modal-result");
    const $reasonInput = $("#kmlDeleteReason");
    const $reasonError = $("#kmlDeleteReasonError");
    let pendingDelete = null; // { $btn, compName, sid }

    function showModalStep(step) {
        $modalStepInput.hide();
        $modalLoading.hide();
        $modalResult.hide();
        if (step === "input") $modalStepInput.show();
        if (step === "loading") $modalLoading.show();
        if (step === "result") $modalResult.show();
    }

    function openDeleteModal(compName, sid, $btn) {
        pendingDelete = { $btn: $btn, compName: compName, sid: sid };
        $("#kmlDeleteCompName").text(compName);
        $reasonInput.val("");
        $reasonError.hide();
        showModalStep("input");
        $modalOverlay.addClass("active");
    }

    function closeDeleteModal() {
        $modalOverlay.removeClass("active");
        pendingDelete = null;
    }

    // remove previous delegated handler, then attach
    $(document).off("click", ".delete-component").on("click", ".delete-component", function (e) {
       e.preventDefault();
       const $btn = $(this);
       const compName = $btn.closest(".component-item").data("component-name");
       const sid = $slumSelect.val();

       if (!sid) {
           alert("Please select a slum first!");
           return;
       }

       openDeleteModal(compName, sid, $btn);
    });

    $("#kmlDeleteCancelBtn").on("click", function () {
        closeDeleteModal();
    });

    $("#kmlDeleteConfirmBtn").on("click", function () {
        if (!pendingDelete) return;
        const reason = $reasonInput.val().trim();
        if (!reason) {
            $reasonError.show();
            return;
        }
        $reasonError.hide();

        const { $btn, compName, sid } = pendingDelete;
        showModalStep("loading");

        $.ajax({
            url: "/component/delete_component/",
            type: "POST",
            data: {
                object_id: sid,
                comp_name: compName,
                reason: reason,
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
            },
            success: function (res) {
                $modalResult.removeClass("error").addClass("success");
                $modalResult.find(".kml-modal-result-icon").text("✓");
                $modalResult.find(".kml-modal-result-message").text(res.message || `"${compName}" deleted successfully`);
                showModalStep("result");
                $btn.closest(".component-item").remove();
            },
            error: function (xhr) {
                $modalResult.removeClass("success").addClass("error");
                $modalResult.find(".kml-modal-result-icon").text("✕");
                $modalResult.find(".kml-modal-result-message").text((xhr.responseJSON && xhr.responseJSON.message) || "Failed to delete component.");
                showModalStep("result");
            }
        });
    });

    $("#kmlDeleteCloseBtn").on("click", function () {
        closeDeleteModal();
    });

    // -----------------------------
    // Set/edit metric (shared by: the "Add/Edit metric" button on a
    // component row, and the automatic post-upload prompt for a newly
    // uploaded line-type component with no metric yet)
    // -----------------------------
    const $metricModalOverlay = $("#kmlMetricModalOverlay");
    const $metricStepInput = $metricModalOverlay.find(".kml-modal-step-input");
    const $metricLoading = $metricModalOverlay.find(".kml-modal-loading");
    const $metricResult = $metricModalOverlay.find(".kml-modal-result");
    const $metricValueInput = $("#kmlMetricValue");
    const $metricUnitInput = $("#kmlMetricUnit");
    const $metricReasonInput = $("#kmlMetricReason");
    const $metricReasonError = $("#kmlMetricReasonError");
    let pendingMetric = null; // { compName, sid }

    function showMetricModalStep(step) {
        $metricStepInput.hide();
        $metricLoading.hide();
        $metricResult.hide();
        if (step === "input") $metricStepInput.show();
        if (step === "loading") $metricLoading.show();
        if (step === "result") $metricResult.show();
    }

    function openMetricModal(compName, sid, currentValue, currentUnit) {
        pendingMetric = { compName: compName, sid: sid };
        $("#kmlMetricCompName").text(compName);
        $metricValueInput.val(currentValue || "");
        $metricUnitInput.val(currentUnit || "");
        $metricReasonInput.val("");
        $metricReasonError.hide();
        showMetricModalStep("input");
        $metricModalOverlay.addClass("active");
    }

    function closeMetricModal() {
        $metricModalOverlay.removeClass("active");
        pendingMetric = null;
    }

    $(document).off("click", ".set-metric").on("click", ".set-metric", function (e) {
        e.preventDefault();
        const $btn = $(this);
        const compName = $btn.closest(".component-item").data("component-name");
        const sid = $slumSelect.val();

        if (!sid) {
            alert("Please select a slum first!");
            return;
        }

        openMetricModal(compName, sid, $btn.data("current-value"), $btn.data("current-unit"));
    });

    $("#kmlMetricCancelBtn").on("click", function () {
        closeMetricModal();
    });

    $("#kmlMetricConfirmBtn").on("click", function () {
        if (!pendingMetric) return;
        const value = $metricValueInput.val().trim();
        const unit = $metricUnitInput.val();
        const reason = $metricReasonInput.val().trim();

        if (!value || !unit || !reason) {
            $metricReasonError.show();
            return;
        }
        $metricReasonError.hide();

        const { compName, sid } = pendingMetric;
        showMetricModalStep("loading");

        $.ajax({
            url: "/component/set_component_metric/",
            type: "POST",
            data: {
                object_id: sid,
                comp_name: compName,
                value: value,
                unit: unit,
                reason: reason,
                csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
            },
            success: function (res) {
                $metricResult.removeClass("error").addClass("success");
                $metricResult.find(".kml-modal-result-icon").text("✓");
                $metricResult.find(".kml-modal-result-message").text(res.message || `Metric for "${compName}" saved`);
                showMetricModalStep("result");
                loadComponentList();
            },
            error: function (xhr) {
                $metricResult.removeClass("success").addClass("error");
                $metricResult.find(".kml-modal-result-icon").text("✕");
                $metricResult.find(".kml-modal-result-message").text((xhr.responseJSON && xhr.responseJSON.message) || "Failed to save metric.");
                showMetricModalStep("result");
            }
        });
    });

    $("#kmlMetricCloseBtn").on("click", function () {
        closeMetricModal();
    });

    // -----------------------------
    // Refresh button
    // -----------------------------
    // remove previous delegated handler and attach properly (with event param)
    $(document).off("click", "#refreshComponentList").on("click", "#refreshComponentList", function (e) {
        e.preventDefault();
        e.stopPropagation();
        console.log("Refresh component list clicked");
        updateComponentListTitle();
        loadComponentList();
    });

    // -----------------------------
    // KML upload (AJAX, with the same-style progress modal)
    // -----------------------------
    const $uploadForm = $("#kml-upload-form");
    const $uploadModalOverlay = $("#kmlUploadModalOverlay");
    const $uploadStepLoading = $uploadModalOverlay.find(".ku-upload-step-loading");
    const $uploadStepResult = $uploadModalOverlay.find(".ku-upload-step-result");

    function showUploadStep(step) {
        $uploadStepLoading.hide();
        $uploadStepResult.hide();
        if (step === "loading") $uploadStepLoading.show();
        if (step === "result") $uploadStepResult.show();
    }

    const $uploadDialog = $uploadModalOverlay.find(".ku-modal-dialog");
    const $uploadErrorsBox = $uploadModalOverlay.find(".ku-upload-errors");
    const $uploadErrorList = $uploadModalOverlay.find(".ku-upload-error-list");
    const $copyErrorsBtn = $("#kmlUploadCopyErrorsBtn");
    const COPY_ERRORS_LABEL = $copyErrorsBtn.text() || "Copy all errors";
    let lastUploadErrors = [];

    // '"<folder>" -> <placemark>: <reason>' as produced by KMLValidationError
    const KML_ERROR_RE = /^"([^"]*)"\s*->\s*(.+?):\s([\s\S]*)$/;

    /** Turn one raw server error reason into a readable title/explanation/fix. */
    function classifyKmlError(reason) {
        const lower = reason.toLowerCase();

        if (lower.indexOf("degenerate") !== -1) {
            return {
                title: "Empty or zero-length geometry",
                explanation: "This placemark has no usable shape — it holds no points, or all of its points sit on the exact same spot.",
                fix: "Delete this feature, or redraw it with at least 2 distinct points."
            };
        }

        if (lower.indexOf("self-intersect") !== -1 || lower.indexOf("self intersect") !== -1 || lower.indexOf("invalid") !== -1) {
            const point = reason.match(/\[\s*(-?[\d.]+)[\s,]+(-?[\d.]+)\s*\]/);
            let explanation = "The outline of this shape crosses over or touches itself, so its area cannot be calculated.";
            if (point) {
                explanation += " The problem point is at lon " + point[1] + ", lat " + point[2] + ".";
            }
            return {
                title: "Shape crosses or touches itself",
                explanation: explanation,
                fix: "Remove duplicate or near-duplicate vertices and redraw that corner in QGIS or Google Earth, then export again."
            };
        }

        const duplicate = reason.match(/duplicate placemark id\s+"([^"]*)"/i);
        if (duplicate) {
            return {
                title: "Duplicate house number " + duplicate[1],
                explanation: "Two placemarks in the same folder carry the house number " + duplicate[1] + ", so they cannot be told apart.",
                fix: "Give each feature a unique HouseNo/ID value before exporting."
            };
        }

        if (lower.indexOf("multigeometry polygon not supported") !== -1) {
            const count = reason.match(/bundles\s+(\d+)\s+polygons?/);
            const explanation = "This placemark is a multi-geometry polygon \u2014 "
                + (count && count[1] === "1"
                    ? "it wraps a single polygon in a multi-geometry container"
                    : "it bundles " + (count ? count[1] + " separate polygons" : "several separate polygons") + " into one feature")
                + ". Multi-geometry polygons are not supported, so this file cannot be uploaded as it is.";
            return {
                title: "Multi-geometry polygon \u2014 not supported",
                explanation: explanation,
                fix: 'Split it into one placemark per polygon \u2014 run "Multipart to Singleparts" in QGIS, then export the KML again.'
            };
        }

        if (lower.indexOf("multigeometry has no linestring") !== -1) {
            return {
                title: "Unsupported multi-geometry",
                explanation: "This placemark uses a multi-geometry that holds no lines, so there is nothing this importer can read. " + reason,
                fix: 'Split it into single-part features ("Multipart to Singleparts" in QGIS) and export again.'
            };
        }

        if (lower.indexOf("no such child") !== -1) {
            return {
                title: "Unsupported or missing geometry",
                explanation: "This placemark has no geometry of a kind this importer can read (for example a multi-part or empty feature).",
                fix: 'Run "Multipart to Singleparts" in QGIS before exporting, and make sure every placemark has a polygon or line.'
            };
        }

        return {
            title: "Could not read this placemark",
            explanation: reason,
            fix: "Check this placemark in QGIS or Google Earth and re-export the file."
        };
    }

    /**
     * Build one <li> for a raw error string. Every node is filled with .text()
     * because these strings carry content from the uploaded KML file.
     */
    function buildUploadErrorItem(rawText, openByDefault) {
        const match = KML_ERROR_RE.exec(rawText);
        let info;
        let where = "";

        if (match) {
            const folder = match[1];
            const placemark = match[2].trim();
            info = classifyKmlError(match[3].trim());
            where = placemark + " · folder: " + folder;
        } else {
            info = classifyKmlError(rawText);
        }

        const $summary = $("<summary>").text(info.title);
        if (where) {
            $summary.append($("<span>").addClass("ku-upload-error-where").text(" — " + where));
        }

        const $body = $("<div>").addClass("ku-upload-error-body");
        $body.append($("<p>").text(info.explanation));
        $body.append($("<p>").text("How to fix: " + info.fix));
        $body.append($("<code>").addClass("ku-upload-error-raw").text(rawText));

        const $details = $("<details>").append($summary).append($body);
        if (openByDefault) {
            $details.attr("open", "open");
        }

        return $("<li>").addClass("ku-upload-error-item").append($details);
    }

    function renderUploadErrors(errors) {
        lastUploadErrors = errors;
        $uploadErrorList.empty();

        if (!errors.length) {
            $uploadErrorsBox.hide();
            $copyErrorsBtn.hide();
            $uploadDialog.removeClass("ku-wide");
            return;
        }

        // A short list is more useful opened; a long one needs to stay scannable.
        const openByDefault = errors.length <= 2;
        errors.forEach(function (rawText) {
            $uploadErrorList.append(buildUploadErrorItem(String(rawText), openByDefault));
        });

        $uploadErrorsBox.show().scrollTop(0);
        $copyErrorsBtn.text(COPY_ERRORS_LABEL).show();
        $uploadDialog.addClass("ku-wide");
    }

    function showUploadResult(isSuccess, message, detail, errors) {
        $uploadStepResult.removeClass("success error").addClass(isSuccess ? "success" : "error");
        $uploadStepResult.find(".ku-upload-result-icon").text(isSuccess ? "✓" : "✕");
        $uploadStepResult.find(".ku-upload-result-message").text(message);
        $uploadStepResult.find(".ku-upload-result-detail").text(detail || "");
        renderUploadErrors(errors || []);
        showUploadStep("result");
    }

    /** Shared by the success (res.success === false) and error AJAX callbacks. */
    function showUploadFailure(res, fallbackMessage) {
        res = res || {};
        const allErrors = res.errors || {};
        let kmlErrors = allErrors.kml_file || [];
        if (!Array.isArray(kmlErrors)) {
            kmlErrors = [kmlErrors];
        }

        const otherDetails = [];
        Object.keys(allErrors).forEach(function (field) {
            if (field === "kml_file") return;
            const value = allErrors[field];
            otherDetails.push(Array.isArray(value) ? value.join(", ") : String(value));
        });

        showUploadResult(false, res.message || fallbackMessage, otherDetails.join(" "), kmlErrors);
    }

    function copyWithExecCommand(text) {
        try {
            const textarea = document.createElement("textarea");
            textarea.value = text;
            textarea.setAttribute("readonly", "");
            textarea.style.position = "fixed";
            textarea.style.top = "-1000px";
            document.body.appendChild(textarea);
            textarea.select();
            const copied = document.execCommand("copy");
            document.body.removeChild(textarea);
            return copied;
        } catch (err) {
            return false;
        }
    }

    $copyErrorsBtn.on("click", function () {
        if (!lastUploadErrors.length) return;

        const text = lastUploadErrors.map(function (rawText, index) {
            return (index + 1) + ". " + rawText;
        }).join("\n");

        function markCopied() {
            $copyErrorsBtn.text("Copied");
            setTimeout(function () {
                $copyErrorsBtn.text(COPY_ERRORS_LABEL);
            }, 1500);
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(markCopied, function () {
                if (copyWithExecCommand(text)) markCopied();
            });
        } else if (copyWithExecCommand(text)) {
            markCopied();
        }
    });

    $uploadForm.on("submit", function (e) {
        e.preventDefault();

        const formData = new FormData(this);
        $uploadModalOverlay.addClass("active");
        showUploadStep("loading");

        $.ajax({
            url: window.location.href,
            type: "POST",
            data: formData,
            processData: false,
            contentType: false,
            dataType: "json",
            success: function (res) {
                if (res.success) {
                    const detailParts = [];
                    if (res.parsed && res.parsed.length) {
                        detailParts.push("Parsed: " + res.parsed.join(", "));
                    }
                    if (res.unparsed && res.unparsed.length) {
                        detailParts.push("Unparsed: " + res.unparsed.join(", "));
                    }
                    if (res.email_sent === true) {
                        detailParts.push("Notification email sent successfully.");
                    } else if (res.email_sent === false) {
                        detailParts.push("Upload succeeded, but the notification email failed to send.");
                    }
                    showUploadResult(true, "KML uploaded successfully", detailParts.join(" — "));

                    updateComponentListTitle();
                    loadComponentList();

                    // If a newly-uploaded line-type component still has no
                    // metric (and none was given inline above), prompt for
                    // one now — this is the second of the two "ask" points,
                    // the first being the optional field on the form itself.
                    if (res.needs_metric && res.needs_metric.length && res.object_id) {
                        $uploadModalOverlay.removeClass("active");
                        openMetricModal(res.needs_metric[0], res.object_id, "", "");
                    }
                } else {
                    showUploadFailure(res, "Upload failed.");
                }
            },
            error: function (xhr) {
                // A rejected KML comes back as HTTP 400, so the readable error
                // list has to be rendered from here too, not just on success.
                showUploadFailure(xhr.responseJSON, "Failed to upload KML file. Please try again.");
            }
        });
    });

    $("#kmlUploadModalCloseBtn").on("click", function () {
        $uploadModalOverlay.removeClass("active");
    });

    // -----------------------------
    // Load initial (if slum pre-selected)
    // -----------------------------
    if ($slumSelect.val()) {
        updateComponentListTitle();
        loadComponentList();
    }
});
