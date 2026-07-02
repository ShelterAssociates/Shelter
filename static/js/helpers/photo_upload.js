/* photo_upload.js — drives the Photo Upload Django admin page */
; (function ($) {
    'use strict'

    /* ── helpers ── */
    function getConfig() {
        var $c = $('#photoUploadContainer')
        return {
            isSuperuser: $c.data('is-superuser') === true || $c.data('is-superuser') === 'true',
            cityListUrl: $c.data('city-list-url'),
            adminWardListUrl: $c.data('administrative-ward-list-url'),
            electoralWardListUrl: $c.data('electoral-ward-list-url'),
            slumListUrl: $c.data('slum-list-url'),
            sponsorListUrl: $c.data('sponsor-list-url'),
            photoTypeItemsUrl: $c.data('photo-type-items-url'),
            manageTreeUrl: $c.data('manage-tree-url'),
            manageToggleUrl: $c.data('manage-toggle-url'),
            manageAddUrl: $c.data('manage-add-url'),
            uploadUrl: $c.data('upload-url'),
            defaultPhotoDate: $c.data('default-photo-date'),
            csrfToken: $('input[name="csrfmiddlewaretoken"]').val()
        }
    }

    var cfg = getConfig()

    /*
     * populate a <select> from the API response format:
     *   { idArray: [1,2,3], nameArray: ['A','B','C'] }
     * OR a plain array of objects: [{id,name}, ...]
     */
    function populateSelect($sel, data, placeholder) {
        $sel.empty().append($('<option value="">').text(placeholder || '— Select —'))

        if (data && data.idArray && data.nameArray) {
            /* parallel-array format used by cityList, administrativewardList, etc. */
            $.each(data.idArray, function (i, id) {
                $sel.append($('<option>').val(id).text(data.nameArray[i]))
            })
        } else if ($.isArray(data)) {
            /* array-of-objects format */
            $.each(data, function (i, item) {
                $sel.append($('<option>').val(item.id).text(item.name))
            })
        }

        $sel.prop('disabled', false)
    }

    function disableSelect($sel, placeholder) {
        $sel.empty().append($('<option value="">').text(placeholder || '— Select —'))
        $sel.prop('disabled', true)
    }

    function loadCities() {
        $.get(cfg.cityListUrl, function (data) {
            populateSelect($('#city'), data, '— Select City —')
        })
    }

    /* ════════════════════════════════════════
       1. LOCATION CASCADE
       ════════════════════════════════════════ */

    /* Load cities on page load */
    loadCities()

    /* Load sponsor projects on page load */
    $.get(cfg.sponsorListUrl, function (data) {
        populateSelect($('#sponsor_project'), data, '— Select Sponsor Project —')
    }).fail(function () {
        // sponsor project list failed to load; the field still validates normally
    })

    $('#city').on('change', function () {
        var cityId = $(this).val()
        disableSelect($('#admin_ward'), '— Select Administrative Ward —')
        disableSelect($('#electoral_ward'), '— Select Electoral Ward —')
        disableSelect($('#slum'), '— Select Slum —')
        syncFieldValidity('cityField')
        syncFieldValidity('slumField')
        if (!cityId) return
        /* administrativewardList expects POST with param 'id' */
        $.post(cfg.adminWardListUrl, { id: cityId, csrfmiddlewaretoken: cfg.csrfToken }, function (data) {
            populateSelect($('#admin_ward'), data, '— Select Administrative Ward —')
        })
    })

    $('#admin_ward').on('change', function () {
        var wardId = $(this).val()
        disableSelect($('#electoral_ward'), '— Select Electoral Ward —')
        disableSelect($('#slum'), '— Select Slum —')
        syncFieldValidity('slumField')
        if (!wardId) return
        /* electoralWardList expects POST with param 'id' */
        $.post(cfg.electoralWardListUrl, { id: wardId, csrfmiddlewaretoken: cfg.csrfToken }, function (data) {
            populateSelect($('#electoral_ward'), data, '— Select Electoral Ward —')
        })
    })

    $('#electoral_ward').on('change', function () {
        var eWardId = $(this).val()
        disableSelect($('#slum'), '— Select Slum —')
        syncFieldValidity('slumField')
        if (!eWardId) return
        /* slumList expects POST with param 'id' */
        $.post(cfg.slumListUrl, { id: eWardId, csrfmiddlewaretoken: cfg.csrfToken }, function (data) {
            populateSelect($('#slum'), data, '— Select Slum —')
        })
    })

    /* ════════════════════════════════════════
       2. PHOTO TYPE CASCADING PICKER
       API returns: [{id, name, parent_id, has_children, full_path}, ...]
       Fetched level by level via ?parent_id=X
       ════════════════════════════════════════ */

    var $picker = $('#photoTypePicker')
    var $hiddenTypeId = $('#photo_type_item_id')
    var $summary = $('#photoTypeSummary')
    var $cityLevel = $('#is_city_level')
    var $otherUpload = $('#is_other_upload')
    var $photoDate = $('#photo_date')
    var $customFolder = $('#custom_folder_name')
    var $projectType = $('#project_type')
    var $projectTypeOtherField = $('#projectTypeOtherField')
    var $projectTypeOther = $('#project_type_other')
    var $photoComment = $('#photo_comment')
    var photoTypePickerRequestId = 0

    function currentUploadMode() {
        var isOther = $otherUpload.is(':checked')
        var isCityLevel = $cityLevel.is(':checked') && !isOther
        return {
            isOther: isOther,
            isCityLevel: isCityLevel
        }
    }

    function isBlank(value) {
        return !value || !$.trim(String(value))
    }

    function setFieldValidity(fieldId, isValid) {
        var $field = $('#' + fieldId)
        if ($field.length) {
            $field.toggleClass('pu-field-invalid', !isValid)
        }
    }

    function isPhotoDateValid() {
        var value = $photoDate.val()
        if (isBlank(value)) return false
        var today = new Date().toISOString().slice(0, 10)
        return value <= today
    }

    function isPhotosValid() {
        var fileInput = $('#photos')[0]
        return !!(fileInput && fileInput.files && fileInput.files.length > 0 && fileInput.files.length <= 5)
    }

    function isProjectTypeOtherValid() {
        return $projectType.val() !== 'Other' || !isBlank($projectTypeOther.val())
    }

    function syncFieldValidity(fieldId) {
        var mode = currentUploadMode()
        var isValid = true

        if (fieldId === 'photoDateField') {
            isValid = isPhotoDateValid()
        } else if (fieldId === 'projectTypeField') {
            isValid = !isBlank($projectType.val())
        } else if (fieldId === 'projectTypeOtherField') {
            isValid = isProjectTypeOtherValid()
        } else if (fieldId === 'sponsorProjectField') {
            isValid = !isBlank($('#sponsor_project').val())
        } else if (fieldId === 'photosField') {
            isValid = isPhotosValid()
        } else if (fieldId === 'customFolderField') {
            isValid = !mode.isOther || !isBlank($customFolder.val())
        } else if (fieldId === 'cityField') {
            isValid = !mode.isCityLevel || !isBlank($('#city').val())
        } else if (fieldId === 'slumField') {
            isValid = mode.isOther || mode.isCityLevel || !isBlank($('#slum').val())
        } else if (fieldId === 'photoTypeField') {
            isValid = mode.isOther || !isBlank($hiddenTypeId.val())
        }

        setFieldValidity(fieldId, isValid)
        return isValid
    }

    function syncRelevantValidationState() {
        var mode = currentUploadMode()

        syncFieldValidity('photoDateField')
        syncFieldValidity('projectTypeField')
        syncFieldValidity('projectTypeOtherField')
        syncFieldValidity('sponsorProjectField')
        syncFieldValidity('photosField')

        if (mode.isOther) {
            syncFieldValidity('customFolderField')
        } else if (mode.isCityLevel) {
            syncFieldValidity('cityField')
            syncFieldValidity('photoTypeField')
        } else {
            syncFieldValidity('slumField')
            syncFieldValidity('photoTypeField')
        }
    }

    function clearValidationState() {
        $('.pu-field-invalid').removeClass('pu-field-invalid')
    }

    if ($photoDate.length) {
        var today = cfg.defaultPhotoDate || new Date().toISOString().slice(0, 10)
        $photoDate.val(today)
        $photoDate.attr('max', today)
    }

    function clearLevelsAfter(levelIndex) {
        $picker.find('.photo-type-level-row').each(function () {
            if ($(this).data('level') > levelIndex) $(this).remove()
        })
    }

    function updateSummary() {
        var parts = []
        $picker.find('.photo-type-level-row select').each(function () {
            var $selected = $(this).find('option:selected')
            var value = $(this).val()
            if (value) {
                var label = $.trim($selected.text())
                if (label) parts.push(label)
            }
        })

        if (parts.length) {
            $summary.html('<strong>Selected path:</strong> ' + $('<div>').text(parts.join(' / ')).html())
        } else {
            $summary.text('Select a photo type to see the full path here.')
        }
    }

    function syncProjectTypeOtherField() {
        var isOtherProjectType = $projectType.val() === 'Other'

        if (isOtherProjectType) {
            $projectTypeOtherField.removeClass('pu-hidden')
            $projectTypeOther.prop('required', true)
        } else {
            $projectTypeOtherField.addClass('pu-hidden')
            $projectTypeOther.prop('required', false)
            $projectTypeOther.val('')
        }

        syncFieldValidity('projectTypeField')
        syncFieldValidity('projectTypeOtherField')
    }

    function addLevelRow(items, levelIndex, labelText) {
        var $row = $('<div class="photo-row photo-type-level-row">').data('level', levelIndex)
        var rowId = 'photo_type_level_' + levelIndex
        $row.append($('<label>').attr('for', rowId).text(labelText || 'Level ' + (levelIndex + 1)))

        var $sel = $('<select>').attr('id', rowId)
        $sel.append($('<option value="">— Select —</option>'))
        $.each(items, function (i, item) {
            $sel.append($('<option>').val(item.id).text(item.name).attr('title', item.full_path || item.name).data('has-children', item.has_children))
        })
        $row.append($sel)
        $picker.append($row)

        $sel.on('change', function () {
            var selectedId = $(this).val()
            var hasChildren = $(this).find(':selected').data('has-children')
            clearLevelsAfter(levelIndex)
            $hiddenTypeId.val('')
            checkUploadReady()
            updateSummary()
            syncFieldValidity('photoTypeField')

            if (!selectedId) return

            if (hasChildren) {
                /* fetch next level */
                $.get(cfg.photoTypeItemsUrl, { parent_id: selectedId }, function (data) {
                    if (data && data.length > 0) {
                        addLevelRow(data, levelIndex + 1, getLevelLabel(levelIndex + 1))
                    } else {
                        /* no children returned — treat as leaf */
                        $hiddenTypeId.val(selectedId)
                        checkUploadReady()
                        updateSummary()
                        syncFieldValidity('photoTypeField')
                    }
                }).fail(function () {
                    $hiddenTypeId.val(selectedId)
                    checkUploadReady()
                    updateSummary()
                    syncFieldValidity('photoTypeField')
                })
            } else {
                /* leaf node — set value directly */
                $hiddenTypeId.val(selectedId)
                checkUploadReady()
                updateSummary()
                syncFieldValidity('photoTypeField')
            }
        })
    }

    function getLevelLabel(index) {
        var labels = ['Photo Category', 'Sub-category', 'Type', 'Sub-type', 'Detail']
        return labels[index] || 'Level ' + (index + 1)
    }

    function setUploadMode() {
        var mode = currentUploadMode()
        var isOther = mode.isOther
        var isCityLevel = mode.isCityLevel

        if (isOther) {
            $cityLevel.prop('checked', false)
        }
        if (isCityLevel) {
            $otherUpload.prop('checked', false)
        }

        if (isOther) {
            $('#cityField, #adminWardField, #electoralWardField, #slumField, #photoTypeField').addClass('pu-hidden')
            $('#customFolderField').removeClass('pu-hidden')
            disableSelect($('#city'), '— Select City —')
            disableSelect($('#admin_ward'), '— Select Administrative Ward —')
            disableSelect($('#electoral_ward'), '— Select Electoral Ward —')
            disableSelect($('#slum'), '— Select Slum —')
            $hiddenTypeId.val('')
            $picker.empty()
            $summary.text('Other upload selected. Enter a custom folder name.')
        } else {
            $('#cityField, #adminWardField, #electoralWardField, #slumField, #photoTypeField').removeClass('pu-hidden')
            $('#customFolderField').addClass('pu-hidden')
            $('#city').prop('disabled', false)

            if ($('#city option').length <= 1) {
                loadCities()
            }

            if (isCityLevel) {
                $('#adminWardField, #electoralWardField, #slumField').addClass('pu-hidden')
                disableSelect($('#admin_ward'), '— Select Administrative Ward —')
                disableSelect($('#electoral_ward'), '— Select Electoral Ward —')
                disableSelect($('#slum'), '— Select Slum —')
                $summary.text('City level activity selected. Choose a city and photo type.')
            } else {
                $('#admin_ward').prop('disabled', false)
                $('#electoral_ward').prop('disabled', false)
                $('#slum').prop('disabled', false)
                if (!$picker.children().length) {
                    initPhotoTypePicker()
                }
            }
        }

        clearValidationState()
        checkUploadReady()
    }

    $cityLevel.on('change', function () {
        setUploadMode()
    })

    $otherUpload.on('change', function () {
        setUploadMode()
    })

    function initPhotoTypePicker() {
        var requestId = ++photoTypePickerRequestId
        $picker.empty()
        $hiddenTypeId.val('')
        updateSummary()
        $.get(cfg.photoTypeItemsUrl, function (data) {
            if (requestId !== photoTypePickerRequestId) return
            if (data && data.length > 0) {
                addLevelRow(data, 0, getLevelLabel(0))
            } else {
                $picker.html('<div style="font-size:12px;color:#9ca3af;padding:6px 0;">No photo types available.</div>')
            }
        }).fail(function (xhr) {
            if (requestId !== photoTypePickerRequestId) return
            $picker.html('<div style="font-size:12px;color:#991b1b;padding:6px 0;">Error loading photo types.</div>')
        })
    }

    initPhotoTypePicker()
    syncProjectTypeOtherField()

    /* ════════════════════════════════════════
       3. UPLOAD READINESS & SUBMIT
       ════════════════════════════════════════ */

    function checkUploadReady() {
        var mode = currentUploadMode()
        var isOther = mode.isOther
        var isCityLevel = mode.isCityLevel
        var photoDate = $photoDate.val()
        var slumId = $('#slum').val()
        var typeId = $hiddenTypeId.val()
        var projectType = $projectType.val()
        var projectTypeOtherValid = projectType !== 'Other' || ($projectTypeOther.val() && $projectTypeOther.val().trim())
        var hasPhotos = $('#photos')[0] && $('#photos')[0].files && $('#photos')[0].files.length > 0
        var today = new Date().toISOString().slice(0, 10)
        var validDate = photoDate && photoDate <= today
        var customFolderValid = !isOther || ($('#custom_folder_name').val() && $('#custom_folder_name').val().trim())
        var locationValid = isOther ? true : (isCityLevel ? $('#city').val() : slumId)
        var typeValid = isOther ? true : typeId
        var projectTypeValid = !!projectType
        var sponsorProjectValid = !isBlank($('#sponsor_project').val())
        $('#uploadButton').prop('disabled', !(locationValid && typeValid && projectTypeValid && projectTypeOtherValid && hasPhotos && validDate && customFolderValid && sponsorProjectValid))
    }

    $('#sponsor_project').on('change', function () {
        checkUploadReady()
        syncFieldValidity('sponsorProjectField')
    })
    $('#photos').on('change', function () {
        checkUploadReady()
        syncFieldValidity('photosField')
    })
    $('#city').on('change', function () {
        checkUploadReady()
        syncFieldValidity('cityField')
        syncFieldValidity('slumField')
    })
    $('#photo_date').on('change keyup', function () {
        checkUploadReady()
        syncFieldValidity('photoDateField')
    })
    $('#custom_folder_name').on('change keyup', function () {
        checkUploadReady()
        syncFieldValidity('customFolderField')
    })
    $('#project_type').on('change keyup', function () {
        syncProjectTypeOtherField()
        checkUploadReady()
        syncFieldValidity('projectTypeField')
        syncFieldValidity('projectTypeOtherField')
    })
    $('#project_type_other').on('change keyup', function () {
        syncProjectTypeOtherField()
        checkUploadReady()
        syncFieldValidity('projectTypeOtherField')
    })
    $('#photo_comment').on('change keyup', checkUploadReady)

    $('#slum').on('change', function () {
        checkUploadReady()
        syncFieldValidity('slumField')
    })

    function setStatus(type, html) {
        var $s = $('#uploadStatus')
        $s.removeClass('success error loading').addClass(type).html(html).show()
        if (type === 'success' || type === 'error') {
            $('html, body').animate({ scrollTop: $s.offset().top - 20 }, 300)
        }
    }

    var $confirmModal = $('#photoUploadConfirmModal')
    var $confirmDate = $('#photoUploadConfirmDate')
    var $confirmSummary = $('#photoUploadConfirmSummary')
    var confirmAccepted = false

    function escapeHtml(value) {
        return $('<div>').text(value == null ? '' : String(value)).html()
    }

    function selectedText($element, fallback) {
        if (!$element.length) return fallback || '—'
        var value = $.trim($element.find('option:selected').text())
        return value && value !== '— Select —' ? value : (fallback || '—')
    }

    function selectedPhotoTypePath() {
        var parts = []
        $picker.find('.photo-type-level-row select').each(function () {
            var text = $.trim($(this).find('option:selected').text())
            if (text && text !== '— Select —') {
                parts.push(text)
            }
        })
        return parts.length ? parts.join(' / ') : '—'
    }

    function selectedFilesSummary() {
        var fileInput = $('#photos')[0]
        if (!fileInput || !fileInput.files || !fileInput.files.length) return '—'
        var names = []
        $.each(fileInput.files, function (i, file) {
            names.push(file.name)
        })
        return names.join(', ')
    }

    function buildConfirmationSummary() {
        var isOther = $otherUpload.is(':checked')
        var isCityLevel = $cityLevel.is(':checked') && !isOther
        var projectType = $projectType.val() || '—'
        var rows = []

        function addRow(label, value) {
            rows.push('<div class="pu-confirm-row"><div class="pu-confirm-key">' + escapeHtml(label) + '</div><div class="pu-confirm-value">' + escapeHtml(value || '—') + '</div></div>')
        }

        addRow('Mode', isOther ? 'Other upload' : (isCityLevel ? 'City level activity' : 'Slum upload'))
        addRow('City', isOther ? '—' : selectedText($('#city'), '—'))
        addRow('Administrative ward', isOther ? '—' : selectedText($('#admin_ward'), '—'))
        addRow('Electoral ward', isOther ? '—' : selectedText($('#electoral_ward'), '—'))
        addRow('Slum', isOther ? '—' : selectedText($('#slum'), '—'))
        addRow('Photo type', isOther ? '—' : selectedPhotoTypePath())
        addRow('Project type', projectType === 'Other' ? projectType + ' / ' + ($projectTypeOther.val() || '—') : projectType)
        addRow('Sponsor project', selectedText($('#sponsor_project'), '—'))
        addRow('Custom folder', isOther ? ($('#custom_folder_name').val() || '—') : '—')
        addRow('Photo comment', $('#photo_comment').val() || '—')
        addRow('Photos', selectedFilesSummary())

        $confirmDate.text($('#photo_date').val())
        $confirmSummary.html(rows.join(''))
    }

    function openConfirmModal() {
        buildConfirmationSummary()
        $confirmModal.removeClass('pu-hidden').attr('aria-hidden', 'false')
        $('body').css('overflow', 'hidden')
        $confirmModal.find('#photoUploadConfirmProceed').trigger('focus')
    }

    function closeConfirmModal() {
        $confirmModal.addClass('pu-hidden').attr('aria-hidden', 'true')
        $('body').css('overflow', '')
    }

    function performUpload() {
        var today = new Date().toISOString().slice(0, 10)
        var formData = new FormData($('#photoUploadForm')[0])
        var isOther = $otherUpload.is(':checked')
        var isCityLevel = $cityLevel.is(':checked') && !isOther
        var projectType = $projectType.val() || ''

        formData.set('is_city_level', isCityLevel ? '1' : '0')
        formData.set('is_other_upload', isOther ? '1' : '0')
        formData.set('custom_folder_name', $('#custom_folder_name').val() || '')
        formData.set('photo_date', $('#photo_date').val() || '')
        formData.set('project_type', projectType)
        formData.set('project_type_other', projectType === 'Other' ? ($projectTypeOther.val() || '') : '')
        formData.set('photo_comment', $('#photo_comment').val() || '')

        $('#uploadButton').prop('disabled', true)
        setStatus('loading', '⏳ Uploading and encrypting photos…')

        $.ajax({
            url: cfg.uploadUrl,
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function (resp) {
                var payload = resp && resp.data ? resp.data : resp
                var isSuccess = resp && (resp.status === 'success' || resp.success)

                if (isSuccess) {
                    var link = payload && payload.folder_url
                        ? ' <a href="' + payload.folder_url + '" target="_blank">View folder ↗</a>'
                        : ''
                    setStatus('success', '✅ ' + ((payload && payload.message) || (resp && resp.message) || 'Photos uploaded successfully!') + link)
                    $('#photoUploadForm')[0].reset()
                    $photoDate.val(cfg.defaultPhotoDate || today)
                    $photoDate.attr('max', today)
                    $customFolder.val('')
                    $projectType.val('')
                    $projectTypeOther.val('')
                    $photoComment.val('')
                    $cityLevel.prop('checked', false)
                    $otherUpload.prop('checked', false)
                    syncProjectTypeOtherField()
                    loadCities()
                    initPhotoTypePicker()
                    disableSelect($('#admin_ward'), '— Select Administrative Ward —')
                    disableSelect($('#electoral_ward'), '— Select Electoral Ward —')
                    disableSelect($('#slum'), '— Select Slum —')
                    $('#customFolderField').addClass('pu-hidden')
                    $('#cityField, #adminWardField, #electoralWardField, #slumField, #photoTypeField').removeClass('pu-hidden')
                    clearValidationState()
                } else {
                    setStatus('error', '❌ ' + (resp && resp.message ? resp.message : 'Upload failed. Please try again.'))
                }
                $('#uploadButton').prop('disabled', false)
                checkUploadReady()
                closeConfirmModal()
                confirmAccepted = false
            },
            error: function (xhr) {
                var msg = 'Upload failed.'
                try {
                    var r = JSON.parse(xhr.responseText)
                    if (r && r.message) msg = r.message
                } catch (ex) { }
                setStatus('error', '❌ ' + msg)
                $('#uploadButton').prop('disabled', false)
                checkUploadReady()
                closeConfirmModal()
                confirmAccepted = false
            }
        })
    }

    $('#photoUploadConfirmProceed').on('click', function () {
        confirmAccepted = true
        closeConfirmModal()
        performUpload()
    })

    $('#photoUploadConfirmCancel, .pu-modal [data-modal-close]').on('click', function () {
        closeConfirmModal()
        confirmAccepted = false
    })

    $(document).on('keydown', function (e) {
        if (e.key === 'Escape' && !$confirmModal.hasClass('pu-hidden')) {
            closeConfirmModal()
            confirmAccepted = false
        }
    })

    $('#photoUploadForm').on('submit', function (e) {
        e.preventDefault()

        syncRelevantValidationState()

        var files = $('#photos')[0].files
        if (!files || files.length === 0) {
            setStatus('error', 'Please select at least one photo.')
            return
        }
        if (files.length > 5) {
            setStatus('error', 'Maximum 5 photos per upload.')
            return
        }

        var isOther = $otherUpload.is(':checked')
        var isCityLevel = $cityLevel.is(':checked') && !isOther
        var today = new Date().toISOString().slice(0, 10)

        if (!$('#photo_date').val()) {
            setStatus('error', 'Please select a photo date.')
            return
        }
        if ($('#photo_date').val() > today) {
            setStatus('error', 'Photo date cannot be in the future.')
            return
        }

        if (!$projectType.val()) {
            setStatus('error', 'Please select a project type.')
            return
        }
        if ($projectType.val() === 'Other' && (!$projectTypeOther.val() || !$projectTypeOther.val().trim())) {
            setStatus('error', 'Please specify the project type.')
            return
        }

        if (!$('#sponsor_project').val()) {
            setStatus('error', 'Please select a sponsor project.')
            return
        }

        if (isOther) {
            if (!$('#custom_folder_name').val() || !$('#custom_folder_name').val().trim()) {
                setStatus('error', 'Please enter a custom folder name.')
                return
            }
        } else if (isCityLevel) {
            if (!$('#city').val()) {
                setStatus('error', 'Please select a city.')
                return
            }
            if (!$hiddenTypeId.val()) {
                setStatus('error', 'Please complete the photo type selection.')
                return
            }
        } else {
            if (!$('#slum').val()) {
                setStatus('error', 'Please select a slum.')
                return
            }
            if (!$hiddenTypeId.val()) {
                setStatus('error', 'Please complete the photo type selection.')
                return
            }
        }

        if (!confirmAccepted) {
            openConfirmModal()
            return
        }

        confirmAccepted = false
        performUpload()
    })

    setUploadMode()

    /* ════════════════════════════════════════
       4. SUPERUSER MANAGEMENT TREE
       ════════════════════════════════════════ */

    if (!cfg.isSuperuser) return  /* non-superuser stops here */

    function renderNode(node, depth) {
        var hasChildren = node.children && node.children.length > 0
        var isRoot = depth === 0

        var $wrap = $('<div class="tree-node">')
        var $row = $('<div class="tree-row">')

        /* chevron toggle */
        var $tog = $('<button class="tree-toggle" type="button" aria-label="expand">')
        $tog.html('<svg viewBox="0 0 24 24"><polyline points="9 18 15 12 9 6"/></svg>')
        if (!hasChildren) $tog.addClass('leaf')
        $row.append($tog)

        /* depth badge */
        var badgeLabel = isRoot ? 'Root' : 'Sub'
        var badgeClass = isRoot ? 'root' : 'child'
        $row.append($('<span class="tree-badge ' + badgeClass + '">').text(badgeLabel))

        /* name */
        var $name = $('<span class="tree-name">').text(node.name)
        if (!node.is_visible) $name.addClass('hidden-item')
        $row.append($name)

        /* actions */
        var $acts = $('<div class="tree-actions">')

        var $addBtn = $('<button type="button" class="tree-btn">').html(
            '<svg viewBox="0 0 24 24"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg> Child'
        )
        $addBtn.on('click', function (e) {
            e.stopPropagation()
            var n = window.prompt('New child name under "' + node.name + '"')
            if (!n || !n.trim()) return
            $.post(cfg.manageAddUrl, {
                parent_id: node.id,
                name: n.trim(),
                csrfmiddlewaretoken: cfg.csrfToken
            }, function () {
                loadTree()
                initPhotoTypePicker()
            })
        })
        $acts.append($addBtn)

        var $togBtn = $('<button type="button" class="tree-btn">')
        if (node.is_visible) {
            $togBtn.addClass('hide-btn').html(
                '<svg viewBox="0 0 24 24"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/>' +
                '<path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/>' +
                '<line x1="1" y1="1" x2="23" y2="23"/></svg> Hide'
            )
        } else {
            $togBtn.addClass('show-btn').html(
                '<svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>' +
                '<circle cx="12" cy="12" r="3"/></svg> Show'
            )
        }
        $togBtn.on('click', function (e) {
            e.stopPropagation()
            $.post(cfg.manageToggleUrl, {
                item_id: node.id,
                csrfmiddlewaretoken: cfg.csrfToken
            }, function () {
                loadTree()
                initPhotoTypePicker()
            })
        })
        $acts.append($togBtn)

        $row.append($acts)
        $wrap.append($row)

        /* children container */
        if (hasChildren) {
            var $kids = $('<div class="tree-children">').hide()
            $.each(node.children, function (i, child) {
                $kids.append(renderNode(child, depth + 1))
            })
            $wrap.append($kids)

            $tog.on('click', function (e) {
                e.stopPropagation()
                if ($tog.hasClass('open')) {
                    $kids.slideUp(160)
                    $tog.removeClass('open')
                } else {
                    $kids.slideDown(180)
                    $tog.addClass('open')
                }
            })

            if (isRoot) {
                $tog.addClass('open')
                $kids.show()
            }
        }

        return $wrap
    }

    function loadTree() {
        $.get(cfg.manageTreeUrl, function (data) {
            var $tree = $('#photoTypeTree').empty()
            var total = 0
            function countAll(nodes) {
                $.each(nodes, function (i, n) {
                    total++
                    if (n.children) countAll(n.children)
                })
            }
            countAll(data)
            $('#mgmt-count').text(total + ' type' + (total !== 1 ? 's' : ''))

            if (!data.length) {
                $tree.append(
                    '<div class="tree-empty">' +
                    '<svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>' +
                    'No types yet. Use Add Root Type to start.</div>'
                )
                return
            }
            $.each(data, function (i, node) {
                $tree.append(renderNode(node, 0))
            })
        })
    }

    $('#mgmt_add_root').on('click', function () {
        var n = window.prompt('Root type name')
        if (!n || !n.trim()) return
        $.post(cfg.manageAddUrl, {
            name: n.trim(),
            csrfmiddlewaretoken: cfg.csrfToken
        }, function () {
            loadTree()
            initPhotoTypePicker()
        })
    })

    loadTree()

})(jQuery)
