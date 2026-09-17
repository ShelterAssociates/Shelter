$(document).ready(function () {
  var PREVIEW_DATA_URL = "/mastersheet/accounts/data/";
  // Must match ACCOUNTS_REPORT_COLUMNS in mastersheet/views.py.
  var ACCOUNTS_REPORT_COLUMNS = [
    "Date", "Invoice No", "Name of Vendor", "Donar Name", "Sponsor Project",
    "City", "Slum", "House No", "Phase I", "Phase II", "Phase III",
    "Type of Material", "Quantity", "Rate", "Gross Amount", "Tax Rate",
    "Tax Amount", "Transport Charges", "Unloading Charges", "Amount",
    "Toilet Record In MasterSheet",
  ];

  var previewTable = null;
  var lastRecords = null;

  // City -> Slum narrowing: swap the free-text/popup slum field for a <select>
  // scoped to that city, and back again when city is cleared.
  var SLUMS_URL = "/mastersheet/accounts/slums/";
  var originalSlumFieldHtml = $("#accounts-slum-field").html();

  function buildSlumSelect(slums) {
    var $select = $('<select name="account_slumname" id="id_account_slumname" class="customized-form"></select>');
    $select.append($('<option value="">All slums in this city</option>'));
    slums.forEach(function (slum) {
      $select.append($("<option></option>").attr("value", slum.id).text(slum.name));
    });
    return $select;
  }

  $("#account_cityname").on("change", function () {
    var cityId = $(this).val();
    if (!cityId) {
      $("#accounts-slum-field").html(originalSlumFieldHtml);
      return;
    }
    $.getJSON(SLUMS_URL, { city_id: cityId }, function (response) {
      $("#accounts-slum-field").empty().append(
        $('<label for="id_account_slumname">Slum</label>'),
        $('<div class="accounts-field-input"></div>').append(buildSlumSelect(response.slums))
      );
    });
  });

  function filtersValid() {
    return (
      $("#id_account_slumname").val() !== "" ||
      $("#account_cityname").val() !== ""
    );
  }

  function warnIfInvalid() {
    if (!filtersValid()) {
      alert("Either Slum or City is required");
      return false;
    }
    return true;
  }

  function toRecords(columns, rows) {
    return rows.map(function (row) {
      var record = {};
      columns.forEach(function (col, idx) {
        record[col] = row[idx];
      });
      record["Month"] = record["Date"] ? String(record["Date"]).substring(0, 7) : "";
      return record;
    });
  }

  function renderPreview() {
    $("#accountsPreviewHint").hide();
    $("#accountsPreviewTable").show();

    if (previewTable) {
      previewTable.destroy();
      $("#accountsPreviewTable").empty();
    }
    previewTable = $("#accountsPreviewTable").DataTable({
      serverSide: true,
      processing: true,
      ajax: {
        url: PREVIEW_DATA_URL,
        type: "POST",
        data: function (d) {
          var formData = $("#accounts_filter_form").serializeArray();
          formData.forEach(function (field) {
            d[field.name] = field.value;
          });
          return d;
        },
      },
      columns: ACCOUNTS_REPORT_COLUMNS.map(function (title) {
        return { title: title };
      }),
      scrollX: true,
    });
    // Reuse the site-wide overlay spinner instead of DataTables' own subtle indicator.
    $("#accountsPreviewTable").on("processing.dt", function (e, settings, processing) {
      $(".overlay").toggle(processing);
    });
  }

  function fetchFullDataset(onSuccess) {
    $(".overlay").show();
    $("#accountsPivotHint")
      .show()
      .text("Fetching accounts data - this can take a few seconds for a large city or slum...");
    $.ajax({
      url: PREVIEW_DATA_URL,
      method: "POST",
      data: $("#accounts_filter_form").serialize(),
      dataType: "json",
      success: function (response) {
        $("#accountsPivotHint").text("Loaded " + response.data.length + " rows.");
        onSuccess(response.columns, response.data);
      },
      error: function () {
        $("#accountsPivotHint").text("Could not load accounts data. Please check the filters and try again.");
      },
      complete: function () {
        $(".overlay").hide();
      },
    });
  }

  function renderPivot(records) {
    $("#accountsPivotHint").hide();
    $("#accountsPivotPresets").show();
    $("#accountsPivotContainer").pivotUI(records, {
      rendererName: "Table",
      aggregatorName: "Sum",
      vals: ["Amount"],
    });
  }

  $("#btnAccountsPreview").on("click", function () {
    if (!warnIfInvalid()) return;
    $('#accountsTabs a[href="#accountsPreviewTab"]').tab("show");
    renderPreview();
  });

  $("#btnAccountsPivot").on("click", function () {
    if (!warnIfInvalid()) return;
    $('#accountsTabs a[href="#accountsPivotTab"]').tab("show");
    fetchFullDataset(function (columns, rows) {
      lastRecords = toRecords(columns, rows);
      renderPivot(lastRecords);
    });
  });

  // Quick views: add an entry here + a matching <li> in the dropdown menu.
  var PIVOT_PRESETS = {
    vendorMonth: { rows: ["Name of Vendor"], cols: ["Month"], vals: ["Amount"] },
    slumTransport: { rows: ["Slum"], cols: [], vals: ["Transport Charges"] },
    vendorTotal: { rows: ["Name of Vendor"], cols: [], vals: ["Amount"] },
    donorTotal: { rows: ["Donar Name"], cols: [], vals: ["Amount"] },
    materialTotal: { rows: ["Type of Material"], cols: [], vals: ["Amount"] },
    cityMaterial: { rows: ["City"], cols: ["Type of Material"], vals: ["Gross Amount"] },
  };

  $("#pivotPresetMenu").on("click", "a[data-preset]", function (e) {
    e.preventDefault();
    if (!lastRecords) return;
    var preset = PIVOT_PRESETS[$(this).data("preset")];
    if (!preset) return;
    $("#accountsPivotContainer").pivotUI(
      lastRecords,
      {
        rows: preset.rows,
        cols: preset.cols,
        aggregatorName: "Sum",
        vals: preset.vals,
        rendererName: "Table",
      },
      true
    );
  });

  $("#btnPivotDownload").on("click", function () {
    var table = $("#accountsPivotContainer table.pvtTable")[0];
    if (!table) {
      alert("Build a pivot table first.");
      return;
    }
    var wb = XLSX.utils.table_to_book(table);
    XLSX.writeFile(wb, "pivot_summary.xlsx");
  });

  // Plain button + .submit() (not type="submit") avoids native required-field validation blocking city-only downloads.
  $("#btnAccountsDownload").on("click", function () {
    if (!warnIfInvalid()) return;
    $("#accounts_filter_form")[0].submit();
  });
});
