/**
 * Kalastree Pulse — daily reflection interactions.
 * Slider gives live emoji/color/label feedback as it's dragged.
 * Server-side validation is authoritative; this only adds live feedback.
 */

const RATING_STEPS = [
  { max: 2, emoji: "😞", label: "Barely moved", color: "#ef4444" },
  { max: 4, emoji: "😕", label: "Slow going", color: "#f97316" },
  { max: 6, emoji: "😐", label: "Steady", color: "#eab308" },
  { max: 8, emoji: "🙂", label: "Good progress", color: "#22c55e" },
  { max: 10, emoji: "🚀", label: "Huge leap forward", color: "#16a34a" },
];

function stepFor(value) {
  return RATING_STEPS.find((step) => value <= step.max) || RATING_STEPS[RATING_STEPS.length - 1];
}

function updateSlider(slider) {
  const value = Number(slider.value);
  const step = stepFor(value);
  const percent = ((value - 1) / 9) * 100;

  slider.style.setProperty("--fill-percent", `${percent}%`);
  slider.style.setProperty("--fill-color", step.color);

  const emoji = document.getElementById("rating-emoji");
  const label = document.getElementById("rating-label");

  if (emoji) {
    emoji.textContent = step.emoji;
    emoji.classList.remove("bump");
    void emoji.offsetWidth; // restart the animation on repeated drags
    emoji.classList.add("bump");
  }
  if (label) label.textContent = step.label;
}

document.addEventListener("DOMContentLoaded", () => {
  const slider = document.getElementById("rating");
  if (slider) {
    updateSlider(slider);
    slider.addEventListener("input", () => updateSlider(slider));
  }

  const form = document.querySelector(".reflect");
  const submitBtn = form?.querySelector(".reflect__submit");
  const overlay = document.getElementById("loading-overlay");

  form?.addEventListener("submit", () => {
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting…";
    }
    overlay?.classList.add("is-visible");
  });
});
