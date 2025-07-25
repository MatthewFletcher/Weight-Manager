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
