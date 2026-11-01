document.addEventListener("alpine:init", () => {

    Alpine.data("filterableSelection", () => ({
        selectedIds: [],
        rows: [],

        init() {
            this.updateRows();

            this.$root.addEventListener("htmx:afterSwap", event => {
                if (event.target.id === "studentsTable") {
                    this.updateRows();
                }
            });
        },

        updateRows() {
            this.rows = [
                ...this.$root.querySelectorAll("[data-selectable-row]")
            ];
        },

        get visibleRows() {
            return this.rows;
        },

        get allVisibleSelected() {
            return this.visibleRows.length > 0 &&
                this.visibleRows.every(row =>
                    this.selectedIds.includes(
                        row.querySelector(".selection-checkbox")?.value
                    )
                );
        },

        get someVisibleSelected() {
            return this.visibleRows.some(row =>
                this.selectedIds.includes(
                    row.querySelector(".selection-checkbox")?.value
                )
            ) && !this.allVisibleSelected;
        },

        toggleVisible(checked) {
            const ids = this.visibleRows
                .map(row => row.querySelector(".selection-checkbox")?.value)
                .filter(Boolean);

            if (checked) {
                this.selectedIds = [...new Set([...this.selectedIds, ...ids])];
            } else {
                this.selectedIds = this.selectedIds.filter(
                    id => !ids.includes(id)
                );
            }
        },

        toggleOne(id, checked) {
            if (checked) {
                if (!this.selectedIds.includes(id)) {
                    this.selectedIds.push(id);
                }
            } else {
                this.selectedIds = this.selectedIds.filter(
                    selectedId => selectedId !== id
                );
            }
        }
    }));
 
    Alpine.data("immediateSelection", (url, templateUrl, pageMode) => ({
        selectedIds: [],
        rows: [],
        pageMode: pageMode,

        init() {
            this.updateRows();

            // Läs in initialt urval en gång.
            this.selectedIds = this.rows
                .filter(row => row.dataset.selected === "true")
                .map(row => String(row.dataset.id));

            this.$root.addEventListener("htmx:afterSwap", event => {
                if (event.target.id === "questionSelection") {
                    // Uppdatera raderna, men behåll hela urvalet.
                    this.updateRows();
                }
            });
        },

        updateRows() {
            this.rows = [
                ...this.$root.querySelectorAll("[data-selectable-row]")
            ];
        },

        get allVisibleSelected() {
            return this.rows.length > 0 &&
                this.rows.every(row =>
                    this.selectedIds.includes(String(row.dataset.id))
                );
        },

        get someVisibleSelected() {
            return this.rows.some(row =>
                this.selectedIds.includes(String(row.dataset.id))
            ) && !this.allVisibleSelected;
        },

        toggleOne(id) {
            id = String(id);

            if (this.selectedIds.includes(id)) {
                this.selectedIds = this.selectedIds.filter(
                    item => item !== id
                );
            } else {
                this.selectedIds = [...this.selectedIds, id];
            }

            this.submit();
        },

        toggleAll(checked) {
            const visibleIds = this.rows.map(
                row => String(row.dataset.id)
            );

            if (checked) {
                this.selectedIds = [
                    ...new Set([...this.selectedIds, ...visibleIds])
                ];
            } else {
                this.selectedIds = this.selectedIds.filter(
                    id => !visibleIds.includes(id)
                );
            }

            this.submit();
        },

        submit() {
            const params = new URLSearchParams();
            const filters = document.getElementById("questionFilters");

            if (filters) {
                new FormData(filters).forEach((value, key) => {
                    if (
                        key !== "selected_question_ids" &&
                        key !== "selection_submitted"
                    ) {
                        params.append(key, value);
                    }
                });
            }

            this.selectedIds.forEach(id => {
                params.append("selected_question_ids", id);
            });

            params.set("selection_submitted", "1");

            htmx.ajax("GET", `${url}?${params.toString()}`, {
                target: "#questionSelection",
                swap: "outerHTML"
            });
        },

        createTemplate() {
            if (!this.selectedIds.length) return;

            const params = new URLSearchParams();

            this.selectedIds.forEach(id => {
                params.append("selected_question_ids", id);
            });

            window.location.href =
                `${templateUrl}?${params.toString()}`;
        }
    }));

    
    Alpine.data("templateSelection", (initialIds) => ({
        selectedIds: initialIds.map(String),
        rows: [],

        init() {
            this.updateRows();

            this.$root.addEventListener("htmx:afterSwap", event => {
                if (event.target.id === "templateQuestionsTable") {
                    this.updateRows();
                }
            });
        },

        updateRows() {
            this.rows = [
                ...this.$root.querySelectorAll("[data-selectable-row]")
            ];
        },

        get allVisibleSelected() {
            return this.rows.length > 0 &&
                this.rows.every(row =>
                    this.selectedIds.includes(row.dataset.id)
                );
        },

        get someVisibleSelected() {
            return this.rows.some(row =>
                this.selectedIds.includes(row.dataset.id)
            ) && !this.allVisibleSelected;
        },

        toggleOne(id) {
            if (this.selectedIds.includes(id)) {
                this.selectedIds = this.selectedIds.filter(
                    item => item !== id
                );
            } else {
                this.selectedIds = [...this.selectedIds, id];
            }
        },

        toggleAll(checked) {
            const visibleIds = this.rows.map(row => row.dataset.id);

            if (checked) {
                this.selectedIds = [
                    ...new Set([...this.selectedIds, ...visibleIds])
                ];
            } else {
                this.selectedIds = this.selectedIds.filter(
                    id => !visibleIds.includes(id)
                );
            }
        }
    }));

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