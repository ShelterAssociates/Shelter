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

    function showUploadResult(isSuccess, message, detail) {
        $uploadStepResult.removeClass("success error").addClass(isSuccess ? "success" : "error");
        $uploadStepResult.find(".ku-upload-result-icon").text(isSuccess ? "✓" : "✕");
        $uploadStepResult.find(".ku-upload-result-message").text(message);
        $uploadStepResult.find(".ku-upload-result-detail").text(detail || "");
        showUploadStep("result");
    }

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
                    let detail = "";
                    if (res.errors) {
                        detail = Object.keys(res.errors).map(function (field) {
                            return res.errors[field].join(", ");
                        }).join(" ");
                    }
                    showUploadResult(false, res.message || "Upload failed.", detail);
                }
            },
            error: function (xhr) {
                const res = xhr.responseJSON;
                showUploadResult(false, (res && res.message) || "Failed to upload KML file. Please try again.", "");
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
