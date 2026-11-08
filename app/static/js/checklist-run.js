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
  const actionPeopleNode = document.getElementById('checklist-action-people-data');
  const actionPeople = actionPeopleNode ? JSON.parse(actionPeopleNode.textContent || '[]') : [];
  const normalize = (value) => (value || '').toString().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
  const labelFor = (person) => person.nome + (person.matricula ? ` — ${person.matricula}` : '');

  document.querySelectorAll('[data-person-picker]').forEach((picker) => {
    const availablePeople = picker.dataset.source === 'actions' ? actionPeople : people;
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
      const labels = ids.map((id) => availablePeople.find((person) => String(person.id) === id)).filter(Boolean).map(labelFor);
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
      const found = availablePeople.filter((person) => !term || normalize(person.nome).includes(term) || normalize(person.matricula).includes(term)).slice(0, 20);
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
    if (mode === 'single' && singleValue.value) {
      const selected = availablePeople.find((person) => String(person.id) === singleValue.value);
      if (selected) search.value = labelFor(selected);
    }
  });

  const nfcNode = document.getElementById('checklist-nfc-data');
  const nfcTags = nfcNode ? JSON.parse(nfcNode.textContent || '[]') : [];
  const nfcText = (tag) => `${tag.numero} — ${tag.descricao}`;
  const nfcCandidates = (raw) => {
    const candidates = [String(raw || '').trim()];
    try {
      const url = new URL(candidates[0]);
      ['token', 'nfc', 'tag', 'etiqueta'].forEach((key) => {
        if (url.searchParams.get(key)) candidates.push(url.searchParams.get(key));
      });
      const last = url.pathname.split('/').filter(Boolean).pop();
      if (last) candidates.push(decodeURIComponent(last));
    } catch (_) { /* O conteúdo também pode ser apenas o número ou token. */ }
    return candidates.map((value) => value.trim()).filter(Boolean);
  };
  const decodedNfcRecords = (message) => {
    const decoder = new TextDecoder();
    return [...(message.records || [])].map((record) => {
      try { return decoder.decode(record.data); } catch (_) { return ''; }
    }).filter(Boolean);
  };
  const refreshNfcSection = (section) => {
    const checkpoints = [...section.querySelectorAll('[data-nfc-checkpoint][data-unlock-section="1"]')];
    if (!checkpoints.length) return;
    const unlocked = checkpoints.every((checkpoint) => {
      const value = checkpoint.querySelector('[data-nfc-value]').value;
      const method = checkpoint.querySelector('[data-nfc-method]').value;
      return value && (checkpoint.dataset.physicalRequired !== '1' || method === 'physical');
    });
    section.classList.toggle('checklist-nfc-locked', !unlocked);
    section.querySelectorAll('input, select, textarea, button').forEach((control) => {
      if (!control.closest('[data-nfc-checkpoint]')) control.disabled = !unlocked;
    });
  };

  document.querySelectorAll('[data-nfc-checkpoint]').forEach((checkpoint) => {
    const value = checkpoint.querySelector('[data-nfc-value]');
    const method = checkpoint.querySelector('[data-nfc-method]');
    const channel = checkpoint.querySelector('[data-nfc-channel]');
    const readAt = checkpoint.querySelector('[data-nfc-read-at]');
    const status = checkpoint.querySelector('[data-nfc-status]');
    const usbInput = checkpoint.querySelector('[data-nfc-usb-input]');
    const button = checkpoint.querySelector('[data-nfc-read]');
    const section = checkpoint.closest('section');
    const setTag = (tag, readChannel) => {
      value.value = tag.id;
      method.value = 'physical';
      channel.value = readChannel;
      readAt.value = new Date().toISOString();
      usbInput.value = '';
      const channelLabel = readChannel === 'usb' ? 'leitor USB' : 'NFC do celular';
      status.textContent = `${nfcText(tag)} · leitura validada por ${channelLabel}`;
      checkpoint.classList.remove('is-invalid'); checkpoint.classList.add('is-valid');
      refreshNfcSection(section);
    };
    const validateCapture = (raw, readChannel) => {
      const candidates = (Array.isArray(raw) ? raw : [raw]).flatMap(nfcCandidates);
      const tag = nfcTags.find((item) => candidates.includes(String(item.token)) || candidates.includes(String(item.numero)));
      if (!tag) {
        checkpoint.classList.remove('is-valid'); checkpoint.classList.add('is-invalid');
        status.textContent = 'Etiqueta não cadastrada, inativa ou fora da abrangência deste checklist.';
        value.value = ''; method.value = ''; channel.value = ''; readAt.value = '';
        refreshNfcSection(section);
        return false;
      }
      setTag(tag, readChannel); return true;
    };
    usbInput.addEventListener('focus', () => {
      usbInput.value = '';
      status.textContent = 'Aguardando a leitura do dispositivo USB…';
    });
    usbInput.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      validateCapture(usbInput.value.trim(), 'usb');
      if (checkpoint.classList.contains('is-invalid')) usbInput.select();
    });
    button.addEventListener('click', async () => {
      if (!('NDEFReader' in window)) {
        checkpoint.classList.add('is-invalid');
        status.textContent = 'Este navegador não oferece leitura NFC. Use um celular Android com Chrome e conexão HTTPS.';
        return;
      }
      button.disabled = true;
      status.textContent = 'Aproxime o aparelho da etiqueta NFC…';
      try {
        const reader = new NDEFReader();
        await reader.scan();
        reader.addEventListener('reading', (event) => {
          const records = decodedNfcRecords(event.message);
          validateCapture(records, 'web_nfc');
          button.disabled = false;
        }, {once: true});
      } catch (error) {
        checkpoint.classList.add('is-invalid');
        status.textContent = error && error.name === 'NotAllowedError'
          ? 'A leitura NFC não foi autorizada no aparelho.'
          : 'Não foi possível iniciar a leitura NFC.';
        button.disabled = false;
      }
    });
    const selected = nfcTags.find((item) => String(item.id) === value.value);
    if (selected && method.value) {
      const channelLabel = channel.value === 'usb' ? 'leitor USB' : 'NFC do celular';
      status.textContent = `${nfcText(selected)} · leitura validada por ${channelLabel}`;
      checkpoint.classList.add('is-valid');
    }
    refreshNfcSection(section);
  });
});
