document.addEventListener('DOMContentLoaded', () => {
  const refreshNegative = (name) => {
    const box = document.querySelector(`[data-negative-for="${name}"]`);
    if (!box) return;
    const selected = document.querySelector(`input[name="${name}"]:checked`);
    box.hidden = !selected || !['nao_conforme', 'nao'].includes(selected.value);
  };
  document.querySelectorAll('.negative-details').forEach((box) => {
    const name = box.dataset.negativeFor;
    document.querySelectorAll(`input[name="${name}"]`).forEach((input) => input.addEventListener('change', () => refreshNegative(name)));
    refreshNegative(name);
  });
  document.querySelectorAll('.ranking-select').forEach((select) => select.addEventListener('change', () => {
    const parent = select.closest('.checklist-question');
    const used = [...parent.querySelectorAll('.ranking-select')].map((item) => item.value).filter(Boolean);
    parent.querySelectorAll('.ranking-select option').forEach((option) => {
      option.disabled = option.value && used.includes(option.value) && option.parentElement.value !== option.value;
    });
  }));
});
