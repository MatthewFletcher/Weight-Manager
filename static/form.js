// Toggle a form's visibility
function toggleForm(id) {
  var form = document.getElementById('form-' + id);
  if (form.style.display === "none" || form.style.display === "") {
    form.style.display = "inline-block";
  } else {
    form.style.display = "none";
  }
}

// Confirm delete with count
function confirmDelete() {
  const checked = document.querySelectorAll('input[name="delete_ids"]:checked').length;
  if (checked === 0) {
    alert("Please select at least one entry to delete.");
    return false;
  }
  return confirm(`Are you sure you want to delete ${checked} entr${checked > 1 ? 'ies' : 'y'}?`);
}

// Disable save button after click
function onSaveClick(button) {
  button.disabled = true;
  button.form.submit();
}

// Set today's date in a date field
function setupTodayButton(dateFieldId = "admission_date", btnId = "today-btn") {
  const btn = document.getElementById(btnId);
  const dateField = document.getElementById(dateFieldId);
  if (btn && dateField) {
    btn.addEventListener("click", function () {
      const today = new Date();
      const yyyy = today.getFullYear();
      const mm = String(today.getMonth() + 1).padStart(2, '0');
      const dd = String(today.getDate()).padStart(2, '0');
      dateField.value = `${yyyy}-${mm}-${dd}`;
    });
  } else {
    console.log("Could not find Today button or date field");
  }
}

// Editable weight cells (double-click to edit)
function setupWeightCellEditing() {
  document.querySelectorAll('.weight-cell').forEach(function (cell) {
    cell.ondblclick = function () {
      if (cell.querySelector('input')) return; // Already editing

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
}

// -------- Building dropdown helpers --------

// Handles building selection in filter forms
function setupBuildingFilter(formId, selectId, newInputId, paramName) {
  const form = document.getElementById(formId);
  const sel = document.getElementById(selectId);
  const newBox = document.getElementById(newInputId);
  if (!form || !sel || !newBox) return;

  function showNew(show) {
    newBox.style.display = show ? "inline-block" : "none";
    if (show) newBox.focus();
  }

  sel.addEventListener("change", () => {
    if (sel.value === "__new__") {
      showNew(true);
    } else {
      showNew(false);
      form.submit();
    }
  });

  form.addEventListener("submit", () => {
    if (sel.value === "__new__") {
      const v = (newBox.value || "").trim();
      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = paramName;
      hidden.value = v || "Unassigned";
      form.appendChild(hidden);
      sel.disabled = true;
      newBox.name = "";
    }
  });
}

// Handles building selection inside Add Entry form
function setupBuildingCreator(selectId, inputId) {
  const sel = document.getElementById(selectId);
  const input = document.getElementById(inputId);
  if (!sel || !input) return;

  function toggle() {
    const isNew = sel.value === "__new__";
    input.style.display = isNew ? "inline-block" : "none";
    if (isNew) input.focus();
  }

  sel.addEventListener("change", toggle);
  toggle();
}

// -------- Init on DOMContentLoaded --------
document.addEventListener('DOMContentLoaded', function () {
  setupTodayButton();
  setupWeightCellEditing();

  // Attach building dropdown behavior if present
  setupBuildingFilter("building-filter-form", "building-select", "building-new-filter", "building");
  setupBuildingFilter("entries-building-filter-form", "entries-building-select", "entries-building-new-filter", "building");

  setupBuildingCreator("building", "building-new");
});
