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

window.addEventListener('DOMContentLoaded', function() {
  var dataDiv = document.getElementById('entry-ids');
  if (dataDiv) {
    var ids = dataDiv.getAttribute('data-ids').split(',').map(Number);
    ids.forEach(function(id) {
      var cell = document.getElementById('add-weight-cell-' + id);
      var form = document.getElementById('add-weight-form-' + id);
      if (cell && form) cell.appendChild(form);
    });
  }
});

function showHelp(page) {
  const modal = document.getElementById('help-modal');
  const content = document.getElementById('help-content');
  content.innerHTML = "Loading...";
  modal.style.display = "block";
  fetch('/help/' + page)
    .then(res => res.json())
    .then(data => {
      if (data.html) {
        content.innerHTML = data.html;
      } else {
        content.innerHTML = "Help not found.";
      }
    }).catch(() => {
      content.innerHTML = "Error loading help content.";
    });
}

window.addEventListener('DOMContentLoaded', function() {
  // You may want to set this differently per page:
  let helpPage = "entries"; // or "entry_form" for the form page
  if (document.getElementById('help-btn')) {
    if (window.location.pathname.includes("entries")) {
      helpPage = "entries";
    } else {
      helpPage = "entry_form";
    }
    document.getElementById('help-btn').onclick = () => showHelp(helpPage);
  }
  if (document.getElementById('help-close')) {
    document.getElementById('help-close').onclick = function () {
      document.getElementById('help-modal').style.display = "none";
    };
  }
  // Close modal if click outside content
  window.onclick = function(event) {
    const modal = document.getElementById('help-modal');
    if (event.target == modal) {
      modal.style.display = "none";
    }
  }
});
