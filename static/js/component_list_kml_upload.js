$(document).ready(function () {

    let selectedSlumId = null;
    const $slumSelect = $("select[name='slum_name']");

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
            $("#componentList").append('<div class="list-group-item">No components found.</div>');
            return;
        }

        components.forEach(function (comp) {
            $("#componentList").append(`
                <div class="list-group-item component-item" 
                     data-component-name="${comp.name}" 
                     style="display:flex; justify-content:space-between; align-items:center;">
                    <div>${comp.name}</div>
                    <button class="btn btn-danger btn-xs delete-component" type="button">Delete</button>
                </div>
            `);
        });
    }

    // -----------------------------
    // Load components from server for selected slum
    // -----------------------------
    function loadComponentList() {
        const sid = $slumSelect.val();

        if (!sid) {
            $("#componentList").html('<div class="list-group-item">Select a slum to view components.</div>');
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
    // After form submit (submit button clicked)
    // -----------------------------
    $(document).on("click", "form input[type='submit'], form button[type='submit']", function () {
        updateComponentListTitle();
        $("#refreshComponentList").show();
        loadComponentList();
    });

    // -----------------------------
    // Load initial (if slum pre-selected)
    // -----------------------------
    if ($slumSelect.val()) {
        updateComponentListTitle();
        loadComponentList();
    }
});
