// --------------------------------------------------
// Spara och återställ formulärfält
// --------------------------------------------------

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

// --------------------------------------------------
// Markera alla synliga checkboxar i en tabell
// --------------------------------------------------

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

// --------------------------------------------------
// Behåll markerade elever efter sidladdning
// --------------------------------------------------

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


// --------------------------------------------------
// Filtrerar tabellrader efter text och dropdown-filter
// --------------------------------------------------

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