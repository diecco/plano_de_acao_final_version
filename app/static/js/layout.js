(function () {
    "use strict";

    const root = document.documentElement;
    const toggleButton = document.getElementById("toggleSidebar");
    const collapseButton = document.getElementById("collapseSidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const searchInput = document.getElementById("sidebarSearch");
    const focusSearchButton = document.getElementById("focusSidebarSearch");
    const noResults = document.getElementById("sidebarNoResults");
    const desktopBreakpoint = 992;

    function isDesktop() {
        return window.innerWidth >= desktopBreakpoint;
    }

    function persistSidebar() {
        const state = root.classList.contains("sidebar-collapsed")
            ? "collapsed"
            : "expanded";
        localStorage.setItem("trackplan_sidebar", state);
    }

    function closeMobileSidebar() {
        root.classList.remove("sidebar-mobile-open");
    }

    function toggleSidebar() {
        if (isDesktop()) {
            root.classList.toggle("sidebar-collapsed");
            persistSidebar();
            return;
        }

        root.classList.toggle("sidebar-mobile-open");
    }

    function expandSidebarForNavigation(event) {
        if (!isDesktop() || !root.classList.contains("sidebar-collapsed")) {
            return;
        }

        const trigger = event.currentTarget;
        const targetSelector = trigger.getAttribute("data-bs-target");

        root.classList.remove("sidebar-collapsed");
        persistSidebar();

        if (targetSelector) {
            event.preventDefault();
            const target = document.querySelector(targetSelector);
            if (target && window.bootstrap) {
                bootstrap.Collapse.getOrCreateInstance(target).show();
            }
        }
    }

    function normalizeSearch(value) {
        return value
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase()
            .trim();
    }

    function filterMenu() {
        if (!searchInput) return;

        const query = normalizeSearch(searchInput.value);
        const modules = document.querySelectorAll(".sidebar-module");
        let visibleCount = 0;

        modules.forEach(function (module) {
            const searchable = normalizeSearch(
                module.getAttribute("data-search-label") || module.textContent
            );
            const visible = !query || searchable.includes(query);

            module.classList.toggle("d-none", !visible);
            if (visible) visibleCount += 1;

            if (query && visible && window.bootstrap) {
                const submenu = module.querySelector(".sidebar-submenu");
                if (submenu) {
                    bootstrap.Collapse.getOrCreateInstance(
                        submenu,
                        {toggle: false}
                    ).show();
                }
            }
        });

        if (noResults) {
            noResults.classList.toggle("d-none", visibleCount !== 0);
        }
    }

    function prepareFlashMessages() {
        document.querySelectorAll(".flash-messages .alert").forEach(function (alert) {
            window.setTimeout(function () {
                if (alert.isConnected && window.bootstrap) {
                    bootstrap.Alert.getOrCreateInstance(alert).close();
                }
            }, 5000);
        });
    }

    function prepareSystemConfirmations() {
        const modalElement = document.getElementById("modalConfirmacaoSistema");
        if (!modalElement || !window.bootstrap) return;

        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        const title = document.getElementById("modalConfirmacaoSistemaTitulo");
        const context = document.getElementById("modalConfirmacaoSistemaContexto");
        const message = document.getElementById("modalConfirmacaoSistemaMensagem");
        const note = document.getElementById("modalConfirmacaoSistemaObservacao");
        const icon = document.getElementById("modalConfirmacaoSistemaIcone");
        const confirmButton = document.getElementById("modalConfirmacaoSistemaConfirmar");
        let pendingResolution = null;

        function extractLegacyMessage(source) {
            if (!source) return "";
            const match = source.match(/confirm\s*\(\s*(['"])(.*?)\1\s*\)/);
            return match ? match[2] : "";
        }

        function migrateLegacyConfirmations() {
            document.querySelectorAll("form[onsubmit]").forEach(function (form) {
                const legacyMessage = extractLegacyMessage(form.getAttribute("onsubmit"));
                if (!legacyMessage) return;
                form.removeAttribute("onsubmit");
                form.dataset.confirmacao = legacyMessage;
            });

            document.querySelectorAll("a[onclick], button[onclick], input[onclick]")
                .forEach(function (trigger) {
                    const legacyMessage = extractLegacyMessage(trigger.getAttribute("onclick"));
                    if (!legacyMessage) return;
                    trigger.removeAttribute("onclick");
                    trigger.dataset.confirmacao = legacyMessage;
                });
        }

        function inferredOptions(trigger, confirmationMessage) {
            const normalized = (confirmationMessage || "").toLowerCase();
            let inferredTitle = "Confirmar ação";
            let buttonText = "Confirmar";
            let iconClass = "bi-exclamation-triangle";

            if (normalized.includes("excluir") || normalized.includes("remo")) {
                inferredTitle = "Confirmar exclusão";
                buttonText = normalized.includes("remo") ? "Remover" : "Excluir";
                iconClass = "bi-trash";
            } else if (normalized.includes("inativar") || normalized.includes("desativar")) {
                inferredTitle = "Confirmar inativação";
                buttonText = "Inativar";
                iconClass = "bi-pause-circle";
            } else if (normalized.includes("ativar")) {
                inferredTitle = "Confirmar ativação";
                buttonText = "Ativar";
                iconClass = "bi-check-circle";
            } else if (normalized.includes("cancel")) {
                inferredTitle = "Confirmar cancelamento";
                iconClass = "bi-x-circle";
            } else if (normalized.includes("enviar")) {
                inferredTitle = "Confirmar envio";
                buttonText = "Enviar";
                iconClass = "bi-send";
            }

            return {
                titulo: trigger?.dataset.confirmacaoTitulo || inferredTitle,
                mensagem: confirmationMessage || "Deseja continuar com esta ação?",
                contexto: trigger?.dataset.confirmacaoContexto || "",
                observacao: trigger?.dataset.confirmacaoObservacao || "",
                botao: trigger?.dataset.confirmacaoBotao || buttonText,
                icone: trigger?.dataset.confirmacaoIcone || iconClass,
            };
        }

        function setOptionalText(element, value) {
            element.textContent = value || "";
            element.classList.toggle("d-none", !value);
        }

        window.confirmarAcaoSistema = function (options) {
            const settings = Object.assign({
                titulo: "Confirmar ação",
                mensagem: "Deseja continuar com esta ação?",
                contexto: "",
                observacao: "",
                botao: "Confirmar",
                icone: "bi-exclamation-triangle",
            }, options || {});

            title.textContent = settings.titulo;
            message.textContent = settings.mensagem;
            setOptionalText(context, settings.contexto);
            setOptionalText(note, settings.observacao);
            confirmButton.textContent = settings.botao;
            icon.innerHTML = `<i class="bi ${settings.icone}"></i>`;

            if (pendingResolution) pendingResolution(false);
            return new Promise(function (resolve) {
                pendingResolution = resolve;
                modal.show();
            });
        };

        confirmButton.addEventListener("click", function () {
            const resolve = pendingResolution;
            pendingResolution = null;
            modal.hide();
            if (resolve) resolve(true);
        });

        modalElement.addEventListener("hidden.bs.modal", function () {
            const resolve = pendingResolution;
            pendingResolution = null;
            if (resolve) resolve(false);
        });

        migrateLegacyConfirmations();

        document.addEventListener("submit", function (event) {
            const form = event.target.closest("form[data-confirmacao]");
            if (!form) return;
            if (form.dataset.confirmacaoLiberada === "1") {
                delete form.dataset.confirmacaoLiberada;
                return;
            }

            event.preventDefault();
            const options = inferredOptions(form, form.dataset.confirmacao);
            window.confirmarAcaoSistema(options).then(function (confirmed) {
                if (!confirmed) return;
                form.dataset.confirmacaoLiberada = "1";
                if (typeof form.requestSubmit === "function") {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            });
        });

        document.addEventListener("click", function (event) {
            const trigger = event.target.closest(
                "a[data-confirmacao], button[data-confirmacao], input[data-confirmacao]"
            );
            if (!trigger) return;
            if (trigger.dataset.confirmacaoLiberada === "1") {
                delete trigger.dataset.confirmacaoLiberada;
                return;
            }

            event.preventDefault();
            const options = inferredOptions(trigger, trigger.dataset.confirmacao);
            window.confirmarAcaoSistema(options).then(function (confirmed) {
                if (!confirmed) return;
                if (trigger.tagName === "A" && trigger.href) {
                    window.location.assign(trigger.href);
                    return;
                }
                trigger.dataset.confirmacaoLiberada = "1";
                trigger.click();
            });
        });
    }

    if (toggleButton) {
        toggleButton.addEventListener("click", toggleSidebar);
    }

    if (collapseButton) {
        collapseButton.addEventListener("click", function () {
            if (isDesktop()) {
                root.classList.add("sidebar-collapsed");
                persistSidebar();
            } else {
                closeMobileSidebar();
            }
        });
    }

    if (overlay) {
        overlay.addEventListener("click", closeMobileSidebar);
    }

    document.querySelectorAll(".sidebar-module-toggle[data-bs-toggle='collapse']")
        .forEach(function (trigger) {
            trigger.addEventListener("click", expandSidebarForNavigation);
        });

    document.querySelectorAll(".sidebar-link, .sidebar-direct-link")
        .forEach(function (link) {
            link.addEventListener("click", function () {
                if (!isDesktop()) closeMobileSidebar();
            });
        });

    if (searchInput) {
        searchInput.addEventListener("input", filterMenu);
    }

    if (focusSearchButton) {
        focusSearchButton.addEventListener("click", function () {
            if (isDesktop() && root.classList.contains("sidebar-collapsed")) {
                root.classList.remove("sidebar-collapsed");
                persistSidebar();
            } else if (!isDesktop()) {
                root.classList.add("sidebar-mobile-open");
            }

            window.setTimeout(function () {
                if (searchInput) searchInput.focus();
            }, 180);
        });
    }

    window.addEventListener("resize", function () {
        if (isDesktop()) closeMobileSidebar();
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") closeMobileSidebar();
    });

    prepareFlashMessages();
    prepareSystemConfirmations();
})();
