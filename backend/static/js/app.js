// --- Controlador Javascript Panel de Administración ---

document.addEventListener("DOMContentLoaded", () => {
    // --- Estado de la Aplicación ---
    let state = {
        activeTab: "rates-tab",
        rates: [],
        apiKeys: [],
        logs: []
    };

    // --- Selectores DOM ---
    const navItems = document.querySelectorAll(".nav-item");
    const tabPanes = document.querySelectorAll(".tab-pane");
    const tabTitle = document.getElementById("tabTitle");
    const tabSubtitle = document.getElementById("tabSubtitle");

    // Botones de acción generales
    const btnScrapeTrigger = document.getElementById("btnScrapeTrigger");
    const btnOpenCreateModal = document.getElementById("btnOpenCreateModal");
    const btnLogoutBtn = document.getElementById("btnLogoutBtn");

    // Tablas bodies
    const ratesTableBody = document.getElementById("ratesTableBody");
    const apiKeysTableBody = document.getElementById("apiKeysTableBody");
    const logsTableBody = document.getElementById("logsTableBody");

    // Filtros
    const filterMoneda = document.getElementById("filterMoneda");
    const filterTipo = document.getElementById("filterTipo");
    const filterFecha = document.getElementById("filterFecha");
    const btnResetFilters = document.getElementById("btnResetFilters");

    // Modal Cotizaciones
    const rateModal = document.getElementById("rateModal");
    const rateForm = document.getElementById("rateForm");
    const modalTitle = document.getElementById("modalTitle");
    const btnCloseRateModal = document.getElementById("btnCloseRateModal");
    const btnCancelRateModal = document.getElementById("btnCancelRateModal");
    const rateId = document.getElementById("rateId");
    const rateMoneda = document.getElementById("rateMoneda");
    const rateTipo = document.getElementById("rateTipo");
    const rateFechaRegistro = document.getElementById("rateFechaRegistro");
    const rateFechaOficial = document.getElementById("rateFechaOficial");
    const rateHora = document.getElementById("rateHora");
    const rateCompra = document.getElementById("rateCompra");
    const rateVenta = document.getElementById("rateVenta");

    // Modal Revelación de Key
    const keyRevealModal = document.getElementById("keyRevealModal");
    const revealedApiKey = document.getElementById("revealedApiKey");
    const revealedClientName = document.getElementById("revealedClientName");
    const revealedPrefix = document.getElementById("revealedPrefix");
    const btnCopyKey = document.getElementById("btnCopyKey");
    const btnConfirmKeyReveal = document.getElementById("btnConfirmKeyReveal");

    // Formularios
    const apiKeyForm = document.getElementById("apiKeyForm");
    const clientName = document.getElementById("clientName");
    const clientEmail = document.getElementById("clientEmail");
    const btnRefreshLogs = document.getElementById("btnRefreshLogs");

    // --- Notificaciones Toast ---
    function showToast(message, type = "info") {
        const container = document.getElementById("toastContainer");
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;

        let icon = "fa-circle-info";
        if (type === "success") icon = "fa-circle-check";
        if (type === "error") icon = "fa-circle-exclamation";

        toast.innerHTML = `
            <i class="fa-solid ${icon}"></i>
            <span>${message}</span>
        `;

        container.appendChild(toast);

        // Remover después de 3.5 segundos
        setTimeout(() => {
            toast.style.animation = "toastSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse forwards";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // --- Cliente HTTP con manejo automático de 401 ---
    async function apiFetch(url, options = {}) {
        try {
            const response = await fetch(url, options);
            if (response.status === 401) {
                showToast("Sesión expirada o no válida. Redirigiendo...", "error");
                setTimeout(() => {
                    window.location.href = "/login";
                }, 1500);
                throw new Error("No autorizado");
            }
            return response;
        } catch (error) {
            console.error(`Error en petición a ${url}:`, error);
            throw error;
        }
    }

    // --- Navegación entre Solapas ---
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetTab = item.getAttribute("data-tab");

            navItems.forEach(nav => nav.classList.remove("active"));
            item.classList.add("active");

            tabPanes.forEach(pane => {
                if (pane.id === targetTab) {
                    pane.classList.remove("hidden");
                    pane.classList.add("active");
                } else {
                    pane.classList.add("hidden");
                    pane.classList.remove("active");
                }
            });

            state.activeTab = targetTab;
            updateHeader(targetTab);
            loadTabData(targetTab);
        });
    });

    function updateHeader(tabId) {
        if (tabId === "rates-tab") {
            tabTitle.textContent = "Monitoreo de Cotizaciones";
            tabSubtitle.textContent = "Historial y gestión de valores de compra y venta oficial del BNA.";
            btnOpenCreateModal.classList.remove("hidden");
            btnScrapeTrigger.classList.remove("hidden");
        } else if (tabId === "clients-tab") {
            tabTitle.textContent = "API Keys Clientes";
            tabSubtitle.textContent = "Administra las credenciales de los servicios que consumen esta API.";
            btnOpenCreateModal.classList.add("hidden");
            btnScrapeTrigger.classList.add("hidden");
        } else if (tabId === "logs-tab") {
            tabTitle.textContent = "Logs de Auditoría";
            tabSubtitle.textContent = "Trazabilidad completa de las llamadas hechas a los endpoints de la API.";
            btnOpenCreateModal.classList.add("hidden");
            btnScrapeTrigger.classList.add("hidden");
        }
    }

    function loadTabData(tabId) {
        if (tabId === "rates-tab") fetchRates();
        else if (tabId === "clients-tab") fetchApiKeys();
        else if (tabId === "logs-tab") fetchLogs();
    }

    // --- Lógica de Cotizaciones (Tab 1) ---

    async function fetchRates() {
        ratesTableBody.innerHTML = `
            <tr>
                <td colspan="9" class="td-loading">
                    <div class="spinner spinner-accent"></div>
                    <span>Cargando cotizaciones...</span>
                </td>
            </tr>
        `;
        try {
            const res = await apiFetch("/api/admin/cotizaciones");
            if (res.ok) {
                state.rates = await res.json();
                renderRates();
            } else {
                showToast("No se pudieron cargar las cotizaciones.", "error");
            }
        } catch (e) {
            ratesTableBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Error de conexión.</td></tr>`;
        }
    }

    function renderRates() {
        const monedaVal = filterMoneda.value;
        const tipoVal = filterTipo.value;
        const fechaVal = filterFecha.value;

        // Filtrado local instantáneo
        const filteredRates = state.rates.filter(rate => {
            if (monedaVal && rate.moneda !== monedaVal) return false;
            if (tipoVal && rate.tipo !== tipoVal) return false;
            if (fechaVal && rate.fecha_registro !== fechaVal) return false;
            return true;
        });

        if (filteredRates.length === 0) {
            ratesTableBody.innerHTML = `
                <tr>
                    <td colspan="9" class="text-center text-dimmed">No se encontraron cotizaciones cargadas con estos filtros.</td>
                </tr>
            `;
            return;
        }

        ratesTableBody.innerHTML = filteredRates.map(rate => {
            const badgeMoneda = rate.moneda === "USD" ? "badge-usd" : "badge-eur";
            const badgeTipo = rate.tipo === "billete" ? "badge-billete" : "badge-divisa";
            const badgeOrigen = rate.origen === "scraped" ? "badge-scraped" : "badge-manual";

            // Formatear fechas para mejor visualización
            const fRegistro = formatDate(rate.fecha_registro);
            const fOficial = formatDate(rate.fecha_oficial_bna);

            return `
                <tr data-id="${rate.id}">
                    <td><strong>${fRegistro}</strong></td>
                    <td>${fOficial}</td>
                    <td><i class="fa-regular fa-clock"></i> ${rate.hora_actualizacion}</td>
                    <td><span class="badge ${badgeMoneda}">${rate.moneda}</span></td>
                    <td><span class="badge ${badgeTipo}">${rate.tipo}</span></td>
                    <td><strong>$ ${parseFloat(rate.compra).toFixed(2)}</strong></td>
                    <td><strong>$ ${parseFloat(rate.venta).toFixed(2)}</strong></td>
                    <td><span class="badge ${badgeOrigen}">${rate.origen}</span></td>
                    <td class="table-actions">
                        <button class="btn-table btn-edit" onclick="window.editRate('${rate.id}')" title="Editar">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button class="btn-table btn-delete" onclick="window.deleteRate('${rate.id}')" title="Eliminar">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // Helper de formateo de fechas YYYY-MM-DD -> DD/MM/YYYY
    function formatDate(dateStr) {
        if (!dateStr) return "-";
        const parts = dateStr.split('-');
        if (parts.length === 3) {
            return `${parts[2]}/${parts[1]}/${parts[0]}`;
        }
        return dateStr;
    }

    // Aplicar filtros en tiempo real
    filterMoneda.addEventListener("change", renderRates);
    filterTipo.addEventListener("change", renderRates);
    filterFecha.addEventListener("change", renderRates);

    btnResetFilters.addEventListener("click", () => {
        filterMoneda.value = "";
        filterTipo.value = "";
        filterFecha.value = "";
        renderRates();
        showToast("Filtros limpiados.", "info");
    });

    // --- Modal CRUD Cotizaciones ---

    // Configurar fechas de hoy por defecto al abrir modal
    btnOpenCreateModal.addEventListener("click", () => {
        rateId.value = "";
        rateForm.reset();
        modalTitle.textContent = "Cargar Cotización Manual";

        const hoy = new Date().toISOString().split('T')[0];
        rateFechaRegistro.value = hoy;
        rateFechaOficial.value = hoy;
        rateHora.value = new Date().toLocaleTimeString("es-AR", {hour: '2-digit', minute:'2-digit'});

        rateFechaRegistro.disabled = false; // Permitir setear baches en carga manual
        rateMoneda.disabled = false;
        rateTipo.disabled = false;

        rateModal.classList.remove("hidden");
    });

    function closeModal() {
        rateModal.classList.add("hidden");
    }

    btnCloseRateModal.addEventListener("click", closeModal);
    btnCancelRateModal.addEventListener("click", closeModal);

    // Guardar / Editar Cotización
    rateForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const payload = {
            fecha_registro: rateFechaRegistro.value,
            fecha_oficial_bna: rateFechaOficial.value,
            hora_actualizacion: rateHora.value,
            moneda: rateMoneda.value,
            tipo: rateTipo.value,
            compra: parseFloat(rateCompra.value),
            venta: parseFloat(rateVenta.value)
        };

        const id = rateId.value;
        const isEdit = id !== "";
        const url = isEdit ? `/api/admin/cotizaciones/${id}` : "/api/admin/cotizaciones";
        const method = isEdit ? "PUT" : "POST";

        try {
            const res = await apiFetch(url, {
                method: method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok && data.status === "success") {
                showToast(isEdit ? "Cotización modificada exitosamente." : "Cotización guardada exitosamente.", "success");
                closeModal();
                fetchRates();
            } else {
                showToast(data.detail || "Error al guardar la cotización.", "error");
            }
        } catch (error) {
            showToast("Error de comunicación.", "error");
        }
    });

    // Exponer funciones al scope global para que los botones de fila funcionen
    window.editRate = function(id) {
        const rate = state.rates.find(r => r.id === id);
        if (!rate) return;

        rateId.value = rate.id;
        rateMoneda.value = rate.moneda;
        rateTipo.value = rate.tipo;
        rateFechaRegistro.value = rate.fecha_registro;
        rateFechaOficial.value = rate.fecha_oficial_bna;
        rateHora.value = rate.hora_actualizacion;
        rateCompra.value = rate.compra;
        rateVenta.value = rate.venta;

        // Desactivar campos de llave única en edición para evitar romper la restricción UNIQUE
        rateFechaRegistro.disabled = true;
        rateMoneda.disabled = true;
        rateTipo.disabled = true;

        modalTitle.textContent = "Editar Cotización Manual";
        rateModal.classList.remove("hidden");
    };

    window.deleteRate = async function(id) {
        if (!confirm("¿Está seguro de que desea eliminar esta cotización permanentemente?")) return;

        try {
            const res = await apiFetch(`/api/admin/cotizaciones/${id}`, { method: "DELETE" });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                showToast("Cotización eliminada correctamente.", "success");
                fetchRates();
            } else {
                showToast(data.detail || "No se pudo eliminar la cotización.", "error");
            }
        } catch (error) {
            showToast("Error de comunicación.", "error");
        }
    };

    // --- Disparador del Scraper (BNA Ahora) ---
    btnScrapeTrigger.addEventListener("click", async () => {
        btnScrapeTrigger.disabled = true;
        btnScrapeTrigger.querySelector("i").classList.add("fa-spin");

        try {
            const res = await apiFetch("/api/admin/scrape/trigger", { method: "POST" });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                console.group("Scraper trigger result");
                console.log("Scraper stdout:", data.stdout);
                console.log("Scraper stderr:", data.stderr);
                console.groupEnd();

                showToast("Scraper ejecutado y completado. Actualizando datos...", "success");

                await fetchRates();
                btnScrapeTrigger.disabled = false;
                btnScrapeTrigger.querySelector("i").classList.remove("fa-spin");
            } else {
                showToast(data.detail || "Error al disparar el scraper.", "error");
                btnScrapeTrigger.disabled = false;
                btnScrapeTrigger.querySelector("i").classList.remove("fa-spin");
            }
        } catch (error) {
            showToast("Error de conexión.", "error");
            btnScrapeTrigger.disabled = false;
            btnScrapeTrigger.querySelector("i").classList.remove("fa-spin");
        }
    });

    // --- Lógica de API Keys Clientes (Tab 2) ---

    async function fetchApiKeys() {
        apiKeysTableBody.innerHTML = `<tr><td colspan="6" class="td-loading">Cargando API Keys...</td></tr>`;
        try {
            const res = await apiFetch("/api/admin/api-keys");
            if (res.ok) {
                state.apiKeys = await res.json();
                renderApiKeys();
            } else {
                showToast("Error al obtener API Keys.", "error");
            }
        } catch (e) {
            apiKeysTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error de conexión.</td></tr>`;
        }
    }

    function renderApiKeys() {
        if (state.apiKeys.length === 0) {
            apiKeysTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-dimmed">No hay clientes ni API Keys registradas.</td></tr>`;
            return;
        }

        apiKeysTableBody.innerHTML = state.apiKeys.map(key => {
            const badgeStatus = key.activo ? "badge-active" : "badge-inactive";
            const textStatus = key.activo ? "Activo" : "Revocado";
            const fechaCreacion = new Date(key.created_at).toLocaleDateString("es-AR") + " " + new Date(key.created_at).toLocaleTimeString("es-AR", {hour:'2-digit', minute:'2-digit'});

            // Botón deshabilitado si ya está revocado
            const actionBtn = key.activo
                ? `<button class="btn-danger" onclick="window.revokeKey('${key.id}')" title="Revocar Clave">Revocar</button>`
                : `<span class="text-dimmed"><i class="fa-solid fa-ban"></i> Sin acceso</span>`;

            return `
                <tr>
                    <td><strong>${key.cliente_nombre}</strong></td>
                    <td>${key.cliente_email}</td>
                    <td><code>${key.api_key_prefix}</code></td>
                    <td><span class="badge ${badgeStatus}">${textStatus}</span></td>
                    <td>${fechaCreacion}</td>
                    <td class="table-actions">${actionBtn}</td>
                </tr>
            `;
        }).join('');
    }

    // Registrar nuevo cliente
    apiKeyForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const payload = {
            cliente_nombre: clientName.value,
            cliente_email: clientEmail.value
        };

        try {
            const res = await apiFetch("/api/admin/api-keys", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            if (res.ok && data.status === "success") {
                showToast("API Key generada con éxito.", "success");
                apiKeyForm.reset();

                // Mostrar modal de revelación segura de clave única
                revealedApiKey.textContent = data.api_key_completa;
                revealedClientName.textContent = data.cliente_nombre;
                revealedPrefix.textContent = data.prefix;
                keyRevealModal.classList.remove("hidden");

                fetchApiKeys();
            } else {
                showToast(data.detail || "Error al crear la API Key.", "error");
            }
        } catch (e) {
            showToast("Error de conexión.", "error");
        }
    });

    // Copiar API Key
    btnCopyKey.addEventListener("click", () => {
        navigator.clipboard.writeText(revealedApiKey.textContent);
        showToast("¡API Key copiada al portapapeles!", "success");
        btnCopyKey.innerHTML = `<i class="fa-solid fa-check text-success"></i>`;
        setTimeout(() => {
            btnCopyKey.innerHTML = `<i class="fa-regular fa-copy"></i>`;
        }, 2000);
    });

    btnConfirmKeyReveal.addEventListener("click", () => {
        keyRevealModal.classList.add("hidden");
    });

    // Revocar API Key
    window.revokeKey = async function(id) {
        if (!confirm("¿Está seguro de que desea revocar el acceso a este cliente? Esta acción no se puede deshacer y bloqueará las consultas inmediatamente.")) return;

        try {
            const res = await apiFetch(`/api/admin/api-keys/${id}`, { method: "DELETE" });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                showToast("Acceso revocado correctamente.", "success");
                fetchApiKeys();
            } else {
                showToast(data.detail || "No se pudo revocar la API Key.", "error");
            }
        } catch (e) {
            showToast("Error de conexión.", "error");
        }
    };

    // --- Lógica de Logs de Auditoría (Tab 3) ---

    async function fetchLogs() {
        logsTableBody.innerHTML = `<tr><td colspan="7" class="td-loading">Cargando logs...</td></tr>`;
        try {
            const res = await apiFetch("/api/admin/logs");
            if (res.ok) {
                state.logs = await res.json();
                renderLogs();
            } else {
                showToast("No se pudieron cargar los logs de auditoría.", "error");
            }
        } catch (e) {
            logsTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error de conexión.</td></tr>`;
        }
    }

    function renderLogs() {
        if (state.logs.length === 0) {
            logsTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-dimmed">No hay registros de llamadas en el historial.</td></tr>`;
            return;
        }

        logsTableBody.innerHTML = state.logs.map(log => {
            // Formatear fecha y hora local
            const dateObj = new Date(log.created_at);
            const fechaFormateada = dateObj.toLocaleDateString("es-AR") + " " + dateObj.toLocaleTimeString("es-AR", {hour:'2-digit', minute:'2-digit', second:'2-digit'});

            // Resolver nombre cliente
            const cliente = log.api_keys ? log.api_keys.cliente_nombre : `<em class="text-danger">Clave Inválida</em>`;
            const email = log.api_keys ? log.api_keys.cliente_email : "-";

            // Color del estado HTTP
            let statusBadge = "badge-scraped"; // verde por defecto
            if (log.status_code >= 400 && log.status_code < 500) statusBadge = "badge-manual"; // naranja
            if (log.status_code >= 500) statusBadge = "badge-inactive"; // rojo

            return `
                <tr>
                    <td><code>${fechaFormateada}</code></td>
                    <td><strong>${cliente}</strong></td>
                    <td>${email}</td>
                    <td><code>${log.metodo}</code></td>
                    <td><code>${log.endpoint}</code></td>
                    <td>${log.ip_address}</td>
                    <td><span class="badge ${statusBadge}">${log.status_code}</span></td>
                </tr>
            `;
        }).join('');
    }

    btnRefreshLogs.addEventListener("click", () => {
        fetchLogs();
        showToast("Registros actualizados.", "info");
    });

    // --- Cierre de Sesión ---
    btnLogoutBtn.addEventListener("click", async () => {
        if (!confirm("¿Desea cerrar su sesión administrativa?")) return;
        try {
            const res = await fetch("/api/admin/logout", { method: "POST" });
            if (res.ok) {
                showToast("Sesión cerrada.", "success");
                setTimeout(() => {
                    window.location.href = "/login";
                }, 1000);
            }
        } catch (e) {
            window.location.href = "/login";
        }
    });

    // --- Inicialización ---
    // Cargar la solapa por defecto al iniciar
    loadTabData("rates-tab");
});
