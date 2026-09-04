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
    const EMPTY_STATE_ICON = '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>';

    function renderComponents(components) {
        $("#componentList").empty();

        if (!components || components.length === 0) {
            $("#componentList").append(
                '<div class="ku-empty-state">' +
                    '<div class="ku-empty-state-icon">' + EMPTY_STATE_ICON + '</div>' +
                    '<p>No components available.<br>Start by uploading your first KML for this slum.</p>' +
                '</div>'
            );
            return;
        }

        components.forEach(function (comp) {
            $("#componentList").append(`
                <div class="ku-component-row component-item" data-component-name="${comp.name}">
                    <div>${comp.name}</div>
                    <button class="ku-delete-btn delete-component" type="button">
                        <svg viewBox="0 0 24 24" width="11" height="11" stroke="currentColor" stroke-width="2.5" fill="none"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>Delete
                    </button>
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
            $("#componentList").html(
                '<div class="ku-empty-state">' +
                    '<div class="ku-empty-state-icon">' + EMPTY_STATE_ICON + '</div>' +
                    '<p>Select a slum to view components.</p>' +
                '</div>'
            );
            return;
        }

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
