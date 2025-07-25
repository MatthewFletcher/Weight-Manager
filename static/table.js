window.addEventListener('DOMContentLoaded', function () {
  // Move add-weight forms into the correct cell, if using data-ids
  var dataDiv = document.getElementById('entry-ids');
  if (dataDiv) {
    var ids = dataDiv.getAttribute('data-ids').split(',').map(Number);
    ids.forEach(function (id) {
      var cell = document.getElementById('add-weight-cell-' + id);
      var form = document.getElementById('add-weight-form-' + id);
      if (cell && form) cell.appendChild(form);
    });
  }

  // Shift+click for range selection on checkboxes
  let lastChecked = null;
  const checkboxes = Array.from(document.querySelectorAll('.entry-checkbox'));
  checkboxes.forEach((cb) => {
    cb.addEventListener('click', function (event) {
      if (!lastChecked) {
        lastChecked = cb;
        return;
      }
      if (event.shiftKey) {
        let start = checkboxes.indexOf(lastChecked);
        let end = checkboxes.indexOf(cb);
        let [min, max] = [Math.min(start, end), Math.max(start, end)];
        for (let i = min; i <= max; i++) {
          checkboxes[i].checked = lastChecked.checked;
        }
      }
      lastChecked = cb;
    });
  });

  const selectAll = document.getElementById('select-all-checkbox');
  if (selectAll) {
    // Prevent sorting when clicking the select-all checkbox
    selectAll.addEventListener('click', function (event) {
      event.stopPropagation();
    });

    selectAll.addEventListener('change', function () {
      checkboxes.forEach(cb => cb.checked = selectAll.checked);
      selectAll.indeterminate = false;
    });

    // Keep "select all" checkbox in sync when checkboxes are changed individually
    checkboxes.forEach(cb => {
      cb.addEventListener('change', function () {
        if (checkboxes.every(c => c.checked)) {
          selectAll.checked = true;
          selectAll.indeterminate = false;
        } else if (checkboxes.every(c => !c.checked)) {
          selectAll.checked = false;
          selectAll.indeterminate = false;
        } else {
          selectAll.checked = false;
          selectAll.indeterminate = true;
        }
      });
    });
  }

});


document.addEventListener('DOMContentLoaded', function () {
    // Initialize table sorting
    if (window.Tablesort) {
        new Tablesort(document.getElementById('entries-table'));
    }

    // Move Add Weight forms into the right table cells
    if (window.addWeightEntryMap) {
        Object.entries(window.addWeightEntryMap).forEach(([hash, formId]) => {
            var cell = document.getElementById('add-weight-cell-' + hash);
            var form = document.getElementById(formId);
            if (cell && form) cell.appendChild(form);
        });
    }
});

// In-place editing for table cells
document.addEventListener("DOMContentLoaded", function () {
    // Editable text/date fields
    document.querySelectorAll('.editable').forEach(function (cell) {
        cell.ondblclick = function () {
            if (cell.querySelector('input')) return;
            let oldValue = cell.innerText === "N/A" ? "" : cell.innerText;
            let field = cell.dataset.field;
            let hash = cell.dataset.hash;
            let inputType = field === "admission_date" ? "date" : "text";
            let input = document.createElement("input");
            input.type = inputType;
            input.value = oldValue;
            if (inputType === "date" && oldValue && !/^\d{4}-\d{2}-\d{2}$/.test(oldValue)) {
                let d = new Date(oldValue);
                input.value = d.toISOString().split('T')[0];
            }
            cell.innerHTML = "";
            cell.appendChild(input);
            input.focus();

            input.onkeydown = function (e) {
                if (e.key === "Enter") input.blur();
                if (e.key === "Escape") { cell.innerHTML = oldValue || "N/A"; }
            };
            input.onblur = function () {
                let newValue = input.value.trim();
                if (newValue === "") newValue = field === "room" ? "" : oldValue;
                fetch("/update_field", {
                    method: "POST",
                    body: new URLSearchParams({
                        hash,
                        field,
                        value: newValue
                    })
                })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            cell.innerText = (field === "room" && !newValue) ? "N/A" : newValue;
                        } else {
                            cell.innerText = oldValue || "N/A";
                            alert("Update failed: " + (data.error || "unknown error"));
                        }
                    })
                    .catch(() => {
                        cell.innerText = oldValue || "N/A";
                        alert("Update failed.");
                    });
            };
        }
    });

    // Editable weights
    document.querySelectorAll('.weight-cell').forEach(function (cell) {
        cell.ondblclick = function () {
            if (cell.querySelector('input')) return;
            let oldValue = cell.dataset.value;
            let hash = cell.dataset.hash;
            let index = cell.dataset.index;
            let input = document.createElement("input");
            input.type = "number";
            input.step = "0.1";
            input.value = oldValue;
            cell.innerHTML = "";
            cell.appendChild(input);
            input.focus();

            input.onkeydown = function (e) {
                if (e.key === "Enter") input.blur();
                if (e.key === "Escape") cell.innerHTML = oldValue;
            };
            input.onblur = function () {
                let newValue = input.value.trim();
                if (newValue === "") {
                    cell.innerHTML = oldValue;
                    return;
                }
                fetch("/update_field", {
                    method: "POST",
                    body: new URLSearchParams({
                        hash,
                        field: "weight",
                        value: newValue,
                        index
                    })
                })
                    .then(r => r.json())
                    .then(data => {
                        if (data.success) {
                            cell.innerText = newValue;
                            cell.dataset.value = newValue;
                        } else {
                            cell.innerText = oldValue;
                            alert("Update failed: " + (data.error || "unknown error"));
                        }
                    })
                    .catch(() => {
                        cell.innerText = oldValue;
                        alert("Update failed.");
                    });
            };
        }
    });
});
