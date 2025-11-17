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
    // Delete component
    // -----------------------------
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

       if (!confirm(`Are you sure you want to delete "${compName}"?`)) return;

       $.ajax({
           url: "/component/delete_component/",
           type: "POST",
           data: {
               object_id: sid,
               comp_name: compName,
               csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
           },
           success: function (res) {
               alert(res.message || `"${compName}" deleted successfully`);
               $btn.closest(".component-item").remove();
           },
           error: function () {
               alert("Failed to delete component.");
           }
       });
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
