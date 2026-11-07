document.addEventListener('DOMContentLoaded', () => {
  const refreshNegative = (name) => {
    const box = document.querySelector(`[data-negative-for="${name}"]`);
    if (!box) return;
    const selected = document.querySelector(`input[name="${name}"]:checked, select[name="${name}"]`);
    box.hidden = !selected || !['nao_conforme', 'nao'].includes(selected.value);
  };
  document.querySelectorAll('.negative-details').forEach((box) => {
    const name = box.dataset.negativeFor;
    document.querySelectorAll(`input[name="${name}"], select[name="${name}"]`).forEach((input) => input.addEventListener('change', () => refreshNegative(name)));
    refreshNegative(name);
  });
  document.querySelectorAll('.ranking-select').forEach((select) => select.addEventListener('change', () => {
    const parent = select.closest('.checklist-question');
    const used = [...parent.querySelectorAll('.ranking-select')].map((item) => item.value).filter(Boolean);
    parent.querySelectorAll('.ranking-select option').forEach((option) => {
      option.disabled = option.value && used.includes(option.value) && option.parentElement.value !== option.value;
    });
  }));

  const peopleNode = document.getElementById('checklist-people-data');
  const people = peopleNode ? JSON.parse(peopleNode.textContent || '[]') : [];
  const normalize = (value) => (value || '').toString().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const labelFor = (person) => person.nome + (person.matricula ? ` — ${person.matricula}` : '');

  document.querySelectorAll('[data-person-picker]').forEach((picker) => {
    const mode = picker.dataset.mode;
    const name = picker.dataset.name;
    const search = picker.querySelector('.person-search');
    const results = picker.querySelector('.person-results');
    const valuesHost = picker.querySelector('[data-person-values]');
    const selectedHost = picker.querySelector('[data-person-selected]');
    const singleValue = picker.querySelector('[data-person-value]');
    const selectedIds = () => mode === 'single'
      ? (singleValue.value ? [singleValue.value] : [])
      : [...valuesHost.querySelectorAll('input')].map((input) => input.value);
    const close = () => { results.hidden = true; results.replaceChildren(); };
    const updateSelected = () => {
      if (!selectedHost) return;
      const ids = selectedIds();
      const labels = ids.map((id) => people.find((person) => String(person.id) === id)).filter(Boolean).map(labelFor);
      selectedHost.textContent = labels.length ? labels.join(', ') : 'Nenhuma pessoa selecionada.';
    };
    const setMultiple = (person, checked) => {
      const selector = `input[value="${CSS.escape(String(person.id))}"]`;
      const existing = valuesHost.querySelector(selector);
      if (checked && !existing) {
        const input = document.createElement('input'); input.type = 'hidden'; input.name = name; input.value = person.id; valuesHost.appendChild(input);
      } else if (!checked && existing) existing.remove();
      updateSelected();
    };
    const render = () => {
      const term = normalize(search.value);
      const found = people.filter((person) => !term || normalize(person.nome).includes(term) || normalize(person.matricula).includes(term)).slice(0, 20);
      results.replaceChildren();
      if (!found.length) {
        const empty = document.createElement('div'); empty.className = 'person-empty'; empty.textContent = 'Nenhum colaborador encontrado.'; results.appendChild(empty);
      }
      const ids = selectedIds();
      found.forEach((person) => {
        const row = document.createElement('label'); row.className = 'person-result';
        if (mode === 'multiple') {
          const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.checked = ids.includes(String(person.id));
          checkbox.addEventListener('change', () => setMultiple(person, checkbox.checked)); row.appendChild(checkbox);
        }
        const text = document.createElement('span'); text.textContent = labelFor(person); row.appendChild(text);
        if (mode === 'single') row.addEventListener('click', () => { singleValue.value = person.id; search.value = labelFor(person); close(); });
        results.appendChild(row);
      });
      results.hidden = false;
    };
    search.addEventListener('input', () => { if (mode === 'single') singleValue.value = ''; render(); });
    search.addEventListener('focus', render);
    document.addEventListener('click', (event) => { if (!picker.contains(event.target)) close(); });
    updateSelected();
  });
});
