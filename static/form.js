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
