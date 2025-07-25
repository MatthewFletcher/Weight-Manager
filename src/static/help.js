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
  // Set help page name based on current route
  let helpPage = "entries";
  if (window.location.pathname.includes("entries")) {
    helpPage = "entries";
  } else {
    helpPage = "entry_form";
  }
  // Open help modal
  const helpBtn = document.getElementById('help-btn');
  if (helpBtn) {
    helpBtn.onclick = () => showHelp(helpPage);
  }
  // Close help modal
  const helpClose = document.getElementById('help-close');
  if (helpClose) {
    helpClose.onclick = function () {
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
