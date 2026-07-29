function initToasts() {
    document
        .querySelectorAll(".toast")
        .forEach(function (toastEl) {
            const delay =
                Number(toastEl.dataset.delay || 5000);
            const toast =
                new bootstrap.Toast(toastEl, {
                    delay: delay
                });
            toast.show();
        });
}

function rememberInput(id) {
    const element = document.getElementById(id);
    if (!element) return;
    const key = "remember_" + id;
    // Återställ
    const saved = localStorage.getItem(key);
    if (saved !== null) {
        element.value = saved;
    }
    // Spara
    element.addEventListener("input", () => {
        localStorage.setItem(key, element.value);
    });
    element.addEventListener("change", () => {
        localStorage.setItem(key, element.value);
    });
}

function rememberSelectedStudents(name) {
    const key = "selected_" + name;
    // Återställ efter omladdning
    const saved = JSON.parse(
        sessionStorage.getItem(key) || "[]"
    );
    document
        .querySelectorAll(`input[name="${name}"]`)
        .forEach(cb => {
            if (saved.includes(cb.value)) {
                cb.checked = true;
            }
        });
    // Uppdatera innan formulär skickas
    document
        .querySelectorAll("form")
        .forEach(form => {
            form.addEventListener(
                "submit",
                function() {
                    const selected = [
                        ...document.querySelectorAll(
                            `input[name="${name}"]:checked`
                        )
                    ]
                    .map(cb => cb.value);
                    sessionStorage.setItem(
                        key,
                        JSON.stringify(selected)
                    );
                }
            );
        });
}

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

function setupTableFilter(options) {
    const searchInput = document.getElementById(options.searchId);
    const filters = options.filters || [];
    if (!searchInput) return;
    function filterTable() {
        const search = searchInput.value.toLowerCase();
        document
            .querySelectorAll(`#${options.tableId} tbody tr`)
            .forEach(row => {
                let visible = true;

                // Sökning
                if (search) {
                    const name = row.dataset.name || "";
                    if (!name.includes(search)) {
                        visible = false;
                    }
                }

                // Dropdown-filter
                filters.forEach(filter => {
                    const element =
                        document.getElementById(filter.id);

                    if (!element) return;
                    const value = element.value;
                    if (
                        value &&
                        row.dataset[filter.data] !== value
                    ) {
                        visible = false;
                    }
                });
                row.style.display =
                    visible ? "" : "none";

            });
        // Uppdatera "markera alla"
        if (typeof updateSelectAll === "function") {
            updateSelectAll();
        }
    }

    searchInput.addEventListener(
        "input",
        filterTable
    );

    filters.forEach(filter => {
        const element =
            document.getElementById(filter.id);
        if (element) {
            element.addEventListener(
                "change",
                filterTable
            );
        }
    });
    // Kör direkt vid sidladdning
    filterTable();
    if (typeof updateSelectAll === "function") {
        updateSelectAll();
    }
}

function showMessage(message, category="success") {

    const container =
        document.getElementById("toastContainer");

    if (!container) return;

    const toastElement = document.createElement("div");

    toastElement.className =
        "toast";

    toastElement.setAttribute(
        "role",
        "alert"
    );

    toastElement.innerHTML = `
        <div class="toast-body">
            ${message}
        </div>
    `;

    container.appendChild(toastElement);

    const toast =
        new bootstrap.Toast(
            toastElement,
            {
                delay:5000
            }
        );

    toast.show();
}

function closeModal() {
    const modalElement =
        document.getElementById("studentModal");
    const modal =
        bootstrap.Modal.getInstance(modalElement);
    if (modal) {
        modal.hide();
    }
}


document.body.addEventListener(
    "showToast",
    function(event) {
        const container =
            document.getElementById("toastContainer");
        const toastId =
            "toast-" + Date.now();
        container.insertAdjacentHTML(
            "beforeend",
            `
            <div 
                id="${toastId}"
                class="toast"
                role="alert"
                data-bs-delay="5000">
                <div class="toast-body">
                    ${event.detail.message}
                </div>
            </div>
            `
        );
        const toastElement =
            document.getElementById(toastId);
        const toast =
            new bootstrap.Toast(
                toastElement,
                {delay: 5000}
            );
        toastElement.addEventListener(
            "hidden.bs.toast",
            function () {
                toastElement.remove();
            }
        );
        toast.show();
    }
);

///// Nya funktioner HTMX/Alpine style

window.addEventListener("close-modal", () => {

    const modalElement = document.getElementById("groupModal");

    console.log("Modal element:", modalElement);

    const modal = bootstrap.Modal.getInstance(modalElement);

    console.log("Modal instance:", modal);

});

window.addEventListener("close-modal", () => {

    const modalElement = document.getElementById("groupModal");

    if (!modalElement) {
        console.log("Modal hittades inte");
        return;
    }

    const modal = bootstrap.Modal.getInstance(modalElement);

    if (modal) {
        modal.hide();
    } else {
        console.log("Bootstrap-modalinstans saknas");
    }

});

document.addEventListener("alpine:init", () => {
    Alpine.data("toast", () => ({
        visible: false,
        message: "",
        type: "success",
        show(detail) {
            this.message = detail.message;
            this.type = detail.type || "success";
            this.visible = true;
            setTimeout(() => {
                this.visible = false;
            }, 5000);
        }
    }));
});

document.body.addEventListener("show-toast", e => console.log(e.detail))

function closeGroupModal() {

    const modal =
        bootstrap.Modal.getInstance(
            document.getElementById("groupModal")
        );

    modal.hide();

}