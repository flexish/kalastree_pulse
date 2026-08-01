/**
 * Kalastree Pulse — login page interactions.
 * Server-side validation is authoritative; this only adds submit feedback.
 */

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".auth__card");
  const submitBtn = form?.querySelector(".auth__submit");

  form?.addEventListener("submit", () => {
    if (!submitBtn) return;
    submitBtn.disabled = true;
    submitBtn.textContent = submitBtn.dataset.loadingText || "Please wait…";
  });
});
