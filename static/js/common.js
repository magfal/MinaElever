// common.js

// ├── TOM SELECT
//│   └── initTomSelects()
//├── CHECKBOXAR
//│   └── setupSelectAll()
//├── TABELLSORTERING
//│   └── document click delegation
//├── STUDENTER
//│   └── document change delegation
//├── MODALER
//│   ├── hide.bs.modal
//│   └── htmx:afterRequest
//├── TOASTS
//│   ├── Bootstrap toast
//│   ├── auto-dismiss
//│   ├── Alpine toast
//│   └── showToast
//└── INITIERING
//    ├── DOMContentLoaded
//    └── htmx:afterSwa

// ============================================================
// TOM SELECT
// ============================================================
function initTomSelects(root = document) {
    root.querySelectorAll(".tomselect-create")
        .forEach(el => {
            if (el.tomselect) return;
            const tom = new TomSelect(el, {
                create: true,
                createOnBlur: true,
                persist: false
            });
            const button = el
                .closest(".input-group")
                ?.querySelector(".add-tomselect-btn");
            if (button) {
                tom.control_input.addEventListener(
                    "keydown", 
                    (event) => {
                        if (event.key === "Enter") {
                            event.preventDefault();
                            event.stopPropagation();
                            el.dispatchEvent(
                                new Event("change", { 
                                    bubbles: true 
                                })
                            );
                            button.click();
                        }
                    }
                )
            }
        });
}

// ============================================================
// CHECKBOXAR
// ============================================================
function setupSelectAll(selectAllId, checkboxName, tableId) {
    const selectAll = document.getElementById(selectAllId);
    if (!selectAll) return;
    function getVisibleCheckboxes() {
        return [...document.querySelectorAll(`#${tableId} tbody tr`)]
            .filter(row => row.style.display !== "none")
            .map(row =>
                row.querySelector(
                    `input[name="${checkboxName}"]`
                )
            )
            .filter(cb => cb);
    }
    function updateSelectAll() {
        const checkboxes = getVisibleCheckboxes();
        selectAll.checked =
            checkboxes.length > 0 &&
            checkboxes.every(cb => cb.checked);
    }
    // Markera/avmarkera alla synliga
    selectAll.addEventListener("change", function () {
        getVisibleCheckboxes()
            .forEach(cb => {
                cb.checked = selectAll.checked;
            });
        updateSelectAll();
    });
    // Om en elev ändras manuellt
    document
        .querySelectorAll(`input[name="${checkboxName}"]`)
        .forEach(cb => {
            cb.addEventListener(
                "change",
                updateSelectAll
            );
        });
    // Gör funktionen tillgänglig för filtret
    window.updateSelectAll = updateSelectAll;
    // Startläge
    updateSelectAll();
}

// ============================================================
// TABELLSORTERING
// ============================================================
document.addEventListener("click", (event) => {
    const header = event.target.closest(".sortable");
    if (!header) return;
    const table = header.closest("table");
    if (!table) return;
    const tbody = table.tBodies[0];
    if (!tbody) return;
    const rows = Array.from(tbody.rows);
    const column = header.cellIndex;
    // Växla riktning
    const ascending = header.dataset.sort !== "asc";
    header.dataset.sort = ascending ? "asc" : "desc";
    // Återställ övriga rubriker
    table.querySelectorAll(".sortable").forEach(th => {
        if (th !== header) {
            delete th.dataset.sort;
        }
    });
    // Återställ alla ikoner
    table.querySelectorAll(".sortable i").forEach(icon => {
        icon.className = "bi bi-chevron-expand ms-1";
    });
    // Sätt ikon på den klickade kolumnen
    const icon = header.querySelector("i");
    if (icon) {
        icon.className = ascending
            ? "bi bi-caret-down-fill ms-1"
            : "bi bi-caret-up-fill ms-1";
    }
    // Sortera
    rows.sort((a, b) => {
        const aValue = a.cells[column].textContent.trim();
        const bValue = b.cells[column].textContent.trim();
        return ascending
            ? aValue.localeCompare(bValue, "sv")
            : bValue.localeCompare(aValue, "sv");
    });
    rows.forEach(row => tbody.appendChild(row));
});

// ============================================================
// STUDENTER
// ============================================================
document.addEventListener("change", (event) => {
    if (event.target.id !== "selectAll") return;

    document.querySelectorAll(".student-checkbox")
        .forEach(cb => {
            cb.checked = event.target.checked;
        });
});

// ============================================================
// MODALER
// ============================================================
document.addEventListener("hide.bs.modal", (event) => {
    if (event.target.contains(document.activeElement)) {
        document.activeElement.blur();
    }
});

document.body.addEventListener("htmx:afterRequest", (event) => {
    if (!event.detail.successful) return;
    const element = event.target;
    if (!element.matches("[data-modal-close]")) return;
    const modalElement = element.closest(".modal");
    if (!modalElement) return;
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) {
        modal.hide();
    }
});

// ============================================================
// TOASTS
// ============================================================
document.body.addEventListener("showToast", (event) => {
    window.dispatchEvent(
        new CustomEvent("toast", {
            detail: event.detail
        })
    );
});

document.addEventListener("alpine:init", () => {
    Alpine.data("toast", () => ({
        visible: false,
        message: "",
        type: "success",
        show(detail) {
            this.message = detail.message;
            this.type = detail.level;
            this.visible = true;
            setTimeout(() => {
                this.visible = false;
            }, detail.duration);
        }
    }));
});

// ============================================================
// INITIERING
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
    initTomSelects();

    document.querySelectorAll(".toast").forEach(toastElement => {
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
    });

    document.querySelectorAll(".alert[data-auto-dismiss]").forEach(alert => {
        setTimeout(() => {
            alert.remove();
        }, 4000);
    });
});

document.body.addEventListener("htmx:afterSwap", (event) => {
    initTomSelects(event.target);
});