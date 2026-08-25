// Initierar Tomselect (klass add-tomselect-btn på plusknapp skcikas dit från enter)
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

document.addEventListener(
    "DOMContentLoaded",
    () => initTomSelects()
);


document.body.addEventListener(
    "htmx:afterSwap",
    (event) => {
        initTomSelects(event.target);
    }
);


// Har koll på checkboxarna
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

// Hanterar markering av elever i students/manage
function setupStudentSelection() {
    const selectAll = document.getElementById("selectAll");
    const checkboxes = document.querySelectorAll(".student-checkbox");
    if (!selectAll) return;
    selectAll.addEventListener("change", () => {
        checkboxes.forEach(cb => {
            cb.checked = selectAll.checked;
        });
    });

}

// sortera elevtabellen i students.manage baserat på kolum
function setupTableSorting() {
    document.querySelectorAll(".sortable").forEach(header => {
        header.addEventListener("click", () => {
            const table = header.closest("table");
            const tbody = table.tBodies[0];
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
            icon.className = ascending
                ? "bi bi-caret-down-fill ms-1"
                : "bi bi-caret-up-fill ms-1";
            rows.sort((a, b) => {
                const aValue = a.cells[column].textContent.trim();
                const bValue = b.cells[column].textContent.trim();
                return ascending
                    ? aValue.localeCompare(bValue, "sv")
                    : bValue.localeCompare(aValue, "sv");
            });
            rows.forEach(row => tbody.appendChild(row));
        });
    });
}   

// Kör checkbox och kolumnsortering vid sidstart
document.addEventListener(
    "DOMContentLoaded",
    () => {
        setupStudentSelection();
        setupTableSorting();
    }
);

// Kör checkbox och kolumnsortering vid HTMX-anrop
document.body.addEventListener(
    "htmx:afterSwap",
    (event) => {
        if (event.target.id === "studentsTable") {
            setupStudentSelection();
            setupTableSorting();
        }
    }
);

// Blura ett element när modalen ska stängas ( för att det ska funka )
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

// Flask flash
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".toast").forEach(toastElement => {
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
    });
});

document.querySelectorAll('.alert[data-auto-dismiss]').forEach(alert => {
    setTimeout(() => {
        alert.remove();
    }, 4000);
});

// Alpine-toast
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