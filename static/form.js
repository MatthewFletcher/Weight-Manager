function toggleForm(id) {
  var form = document.getElementById('form-' + id);
  if (form.style.display === "none" || form.style.display === "") {
    form.style.display = "inline-block";
  } else {
    form.style.display = "none";
  }
}

function confirmDelete() {
  const checked = document.querySelectorAll('input[name="delete_ids"]:checked').length;
  if (checked === 0) {
    alert("Please select at least one entry to delete.");
    return false;
  }
  return confirm(`Are you sure you want to delete ${checked} entr${checked > 1 ? 'ies' : 'y'}?`);
}

function onSaveClick(button) {
  // Optionally, add more custom validation or effects here
  button.disabled = true;
  button.form.submit();
}


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

// Call after DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
  setupTodayButton();
});

document.addEventListener("DOMContentLoaded", function () {
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
});
