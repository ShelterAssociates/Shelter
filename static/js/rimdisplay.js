(function () {
    function parseId(value) {
        if (!value) {
            return ""
        }
        return String(value).trim()
    }

    function getSelectValue(select) {
        return select && select.value ? String(select.value) : ""
    }

    function toItems(json) {
        var items = []
        var ids = json && json.idArray ? json.idArray : []
        var names = json && json.nameArray ? json.nameArray : []
        for (var index = 0; index < ids.length; index += 1) {
            items.push({
                id: String(ids[index]),
                name: String(names[index]),
            })
        }
        return items
    }

    function fetchOptions(filterApiUrl, payload) {
        var params = new URLSearchParams()
        Object.keys(payload).forEach(function (key) {
            var value = payload[key]
            if (Array.isArray(value)) {
                value.forEach(function (item) {
                    params.append(key, item)
                })
            } else if (value !== null && value !== undefined && value !== "") {
                params.append(key, value)
            }
        })

        return fetch(filterApiUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
            body: params,
        }).then(function (response) {
            if (!response.ok) {
                throw new Error("Failed to load filter options.")
            }
            return response.json()
        })
    }

    function buildOptionsFragment(placeholder, items, selectedValue) {
        var fragment = document.createDocumentFragment()
        fragment.appendChild(new Option("", "", false, false))

        items.forEach(function (item) {
            var option = new Option(item.name, item.id, false, item.id === selectedValue)
            fragment.appendChild(option)
        })

        return fragment
    }

    function renderSelect(select, placeholder, items, selectedValue) {
        if (!select) {
            return
        }

        var value = parseId(selectedValue)
        var validValues = items.map(function (item) {
            return String(item.id)
        })
        var shouldKeepValue = value && validValues.indexOf(value) !== -1
        var nextValue = shouldKeepValue ? value : ""

        select.innerHTML = ""
        select.appendChild(buildOptionsFragment(placeholder, items, nextValue))
        select.value = nextValue
        select.disabled = false
        select.removeAttribute("aria-busy")

        if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
            window.jQuery(select).trigger("change.select2")
        }
    }

    function setLoading(select, isLoading) {
        if (!select) {
            return
        }
        select.disabled = !!isLoading
        if (isLoading) {
            select.setAttribute("aria-busy", "true")
        } else {
            select.removeAttribute("aria-busy")
        }
    }

    function appendFilters(payload, filters) {
        if (filters.cityId) {
            payload.city = [filters.cityId]
        }
        if (filters.adminId) {
            payload.admin = [filters.adminId]
        }
        if (filters.electoralId) {
            payload.electoral = [filters.electoralId]
        }
    }

    function initSelect2(select) {
        if (!window.jQuery || !window.jQuery.fn || !window.jQuery.fn.select2 || !select) {
            return
        }

        window.jQuery(select).select2({
            theme: "bootstrap-5",
            width: "100%",
            allowClear: true,
            placeholder: select.getAttribute("data-placeholder") || "",
            minimumResultsForSearch: 0,
        })
    }

    function main() {
        var rimPage = document.getElementById("rim-page")
        if (!rimPage) {
            return
        }

        var filterApiUrl = rimPage.getAttribute("data-filter-api-url") || ""
        var searchInput = document.getElementById("rim-query")
        var clearBtn = document.getElementById("rim-clear-btn")
        var deleteBtn = document.getElementById("rim-delete-btn")
        var searchForm = document.getElementById("rim-search-form")

        var citySelect = document.getElementById("rim-city-filter")
        var adminSelect = document.getElementById("rim-admin-filter")
        var electoralSelect = document.getElementById("rim-electoral-filter")
        var slumSelect = document.getElementById("rim-slum-filter")

        var state = {
            cityId: parseId(rimPage.getAttribute("data-selected-city-id")),
            adminId: parseId(rimPage.getAttribute("data-selected-admin-id")),
            electoralId: parseId(rimPage.getAttribute("data-selected-electoral-id")),
            slumId: parseId(rimPage.getAttribute("data-selected-slum-id")),
        }

        var requestSerial = 0
        var suppressEvents = false

        function nextRequestSerial() {
            requestSerial += 1
            return requestSerial
        }

        function isCurrentSerial(serial) {
            return serial === requestSerial
        }

        function refreshSelect(select, placeholder, payload, selectedValue, serial) {
            setLoading(select, true)
            return fetchOptions(filterApiUrl, payload)
                .then(function (json) {
                    if (!isCurrentSerial(serial)) {
                        return null
                    }
                    suppressEvents = true
                    try {
                        renderSelect(select, placeholder, toItems(json), selectedValue)
                    } finally {
                        suppressEvents = false
                    }
                    return getSelectValue(select)
                })
                .catch(function (error) {
                    if (window.console && window.console.error) {
                        window.console.error(error)
                    }
                    if (isCurrentSerial(serial)) {
                        suppressEvents = true
                        try {
                            renderSelect(select, placeholder, [], "")
                        } finally {
                            suppressEvents = false
                        }
                    }
                    return ""
                })
                .finally(function () {
                    if (isCurrentSerial(serial)) {
                        setLoading(select, false)
                    }
                })
        }

        function hydrateFromCurrentFilters() {
            if (!state.cityId && !state.adminId && !state.electoralId) {
                return Promise.resolve()
            }

            var serial = nextRequestSerial()

            if (state.cityId) {
                return refreshSelect(
                    adminSelect,
                    "All administrative wards",
                    { type: "administrative", city: [state.cityId] },
                    state.adminId,
                    serial
                ).then(function (adminValue) {
                    if (!isCurrentSerial(serial)) {
                        return null
                    }
                    state.adminId = adminValue || ""

                    var electoralPayload = { type: "electoral", city: [state.cityId] }
                    if (state.adminId) {
                        electoralPayload.admin = [state.adminId]
                    }

                    return refreshSelect(
                        electoralSelect,
                        "All electoral wards",
                        electoralPayload,
                        state.electoralId,
                        serial
                    )
                }).then(function (electoralValue) {
                    if (!isCurrentSerial(serial)) {
                        return null
                    }
                    state.electoralId = electoralValue || ""

                    var slumPayload = { type: "slum", city: [state.cityId] }
                    if (state.adminId) {
                        slumPayload.admin = [state.adminId]
                    }
                    if (state.electoralId) {
                        slumPayload.electoral = [state.electoralId]
                    }

                    return refreshSelect(
                        slumSelect,
                        "All slums",
                        slumPayload,
                        state.slumId,
                        serial
                    )
                }).then(function (slumValue) {
                    if (isCurrentSerial(serial)) {
                        state.slumId = slumValue || ""
                    }
                })
            }

            if (state.adminId) {
                return refreshSelect(
                    electoralSelect,
                    "All electoral wards",
                    { type: "electoral", admin: [state.adminId] },
                    state.electoralId,
                    serial
                ).then(function (electoralValue) {
                    if (!isCurrentSerial(serial)) {
                        return null
                    }
                    state.electoralId = electoralValue || ""

                    var slumPayload = { type: "slum", admin: [state.adminId] }
                    if (state.electoralId) {
                        slumPayload.electoral = [state.electoralId]
                    }

                    return refreshSelect(
                        slumSelect,
                        "All slums",
                        slumPayload,
                        state.slumId,
                        serial
                    )
                }).then(function (slumValue) {
                    if (isCurrentSerial(serial)) {
                        state.slumId = slumValue || ""
                    }
                })
            }

            return refreshSelect(
                slumSelect,
                "All slums",
                { type: "slum", electoral: [state.electoralId] },
                state.slumId,
                serial
            ).then(function (slumValue) {
                if (isCurrentSerial(serial)) {
                    state.slumId = slumValue || ""
                }
            })
        }

        function reloadAfterCityChange() {
            var serial = nextRequestSerial()
            var cityId = getSelectValue(citySelect)
            state.cityId = cityId
            state.adminId = ""
            state.electoralId = ""
            state.slumId = ""

            var adminPayload = { type: "administrative" }
            var electoralPayload = { type: "electoral" }
            var slumPayload = { type: "slum" }

            appendFilters(adminPayload, { cityId: cityId })
            appendFilters(electoralPayload, { cityId: cityId })
            appendFilters(slumPayload, { cityId: cityId })

            setLoading(adminSelect, true)
            setLoading(electoralSelect, true)
            setLoading(slumSelect, true)

            return Promise.all([
                refreshSelect(adminSelect, "All administrative wards", adminPayload, "", serial),
                refreshSelect(electoralSelect, "All electoral wards", electoralPayload, "", serial),
                refreshSelect(slumSelect, "All slums", slumPayload, "", serial),
            ]).then(function () {
                if (isCurrentSerial(serial)) {
                    state.adminId = ""
                    state.electoralId = ""
                    state.slumId = ""
                }
            })
        }

        function reloadAfterAdminChange() {
            var serial = nextRequestSerial()
            var cityId = getSelectValue(citySelect)
            var adminId = getSelectValue(adminSelect)

            state.adminId = adminId
            state.electoralId = ""
            state.slumId = ""

            var electoralPayload = { type: "electoral" }
            var slumPayload = { type: "slum" }
            appendFilters(electoralPayload, { cityId: cityId, adminId: adminId })
            appendFilters(slumPayload, { cityId: cityId, adminId: adminId })

            setLoading(electoralSelect, true)
            setLoading(slumSelect, true)

            return Promise.all([
                refreshSelect(electoralSelect, "All electoral wards", electoralPayload, "", serial),
                refreshSelect(slumSelect, "All slums", slumPayload, "", serial),
            ]).then(function () {
                if (isCurrentSerial(serial)) {
                    state.electoralId = ""
                    state.slumId = ""
                }
            })
        }

        function reloadAfterElectoralChange() {
            var serial = nextRequestSerial()
            var cityId = getSelectValue(citySelect)
            var adminId = getSelectValue(adminSelect)
            var electoralId = getSelectValue(electoralSelect)

            state.electoralId = electoralId
            state.slumId = ""

            var slumPayload = { type: "slum" }
            appendFilters(slumPayload, { cityId: cityId, adminId: adminId, electoralId: electoralId })

            return refreshSelect(slumSelect, "All slums", slumPayload, "", serial).then(function () {
                if (isCurrentSerial(serial)) {
                    state.slumId = ""
                }
            })
        }

        function bindChangeEvents() {
            if (!window.jQuery || !window.jQuery.fn) {
                return
            }

            window.jQuery(citySelect).on("change.rimfilters", function () {
                if (suppressEvents) {
                    return
                }
                reloadAfterCityChange()
            })

            window.jQuery(adminSelect).on("change.rimfilters", function () {
                if (suppressEvents) {
                    return
                }
                reloadAfterAdminChange()
            })

            window.jQuery(electoralSelect).on("change.rimfilters", function () {
                if (suppressEvents) {
                    return
                }
                reloadAfterElectoralChange()
            })

            window.jQuery(slumSelect).on("change.rimfilters", function () {
                if (suppressEvents) {
                    return
                }
                state.slumId = getSelectValue(slumSelect)
            })
        }

        function initControls() {
            initSelect2(citySelect)
            initSelect2(adminSelect)
            initSelect2(electoralSelect)
            initSelect2(slumSelect)
        }

        function syncInitialValues() {
            suppressEvents = true
            if (citySelect) {
                citySelect.value = state.cityId
            }
            if (adminSelect) {
                adminSelect.value = state.adminId
            }
            if (electoralSelect) {
                electoralSelect.value = state.electoralId
            }
            if (slumSelect) {
                slumSelect.value = state.slumId
            }
            suppressEvents = false
        }

        function setupReset() {
            if (clearBtn && searchInput && searchForm) {
                clearBtn.addEventListener("click", function () {
                    searchInput.value = ""
                    searchForm.submit()
                })
            }
        }

        function setupDeleteGuard() {
            if (!deleteBtn) {
                return
            }

            deleteBtn.addEventListener("click", function (event) {
                var checked = document.querySelectorAll("input[name=\"selectcheckbox\"]:checked")
                if (checked.length === 0) {
                    event.preventDefault()
                    alert("Please select at least one row to delete.")
                    return
                }
                if (!confirm("Are you sure you want to delete " + checked.length + " record(s)?")) {
                    event.preventDefault()
                }
            })
        }

        initControls()
        syncInitialValues()
        bindChangeEvents()
        setupReset()
        setupDeleteGuard()

        hydrateFromCurrentFilters()
    }

    document.addEventListener("DOMContentLoaded", main)
})();
/* =========================================================
   RIM Add-New Modal
   ========================================================= */
(function () {
    var $page = $('#rim-page');
    var CITY_LIST_URL = $page.data('city-list-url');
    var ADMIN_LIST_URL = $page.data('admin-list-url');
    var ELECTORAL_LIST_URL = $page.data('electoral-list-url');
    var SLUM_LIST_URL = $page.data('slum-list-url');
    var RIM_CHECK_URL = $page.data('rim-check-url');
    var RIM_EDIT_BASE = $page.data('rim-edit-base');
    var RIM_INSERT_URL = $page.data('rim-insert-url');

    window.openRimSelectModal = function () {
        $('#rs-overlay').addClass('rs-open');
        rsResetModal();
        rsLoadCities();
    };

    window.closeRimSelectModal = function () {
        $('#rs-overlay').removeClass('rs-open');
    };

    function rsResetModal() {
        $('#rs_admin_field, #rs_electoral_field, #rs_slum_field').hide();
        $('#rs_admin, #rs_electoral, #rs_slum').empty().prop('disabled', true);
        $('#rs_city').prop('disabled', false);
        $('#rs-continue, #rs-cancel').prop('disabled', false);
        $('#rs-status').hide();
    }

    function rsPopulateSelect($select, json, placeholder) {
        $select.empty().append('<option value="0">' + placeholder + '</option>');
        for (var i = 0; i < json.nameArray.length; i++) {
            $select.append('<option value="' + json.idArray[i] + '">' + json.nameArray[i] + '</option>');
        }
    }

    function rsLoadCities() {
        $.ajax({
            url: CITY_LIST_URL,
            type: 'GET',
            success: function (json) {
                rsPopulateSelect($('#rs_city'), json, '---select city---');
            }
        });
    }

    function rsLoadAdminWards(cityId) {
        $.ajax({
            url: ADMIN_LIST_URL,
            data: { id: cityId },
            type: 'POST',
            success: function (json) {
                rsPopulateSelect($('#rs_admin'), json, '---select admin ward---');
                $('#rs_admin').prop('disabled', false);
            }
        });
    }

    function rsLoadElectoralWards(adminId) {
        $.ajax({
            url: ELECTORAL_LIST_URL,
            data: { id: adminId },
            type: 'POST',
            success: function (json) {
                rsPopulateSelect($('#rs_electoral'), json, '---select electoral ward---');
                $('#rs_electoral').prop('disabled', false);
            }
        });
    }

    function rsLoadSlums(electoralId) {
        $.ajax({
            url: SLUM_LIST_URL,
            data: { id: electoralId },
            type: 'POST',
            success: function (json) {
                rsPopulateSelect($('#rs_slum'), json, '---select slum---');
                $('#rs_slum').prop('disabled', false);
                rsCheckContinueEnabled();
            }
        });
    }

    function rsCheckContinueEnabled() {
        var slumId = $('#rs_slum').val();
        $('#rs-continue').prop('disabled', !slumId || slumId === '0');
    }

    $(document).on('change', '#rs_city', function () {
        var cityId = $(this).val();
        $('#rs_electoral_field, #rs_slum_field').hide();
        $('#rs_electoral, #rs_slum').empty().prop('disabled', true);
        $('#rs-continue').prop('disabled', true);

        if (!cityId || cityId === '0') {
            $('#rs_admin_field').hide();
            return;
        }
        $('#rs_admin_field').show();
        rsLoadAdminWards(cityId);
    });

    $(document).on('change', '#rs_admin', function () {
        var adminId = $(this).val();
        $('#rs_slum_field').hide();
        $('#rs_slum').empty().prop('disabled', true);
        $('#rs-continue').prop('disabled', true);

        if (!adminId || adminId === '0') {
            $('#rs_electoral_field').hide();
            return;
        }
        $('#rs_electoral_field').show();
        rsLoadElectoralWards(adminId);
    });

    $(document).on('change', '#rs_electoral', function () {
        var electoralId = $(this).val();
        $('#rs-continue').prop('disabled', true);

        if (!electoralId || electoralId === '0') {
            $('#rs_slum_field').hide();
            return;
        }
        $('#rs_slum_field').show();
        rsLoadSlums(electoralId);
    });

    $(document).on('change', '#rs_slum', rsCheckContinueEnabled);

    $(document).on('click', '#rs-cancel', function () {
        closeRimSelectModal();
    });

    $(document).on('click', '#rs-overlay', function (e) {
        if (e.target.id === 'rs-overlay') closeRimSelectModal();
    });

    $(document).on('click', '#rs-continue', function () {
        var slumId = $('#rs_slum').val();
        if (!slumId || slumId === '0') return;

        $('#rs-continue, #rs-cancel, #rs_city, #rs_admin, #rs_electoral, #rs_slum').prop('disabled', true);

        $.ajax({
            url: RIM_CHECK_URL,
            data: { slum_id: slumId },
            type: 'POST',
            dataType: 'json',
            success: function (res) {
                if (res.exists) {
                    var seconds = 5;
                    var targetUrl = RIM_EDIT_BASE + res.rim_id;
                    var $status = $('#rs-status').show();

                    var render = function () {
                        $status.html(
                            'A RIM record already exists for this slum. Redirecting you to edit it in ' + seconds + 's&hellip;'
                        );
                    };
                    render();

                    var timer = setInterval(function () {
                        seconds -= 1;
                        if (seconds <= 0) {
                            clearInterval(timer);
                            window.location.href = targetUrl;
                            return;
                        }
                        render();
                    }, 1000);
                } else {
                    window.location.href = RIM_INSERT_URL + '?slum=' + slumId;
                }
            },
            error: function () {
                $('#rs-status')
                    .show()
                    .css({ background: '#fdecec', color: '#b3261e' })
                    .text('Something went wrong checking this slum. Please try again.');
                $('#rs-continue, #rs-cancel, #rs_city, #rs_admin, #rs_electoral, #rs_slum').prop('disabled', false);
            }
        });
    });
})();
