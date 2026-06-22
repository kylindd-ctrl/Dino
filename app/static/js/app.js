// Solar Proposal Platform - App JavaScript
// Global utility functions

function showAlert(message, type = "info") {
  const alertDiv = document.createElement("div");
  alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
  alertDiv.style.zIndex = 9999;
  alertDiv.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;
  document.body.appendChild(alertDiv);
  setTimeout(() => alertDiv.remove(), 5000);
}

function formatNumber(num) {
  if (num == null) return "-";
  return num.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function formatCurrency(num, symbol = "₱") {
  if (num == null) return "-";
  return symbol + " " + formatNumber(num);
}
