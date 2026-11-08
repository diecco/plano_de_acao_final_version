(() => {
    const root = document.querySelector('[data-checklist-builder]');
    if (!root) return;

    const hidden = document.getElementById('estrutura_json');
    const host = root.querySelector('[data-sections]');
    const addSection = root.querySelector('[data-add-section]');
    const counter = root.querySelector('[data-builder-count]');
    const types = [
        ['conformity', 'Conforme / Não conforme / Não aplicável'],
        ['yes_no', 'Sim / Não / Não aplicável'],
        ['choice', 'Seleção de uma opção'],
        ['multichoice', 'Múltipla escolha'],
        ['matrix', 'Matriz de avaliação'],
        ['ranking', 'Ordem de prioridade'],
        ['rating', 'Avaliação por nota'],
        ['text', 'Texto curto'], ['textarea', 'Texto longo'],
        ['person', 'Uma pessoa'], ['people', 'Várias pessoas'], ['sector', 'Setor / Área'],
        ['nfc_tag', 'Etiqueta NFC'],
        ['number', 'Número'], ['counter', 'Contador'], ['date', 'Data'], ['time', 'Hora']
    ];
    const layouts = [
        ['header', 'Cabeçalho / grade de campos'],
        ['verification', 'Itens de verificação'],
        ['narrative', 'Texto / conclusão'],
        ['grouped', 'Verificação agrupada'],
        ['repeatable', 'Lista repetível'],
        ['evidence', 'Evidências / galeria']
    ];
    const layoutHelp = {
        header: 'Distribui os campos em uma grade responsiva de três colunas.',
        verification: 'Apresenta conformidades em tabela com resultado e desvio/evidência.',
        narrative: 'Prioriza textos longos, pareceres e conclusões em largura total.',
        grouped: 'Exibe a seção recolhível, adequada para checklists extensos por assunto.',
        repeatable: 'Organiza os campos como colunas de uma lista na qual o usuário adiciona registros.',
        evidence: 'Exibe os campos como cartões de evidência, adequados para registros e referências.'
    };
    const repeatableTypes = new Set(['text', 'textarea', 'number', 'date', 'time', 'choice', 'sector']);
    let uid = 0;
    let sections = parse(hidden.value);

    function parse(raw) {
        try {
            const value = JSON.parse(raw || '[]');
            return Array.isArray(value) ? value : [];
        } catch (_) { return []; }
    }
    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }
    function input(value, max, update, type = 'text') {
        const node = element('input', 'form-control');
        node.type = type; node.value = value ?? '';
        if (max) node.maxLength = max;
        node.addEventListener('input', () => update(type === 'number' && node.value !== '' ? Number(node.value) : node.value));
        return node;
    }
    function textarea(value, update, rows = 2) {
        const node = element('textarea', 'form-control');
        node.rows = rows; node.value = value ?? '';
        node.addEventListener('input', () => update(node.value));
        return node;
    }
    function select(options, value, update) {
        const node = element('select', 'form-select');
        options.forEach(([key, label]) => {
            const option = element('option', '', label); option.value = key; node.append(option);
        });
        node.value = String(value ?? '');
        node.addEventListener('change', () => update(node.value));
        return node;
    }
    function field(label, control) {
        const box = element('div', 'checklist-field');
        const title = element('label', '', label);
        control.id = `checklist-control-${++uid}`; title.htmlFor = control.id;
        box.append(title, control); return box;
    }
    function rule(label, checked, update) {
        const wrapper = element('label', 'checklist-rule');
        const control = element('input'); control.type = 'checkbox'; control.checked = checked;
        control.addEventListener('change', () => update(control.checked));
        wrapper.append(control, document.createTextNode(label)); return wrapper;
    }
    function action(text, label, callback, disabled = false) {
        const button = element('button', 'checklist-editor-action', text);
        button.type = 'button'; button.title = label; button.setAttribute('aria-label', label);
        button.disabled = disabled; button.addEventListener('click', callback); return button;
    }
    function actions(list, index, noun) {
        const box = element('div', 'checklist-editor-actions');
        box.append(
            action('↑', `Mover ${noun} para cima`, () => move(list, index, -1), index === 0),
            action('↓', `Mover ${noun} para baixo`, () => move(list, index, 1), index === list.length - 1),
            action('×', `Remover ${noun}`, () => { list.splice(index, 1); sync(); render(); })
        );
        return box;
    }
    function move(list, index, delta) {
        [list[index], list[index + delta]] = [list[index + delta], list[index]];
        sync(); render();
    }
    function newQuestion() {
        return {text: '', type: 'conformity', required: true, negative_comment: false, negative_evidence: false, negative_action: false, options: []};
    }
    function sync() {
        hidden.value = JSON.stringify(sections);
        const total = sections.reduce((sum, section) => sum + section.questions.length, 0);
        counter.textContent = `${sections.length} de 30 seções · ${total} de 200 itens`;
        addSection.disabled = sections.length >= 30;
    }
    function lines(value) { return (value || []).join('\n'); }
    function setLines(target, key, value) { target[key] = value.split('\n'); sync(); }

    function specialSettings(question) {
        if (['choice', 'multichoice', 'ranking'].includes(question.type)) {
            const control = textarea(lines(question.options), value => setLines(question, 'options', value), 3);
            control.placeholder = 'Uma alternativa por linha';
            const alternatives = field('Alternativas · de 2 a 20', control);
            if (question.type !== 'multichoice') return alternatives;
            const box = element('div', 'checklist-special-settings');
            const maximumDefault = Math.max((question.options || []).length, 1);
            const minimum = input(question.minimum_selections ?? 0, null, value => { question.minimum_selections = Number(value); sync(); }, 'number');
            const maximum = input(question.maximum_selections ?? maximumDefault, null, value => { question.maximum_selections = Number(value); sync(); }, 'number');
            minimum.min = '0'; maximum.min = '1'; maximum.max = String(maximumDefault);
            box.append(alternatives, field('Quantidade mínima', minimum), field('Quantidade máxima', maximum));
            return box;
        }
        if (question.type === 'matrix') {
            const box = element('div', 'checklist-special-settings checklist-matrix');
            const rows = textarea(lines(question.matrix_rows), value => setLines(question, 'matrix_rows', value), 4);
            rows.placeholder = 'Organização\nLimpeza\nSinalização';
            const columns = textarea(lines(question.matrix_columns), value => setLines(question, 'matrix_columns', value), 4);
            columns.placeholder = 'Ruim\nRegular\nBom\nÓtimo';
            box.append(field('Linhas da matriz · até 20', rows), field('Alternativas da escala · de 2 a 10', columns));
            return box;
        }
        if (question.type === 'rating') {
            const box = element('div', 'checklist-special-settings');
            box.append(
                field('Menor nota', select([['0','0'],['1','1']], question.rating_min ?? 1, value => { question.rating_min = Number(value); if (value === '0') question.rating_style = 'numbers'; sync(); render(); })),
                field('Maior nota', select(Array.from({length: 9}, (_, i) => [String(i + 2), String(i + 2)]), question.rating_max ?? 5, value => { question.rating_max = Number(value); sync(); })),
                field('Apresentação', select(question.rating_min === 0 ? [['numbers','Números']] : [['numbers','Números'],['stars','Estrelas']], question.rating_style || 'numbers', value => { question.rating_style = value; sync(); })),
                field('Descrição da menor nota', input(question.rating_low_label || '', 80, value => { question.rating_low_label = value; sync(); })),
                field('Descrição da maior nota', input(question.rating_high_label || '', 80, value => { question.rating_high_label = value; sync(); }))
            );
            return box;
        }
        if (question.type === 'number') {
            const box = element('div', 'checklist-special-settings');
            box.append(
                field('Unidade de medida', input(question.measurement_unit || '', 20, value => { question.measurement_unit = value; sync(); })),
                field('Casas decimais', select([['','Livre'], ...Array.from({length: 11}, (_, i) => [String(i), String(i)])], question.decimal_places ?? '', value => { question.decimal_places = value === '' ? null : Number(value); sync(); }))
            ); return box;
        }
        if (question.type === 'counter') {
            const box = element('div', 'checklist-special-settings');
            [['minimum','Valor mínimo',0],['maximum','Valor máximo',999],['counter_initial','Valor inicial',0]].forEach(([key,label,fallback]) => {
                const control = input(question[key] ?? fallback, null, value => { question[key] = value === '' ? '' : Number(value); sync(); }, 'number');
                control.min = '0'; control.max = '1000000'; box.append(field(label, control));
            });
            box.append(rule('Incluir nos totais', question.counted !== false, value => { question.counted = value; sync(); }));
            return box;
        }
        if (['text', 'textarea'].includes(question.type)) {
            const fallback = question.type === 'text' ? 255 : 3000;
            const box = element('div', 'checklist-special-settings');
            const control = input(question.max_length ?? fallback, null, value => { question.max_length = Number(value); sync(); }, 'number');
            control.min = '1'; control.max = question.type === 'text' ? '1000' : '10000';
            box.append(field('Limite de caracteres', control)); return box;
        }
        if (['date', 'time'].includes(question.type)) {
            const box = element('div', 'checklist-special-settings');
            const htmlType = question.type === 'date' ? 'date' : 'time';
            box.append(
                field('Valor mínimo (opcional)', input(question.minimum_value || '', null, value => { question.minimum_value = value; sync(); }, htmlType)),
                field('Valor máximo (opcional)', input(question.maximum_value || '', null, value => { question.maximum_value = value; sync(); }, htmlType))
            ); return box;
        }
        if (question.type === 'people') {
            const box = element('div', 'checklist-special-settings');
            const maximumDefault = 50;
            const minimum = input(question.minimum_selections ?? 0, null, value => { question.minimum_selections = Number(value); sync(); }, 'number');
            const maximum = input(question.maximum_selections ?? maximumDefault, null, value => { question.maximum_selections = Number(value); sync(); }, 'number');
            minimum.min = '0'; maximum.min = '1'; maximum.max = '200';
            box.append(field('Quantidade mínima', minimum), field('Quantidade máxima', maximum)); return box;
        }
        if (question.type === 'nfc_tag') {
            const box = element('div', 'checklist-special-settings');
            box.append(
                rule('Bloquear os itens e etapas seguintes até validar a etiqueta', question.nfc_unlock_section !== false, value => {
                    question.nfc_unlock_section = value; sync();
                }),
                element('p', 'form-text mb-0', 'O preenchimento será feito exclusivamente pela leitura física da etiqueta NFC. O cadastro administrativo será usado para validar número, status e abrangência.')
            );
            return box;
        }
        return null;
    }

    function render() {
        const opened = Array.from(host.children).map(node => node.open);
        host.replaceChildren();
        sections.forEach((section, sectionIndex) => {
            section.questions = Array.isArray(section.questions) ? section.questions : [];
            const wrapper = element('details', 'checklist-section'); wrapper.open = opened[sectionIndex] !== false;
            const summary = element('summary', 'checklist-section-summary');
            if (section.layout === 'standard') section.layout = 'verification';
            const summaryTitle = element('span', 'checklist-section-summary-title', `${section.title || 'Nova seção'} · ${section.questions.length} item(ns)`);
            const summaryActions = actions(sections, sectionIndex, 'seção');
            summaryActions.classList.add('checklist-section-summary-actions');
            summaryActions.addEventListener('click', event => { event.preventDefault(); event.stopPropagation(); });
            summary.append(summaryTitle, summaryActions);
            const heading = element('div', 'checklist-section-heading');
            const layoutControl = select(layouts, section.layout || 'verification', value => {
                if (value === 'repeatable') {
                    const incompatible = section.questions.filter(question => !repeatableTypes.has(question.type));
                    if (incompatible.length && !window.confirm('A lista repetível aceita campos simples. Converter os itens incompatíveis para texto curto?')) {
                        layoutControl.value = section.layout || 'verification';
                        return;
                    }
                    incompatible.forEach(question => {
                        question.type = 'text';
                        question.negative_comment = false;
                        question.negative_evidence = false;
                        question.negative_action = false;
                    });
                }
                section.layout = value;
                layoutDescription.textContent = layoutHelp[value] || '';
                sync(); render();
            });
            const layoutBox = field('Layout da seção', layoutControl);
            const layoutDescription = element('div', 'form-text', layoutHelp[section.layout || 'verification']);
            layoutBox.append(layoutDescription);
            heading.append(
                field('Nome da seção', input(section.title || '', 120, value => { section.title = value; summaryTitle.textContent = `${value || 'Nova seção'} · ${section.questions.length} item(ns)`; sync(); })),
                layoutBox
            );
            wrapper.append(summary, heading);

            section.questions.forEach((question, questionIndex) => {
                Object.assign(question, {options: Array.isArray(question.options) ? question.options : []});
                const item = element('div', 'checklist-question');
                const row = element('div', 'checklist-question-row');
                const availableTypes = section.layout === 'repeatable'
                    ? types.filter(([value]) => repeatableTypes.has(value))
                    : types;
                row.append(
                    field(`Item ${sectionIndex + 1}.${questionIndex + 1}`, input(question.text || '', 500, value => { question.text = value; sync(); })),
                    field('Tipo de resposta', select(availableTypes, question.type || 'conformity', value => { question.type = value; if (!['conformity','yes_no'].includes(value)) { question.negative_comment = false; question.negative_evidence = false; question.negative_action = false; } sync(); render(); })),
                    actions(section.questions, questionIndex, 'item')
                );
                item.append(row);
                const special = specialSettings(question); if (special) item.append(special);

                const details = element('details', 'checklist-item-settings');
                details.append(element('summary', '', 'Orientação do item'));
                const detailBody = element('div', 'checklist-item-settings-body');
                const help = textarea(question.help || '', value => { question.help = value; sync(); }, 2); help.maxLength = 1000;
                detailBody.append(field('Explicação opcional', help)); details.append(detailBody); item.append(details);

                const rules = element('div', 'checklist-rules');
                rules.append(rule('Resposta obrigatória', question.required === true, value => { question.required = value; sync(); }));
                if (['conformity','yes_no'].includes(question.type)) {
                    rules.append(
                        rule('Exigir descrição do desvio', question.negative_comment === true, value => { question.negative_comment = value; sync(); }),
                        rule('Exigir evidência', question.negative_evidence === true, value => { question.negative_evidence = value; sync(); }),
                        rule('Gerar ação para resposta negativa', question.negative_action === true, value => { question.negative_action = value; sync(); })
                    );
                }
                item.append(rules); wrapper.append(item);
            });

            const addItem = element('button', 'btn btn-outline-secondary btn-sm checklist-add-item', 'Adicionar item');
            addItem.type = 'button';
            addItem.disabled = sections.reduce((sum, section) => sum + section.questions.length, 0) >= 200;
            addItem.addEventListener('click', () => { section.questions.push(newQuestion()); sync(); render(); host.children[sectionIndex].open = true; });
            wrapper.append(addItem); host.append(wrapper);
        });
        sync();
    }

    addSection.addEventListener('click', () => {
        if (sections.length >= 30) return;
        sections.push({title: '', layout: 'verification', questions: [newQuestion()]}); sync(); render();
        host.lastElementChild.open = true;
    });
    render();
})();
