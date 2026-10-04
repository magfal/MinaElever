// ============================================================
// TOM SELECT
// ============================================================

function initTomSelects(root = document) {
    root.querySelectorAll(".tomselect-create").forEach(el => {
        if (el.tomselect) return;
        const tom = new TomSelect(el, {
            create: true,
            createOnBlur: true,
            persist: false,
            dropdownParent: "body"
        });
        const button = el
            .closest(".input-group")
            ?.querySelector(".add-tomselect-btn");
        if (button) {
            tom.control_input.addEventListener("keydown", event => {
                if (event.key !== "Enter") return;
                event.preventDefault();
                event.stopPropagation();
                el.dispatchEvent(
                    new Event("change", { bubbles: true })
                );
                button.click();
            });
        }
    });
    root.querySelectorAll(".tomselect-filter").forEach(el => {
        if (el.tomselect) return;
        const tom = new TomSelect(el, {
            create: false,
            allowEmptyOption: true
        });
        if (el.id !== "mediaTags") return;
        tom.control_input.addEventListener("input", () => {
            updateAddMediaTagButton();
        });
        tom.on("dropdown_open", () => {
            updateAddMediaTagButton();
        });
        const button = document.querySelector("#addMediaTagBtn");
        if (!button) return;
        let mediaTagName = "";
        button.addEventListener("mousedown", () => {
            mediaTagName = tom.control_input.value.trim();
        });
        button.onclick = () => {
            if (!mediaTagName) return;
            const url = new URL(
                button.dataset.url,
                window.location.origin
            );
            url.searchParams.set("name", mediaTagName);
            htmx.ajax("GET", url.toString(), {
                target: "#mediaTagModalContent",
                swap: "innerHTML"
            });
        };
    });
}

function updateAddMediaTagButton() {
    const select = document.querySelector("#mediaTags");
    const button = document.querySelector("#addMediaTagBtn");
    if (!select?.tomselect || !button) return;
    const tom = select.tomselect;
    const value = tom.control_input.value.trim();
    if (!value) {
        button.disabled = true;
        return;
    }
    const exists = Object.values(tom.options).some(option =>
        option.text.trim().toLowerCase() === value.toLowerCase()
    );
    button.disabled = exists;
}

// Ny media-tagg har skapats
document.body.addEventListener("media-tag-created", event => {
    const data = event.detail;
    const select = document.querySelector("#mediaTags");
    if (!select?.tomselect) return;
    const tom = select.tomselect;
    tom.addOption({
        value: String(data.id),
        text: data.name
    });
    tom.addItem(String(data.id));
    tom.refreshOptions(false);
    const modal = document.getElementById("mediaTagModal");
    if (modal) {
        bootstrap.Modal.getOrCreateInstance(modal).hide();
    }
});

// Visa minimodalen när formuläret har laddats
document.body.addEventListener("htmx:afterSwap", event => {
    if (event.detail.target.id !== "mediaTagModalContent") return;
    const modal = document.getElementById("mediaTagModal");
    if (modal) {
        bootstrap.Modal.getOrCreateInstance(modal).show();
    }
});

// ============================================================
// CHECKBOXAR
// ============================================================
// Hanterar "markera alla" för tabeller där endast synliga rader
// ska påverkas av markeringen.
function setupSelectAll(selectAllId, checkboxName, tableId) {
    const selectAll = document.getElementById(selectAllId);
    if (!selectAll) return;
    function getVisibleCheckboxes() {
        return [...document.querySelectorAll(`#${tableId} tbody tr`)]
            .filter(row => row.style.display !== "none")
            .map(row =>
                row.querySelector(`input[name="${checkboxName}"]`)
            )
            .filter(Boolean);
    }
    function updateSelectAll() {
        const checkboxes = getVisibleCheckboxes();
        selectAll.checked =
            checkboxes.length > 0 &&
            checkboxes.every(cb => cb.checked);
    }
    selectAll.addEventListener("change", () => {
        getVisibleCheckboxes().forEach(cb => {
            cb.checked = selectAll.checked;
        });
        updateSelectAll();
    });
    document
        .querySelectorAll(`input[name="${checkboxName}"]`)
        .forEach(cb => {
            cb.addEventListener("change", updateSelectAll);
        });
    window.updateSelectAll = updateSelectAll;
    updateSelectAll();
}


// ============================================================
// FRÅGOR
// ============================================================
// ------------------------------------------------------------
// Frågepreview
// ------------------------------------------------------------
// Visar Markdown, bilder och MathJax medan frågan skrivs.
function setupQuestionPreview() {
    const textarea = document.getElementById("questionText");
    const preview = document.getElementById("questionPreview");
    if (!textarea || !preview) return;
    function updatePreview() {
        if (window.MathJax && MathJax.typesetClear) {
            MathJax.typesetClear([preview]);
        }
        let html = marked.parse(textarea.value);
        html = html.replace(
            /\[([^\[\]:]+)(?::(\d+))?\]/g,
            (match, mediaName, size) => {
                const mediaId = mediaMap[mediaName];
                if (!mediaId) return match;
                const width = size ? `${size}%` : "100%";
                return `<img
                    src="/media/file/${mediaId}"
                    class="question-image my-2"
                    style="width: ${width};"
                    alt="${mediaName}">`;
            }
        );
        preview.innerHTML = DOMPurify.sanitize(html);
        if (window.MathJax && MathJax.typesetPromise) {
            MathJax.typesetPromise([preview]);
        }
    }
    textarea.addEventListener("input", updatePreview);
    updatePreview();
}

// ------------------------------------------------------------
// Full rendering av frågor
// ------------------------------------------------------------
// Renderar frågetext i tabeller eller andra vyer där full Markdown
// och MathJax-visning används.
function setupQuestionFullRender(container = document) {
    const renderedQuestions = container.querySelectorAll(
        ".question-rendered"
    );
    renderedQuestions.forEach(rendered => {
        const cell = rendered.closest(".question-cell");
        const source = cell?.querySelector(".question-source");
        if (!source) return;
        let html = marked.parse(source.value);
        html = html.replace(
            /\[([^\[\]:]+)(?::(\d+))?\]/g,
            (match, mediaName, size) => {
                const mediaId = mediaMap[mediaName];
                if (!mediaId) return match;
                const width = size ? `${size}%` : "100%";
                return `<img
                    src="/media/file/${mediaId}"
                    class="question-image my-2"
                    style="width: ${width};"
                    alt="${mediaName}">`;
            }
        );
        rendered.innerHTML = DOMPurify.sanitize(html);
        if (window.MathJax && MathJax.typesetPromise) {
            MathJax.typesetPromise([rendered]);
        }
    });
}

// ------------------------------------------------------------
// Ren text för frågetabellen
// ------------------------------------------------------------
// Omvandlar frågetext till kort, ren text för tabellvisning.
function setupQuestionPlainText(container = document) {
    const cells = container.querySelectorAll(".question-cell");
    cells.forEach(cell => {
        const source = cell.querySelector(".question-source");
        const target = cell.querySelector(".question-table-text");
        if (!source || !target) return;
        let text = source.value;
        text = text.replace(
            /\[([^\[\]:]+)(?::(\d+))?\]/g,
            "[$1]"
        );
        text = text.replace(
            /!\[[^\]]*\]\([^)]*\)/g,
            "[bild]"
        );
        text = text.replace(/\*\*(.*?)\*\*/g, "$1");
        text = text.replace(/__(.*?)__/g, "$1");
        text = text.replace(/\*(.*?)\*/g, "$1");
        text = text.replace(/_(.*?)_/g, "$1");
        text = text.replace(/`([^`]+)`/g, "$1");
        text = text.replace(/^#{1,6}\s+/gm, "");
        text = text.replace(/^\s*[-*+]\s+/gm, "");
        text = text.replace(/^\s*>\s?/gm, "");
        text = text.replace(/\$\$([\s\S]*?)\$\$/g, "$1");
        text = text.replace(/\$([^$\n]+)\$/g, "$1");
        text = text.replace(/\s*\n\s*/g, " ");
        text = text.replace(/\s+/g, " ");
        text = text.trim();
        const maxLength = 180;
        if (text.length > maxLength) {
            text = text.substring(0, maxLength).trimEnd() + "…";
        }
        target.textContent = text;
    });
}

// ------------------------------------------------------------
// Infoga bildreferens
// ------------------------------------------------------------
// Lägger in [bildnamn] där markören står i frågetexten.
function setupImageReferences() {
    const questionText = document.getElementById("questionText");
    if (!questionText) return;
    document.querySelectorAll(".insert-image-reference").forEach(button => {
        button.addEventListener("click", () => {
            const mediaName = button.dataset.mediaName;
            if (!mediaName) return;
            const reference = `[${mediaName}]`;
            const start = questionText.selectionStart;
            const end = questionText.selectionEnd;
            questionText.value =
                questionText.value.slice(0, start) +
                reference +
                questionText.value.slice(end);
            questionText.focus();
            const cursorPosition = start + reference.length;
            questionText.setSelectionRange(
                cursorPosition,
                cursorPosition
            );
            questionText.dispatchEvent(
                new Event("input", { bubbles: true })
            );
        });
    });
}

// ------------------------------------------------------------
// Mediaredigering
// ------------------------------------------------------------
// Fyller i mediats redigeringsmodal när den öppnas.
function setupMediaEdit() {
    const modal = document.getElementById("editMediaModal");
    if (!modal) return;
    const form = document.getElementById("editMediaForm");
    const nameInput = document.getElementById("mediaName");
    const tagSelect = document.getElementById("mediaTags");
    modal.addEventListener("show.bs.modal", event => {
        const button = event.relatedTarget;
        if (!button) return;
        const mediaId = button.dataset.mediaId;
        const mediaName = button.dataset.mediaName;
        const mediaTags = button.dataset.mediaTags
            ? button.dataset.mediaTags.split(",")
            : [];
        form.action = `/media/${mediaId}/edit`;
        nameInput.value = mediaName;
        const tomSelect = tagSelect.tomselect;
        if (tomSelect) {
            tomSelect.clear(true);
            tomSelect.setValue(mediaTags, true);
        } else {
            Array.from(tagSelect.options).forEach(option => {
                option.selected = mediaTags.includes(option.value);
            });
        }
    });
}

// ------------------------------------------------------------
// Mediaurval
// ------------------------------------------------------------
// Lägger in en bildreferens när en bild väljs i mediaväljaren.
function setupMediaSelection() {
    const questionText = document.getElementById("questionText");
    if (!questionText) return;
    document.addEventListener("click", event => {
        const button = event.target.closest(".media-select-btn");
        if (!button) return;
        const mediaName = button.dataset.mediaName;
        if (!mediaName) return;
        const imageSyntax = `[${mediaName}]`;
        const start = questionText.selectionStart;
        const end = questionText.selectionEnd;
        questionText.value =
            questionText.value.substring(0, start) +
            imageSyntax +
            questionText.value.substring(end);
        const cursorPosition = start + imageSyntax.length;
        questionText.focus();
        questionText.setSelectionRange(
            cursorPosition,
            cursorPosition
        );
        questionText.dispatchEvent(
            new Event("input", { bubbles: true })
        );
    });
}

// ============================================================
// FRÅGETYPER OCH SVARSFÄLT
// ============================================================
// Bygger rätt facitfält beroende på vald frågetyp.
function setupQuestionAnswerFields() {
    const questionType = document.getElementById("questionType");
    const answerFields = document.getElementById("answerFields");
    if (!questionType || !answerFields) return;
    const questionDataElement =
        document.getElementById("questionData");
    const questionData = questionDataElement
        ? JSON.parse(questionDataElement.textContent)
        : null;
    // --------------------------------------------------------
    // Fritext
    // --------------------------------------------------------
    function addTextAnswer(value = "") {
        const row = document.createElement("div");
        row.className = "input-group mb-2";
        row.innerHTML = `
            <input
                type="text"
                name="correct_answers"
                class="form-control"
                value="${value}"
                placeholder="Rätt svar">
            <button
                type="button"
                class="btn btn-outline-danger remove-answer">
                Ta bort
            </button>
        `;
        row.querySelector(".remove-answer")
            .addEventListener("click", () => row.remove());
        answerFields
            .querySelector("#textAnswerList")
            .appendChild(row);
    }
    function renderTextAnswers() {
        answerFields.innerHTML = `
            <label class="form-label">Rätt svar</label>
            <div id="textAnswerList"></div>
            <button
                type="button"
                id="addTextAnswer"
                class="btn btn-outline-secondary btn-sm">
                + Lägg till rätt svar
            </button>
        `;
        document
            .getElementById("addTextAnswer")
            .addEventListener("click", () => addTextAnswer());
        const answers =
            questionData?.expected_answer?.answers ?? [];
        if (answers.length > 0) {
            answers.forEach(answer => addTextAnswer(answer));
        } else {
            addTextAnswer();
        }
    }

    // --------------------------------------------------------
    // Tal
    // --------------------------------------------------------
    function renderNumberAnswer() {
        const value =
            questionData?.expected_answer?.answer ?? "";
        answerFields.innerHTML = `
            <div class="row g-3">
                <div class="col-12 col-md-6">
                    <label
                        for="correctNumber"
                        class="form-label">
                        Rätt svar
                    </label>
                    <input
                        id="correctNumber"
                        type="number"
                        step="any"
                        name="correct_number"
                        class="form-control"
                        value="${value}">
                </div>
            </div>
        `;
    }

    // --------------------------------------------------------
    // Sant / falskt
    // --------------------------------------------------------
    function renderBooleanAnswer() {
        const value =
            questionData?.expected_answer?.answer;
        answerFields.innerHTML = `
            <label class="form-label">Rätt svar</label>
            <div class="form-check">
                <input
                    class="form-check-input"
                    type="radio"
                    name="correct_boolean"
                    id="correctTrue"
                    value="true"
                    ${value === true ? "checked" : ""}>
                <label
                    class="form-check-label"
                    for="correctTrue">
                    Sant
                </label>
            </div>
            <div class="form-check">
                <input
                    class="form-check-input"
                    type="radio"
                    name="correct_boolean"
                    id="correctFalse"
                    value="false"
                    ${value === false ? "checked" : ""}>
                <label
                    class="form-check-label"
                    for="correctFalse">
                    Falskt
                </label>
            </div>
        `;
    }

    // --------------------------------------------------------
    // Datum
    // --------------------------------------------------------
    function renderDateAnswer() {
        const value =
            questionData?.expected_answer?.answer ?? "";
        answerFields.innerHTML = `
            <div class="col-12 col-md-6">
                <label
                    for="correctDate"
                    class="form-label">
                    Rätt datum
                </label>
                <input
                    id="correctDate"
                    type="date"
                    name="correct_date"
                    class="form-control"
                    value="${value}">
            </div>
        `;
    }

    // --------------------------------------------------------
    // Slider
    // --------------------------------------------------------
    function renderSliderAnswer() {
        answerFields.innerHTML = `
            <div class="row g-3 mb-4">
                <div class="col-12">
                    <h6>Sliderinställningar</h6>
                </div>
                <div class="col-12 col-md-4">
                    <label for="sliderMin" class="form-label">
                        Minvärde
                    </label>
                    <input
                        id="sliderMin"
                        type="number"
                        name="slider_min"
                        class="form-control"
                        value="0">
                </div>
                <div class="col-12 col-md-4">
                    <label for="sliderMax" class="form-label">
                        Maxvärde
                    </label>
                    <input
                        id="sliderMax"
                        type="number"
                        name="slider_max"
                        class="form-control"
                        value="100">
                </div>
                <div class="col-12 col-md-4">
                    <label for="sliderStep" class="form-label">
                        Steg
                    </label>
                    <input
                        id="sliderStep"
                        type="number"
                        name="slider_step"
                        class="form-control"
                        value="1">
                </div>
            </div>
            <hr>
            <div class="row g-3">
                <div class="col-12">
                    <h6>Facit (valfritt)</h6>
                </div>
                <div class="col-12 col-md-6">
                    <label
                        for="correctSliderValue"
                        class="form-label">
                        Rätt svar
                    </label>
                    <input
                        id="correctSliderValue"
                        type="number"
                        step="any"
                        name="correct_number"
                        class="form-control">
                </div>
            </div>
        `;
    }

    // --------------------------------------------------------
    // Svarsalternativ
    // --------------------------------------------------------
    function renderChoiceAnswers(multiple = false) {
        const answerType = multiple ? "checkbox" : "radio";
        const correctName = multiple
            ? "correct_choice_indexes"
            : "correct_choice_index";
        const title = multiple
            ? "Flervalsalternativ"
            : "Svarsalternativ";
        const helpText = multiple
            ? "Lägg till möjliga svar och markera ett eller flera rätta svar."
            : "Lägg till möjliga svar och markera det rätta svaret.";

        answerFields.innerHTML = `
            <div class="mb-3">
                <h6 class="mb-1">${title}</h6>
                <p class="text-muted mb-3">${helpText}</p>
                <div id="choiceAnswerList"></div>
                <button
                    type="button"
                    id="addChoiceAnswer"
                    class="btn btn-outline-secondary btn-sm">
                    + Lägg till svarsalternativ
                </button>
            </div>
        `;
        function updateChoiceIndexes() {
            answerFields
                .querySelectorAll(".choice-answer-row")
                .forEach((row, index) => {
                    const correctInput = row.querySelector(
                        "input[type='radio'], input[type='checkbox']"
                    );

                    correctInput.value = index;
                });
        }
        function addChoiceAnswer(value = "", isCorrect = false) {
            const row = document.createElement("div");
            row.className =
                "input-group mb-2 choice-answer-row";
            row.innerHTML = `
                <div class="input-group-text">
                    <input
                        class="form-check-input mt-0"
                        type="${answerType}"
                        name="${correctName}"
                        aria-label="Rätt svar"
                        ${isCorrect ? "checked" : ""}>
                </div>
                <input
                    type="text"
                    name="choice_options"
                    class="form-control"
                    value="${value}"
                    placeholder="Svarsalternativ">
                <button
                    type="button"
                    class="btn btn-outline-danger remove-choice">
                    Ta bort
                </button>
            `;
            row
                .querySelector(".remove-choice")
                .addEventListener("click", () => {
                    row.remove();
                    updateChoiceIndexes();
                });
            answerFields
                .querySelector("#choiceAnswerList")
                .appendChild(row);

            updateChoiceIndexes();
        }
        document
            .getElementById("addChoiceAnswer")
            .addEventListener("click", () => addChoiceAnswer());
        const choices = questionData?.choices ?? [];
        if (choices.length > 0) {
            choices.forEach(choice => {
                addChoiceAnswer(
                    choice.text,
                    choice.is_correct
                );
            });
        } else {
            addChoiceAnswer();
            addChoiceAnswer();
        }
    }

    function renderSingleChoiceAnswer() {
        renderChoiceAnswers(false);
    }

    function renderMultipleChoiceAnswer() {
        renderChoiceAnswers(true);
    }

    // --------------------------------------------------------
    // Filuppladdning
    // --------------------------------------------------------
    function renderFileUploadAnswer() {
        answerFields.innerHTML = `
            <div class="text-muted">
                Den här frågetypen har normalt inget
                automatiskt rätt svar. Eleven lämnar sitt
                svar genom att ladda upp en eller flera filer.
            </div>
        `;
    }

    // --------------------------------------------------------
    // Välj rätt svarsfält
    // --------------------------------------------------------
    function renderAnswerFields() {
        switch (questionType.value) {
            case "TEXT":
                renderTextAnswers();
                break;
            case "NUMBER":
                renderNumberAnswer();
                break;
            case "BOOLEAN":
                renderBooleanAnswer();
                break;
            case "DATE":
                renderDateAnswer();
                break;
            case "SLIDER":
                renderSliderAnswer();
                break;
            case "SINGLE_CHOICE":
                renderSingleChoiceAnswer();
                break;
            case "MULTIPLE_CHOICE":
                renderMultipleChoiceAnswer();
                break;
            case "FILE_UPLOAD":
                renderFileUploadAnswer();
                break;
            default:
                answerFields.innerHTML = "";
        }
    }

    questionType.addEventListener("change", renderAnswerFields);
    renderAnswerFields();
}

// ============================================================
// UPPGIFTER
// ============================================================
// Hanterar filtrering och elevurval på skapa/redigera uppgift.
function setupAssignmentStudents() {
    const table = document.getElementById("assignmentStudentsTable");
    if (!table) return;

    const search = document.getElementById("assignmentStudentSearch");
    const group = document.getElementById("assignmentStudentGroup");
    const team = document.getElementById("assignmentStudentTeam");
    const selectAll = document.getElementById("assignmentSelectAll");
    const selectVisible = document.getElementById("assignmentSelectVisible");
    const studentCount = document.getElementById("assignmentStudentCount");
    const selectedStudentCount =
        document.getElementById("assignmentSelectedStudentCount");

    function getRows() {
        return [
            ...table.querySelectorAll(
                "tbody tr[data-assignment-student]"
            )
        ];
    }

    function getVisibleRows() {
        const searchText = search.value.trim().toLowerCase();
        const groupId = group.value;
        const teamId = team.value;

        return getRows().filter(row => {
            const name = row.dataset.name || "";
            const rowGroup = row.dataset.group || "";
            const rowTeams = row.dataset.teams
                ? row.dataset.teams.split(",")
                : [];

            return (
                (!searchText || name.includes(searchText)) &&
                (!groupId || rowGroup === groupId) &&
                (!teamId || rowTeams.includes(teamId))
            );
        });
    }

    function update() {
        const rows = getRows();
        const visibleRows = getVisibleRows();
        rows.forEach(row => {
            row.style.display =
                visibleRows.includes(row) ? "" : "none";
        });
        studentCount.textContent = visibleRows.length;
        const checkboxes = rows
            .map(row => row.querySelector(".student-checkbox"))
            .filter(Boolean);
        const selected = checkboxes.filter(cb => cb.checked);
        selectedStudentCount.textContent = selected.length;
        const visibleCheckboxes = visibleRows
            .map(row => row.querySelector(".student-checkbox"))
            .filter(Boolean);
        const visibleSelected = visibleCheckboxes
            .filter(cb => cb.checked);
        selectAll.checked =
            visibleCheckboxes.length > 0 &&
            visibleSelected.length === visibleCheckboxes.length;
        selectAll.indeterminate =
            visibleSelected.length > 0 &&
            visibleSelected.length < visibleCheckboxes.length;
    }
    
    search.addEventListener("input", update);
    group.addEventListener("change", update);
    team.addEventListener("change", update);
    selectAll.addEventListener("change", () => {
        getVisibleRows().forEach(row => {
            const checkbox =
                row.querySelector(".student-checkbox");

            if (checkbox) {
                checkbox.checked = selectAll.checked;
            }
        });

        update();
    });

    selectVisible.addEventListener("click", () => {
        getVisibleRows().forEach(row => {
            const checkbox =
                row.querySelector(".student-checkbox");

            if (checkbox) {
                checkbox.checked = true;
            }
        });

        update();
    });

    table.addEventListener("change", event => {
        if (event.target.matches(".student-checkbox")) {
            update();
        }
    });
    update();
}

// ------------------------------------------------------------
// Skapa uppgift från markerade elever
// ------------------------------------------------------------
// Öppnar sidan för ny uppgift med de markerade eleverna förvalda.
function setupStudentAssignmentButton() {
    const button =
        document.getElementById("createAssignmentFromSelected");

    if (!button) return;
    button.addEventListener("click", () => {
        const checkboxes =
            document.querySelectorAll(".student-checkbox:checked");
        if (checkboxes.length === 0) {
            alert("Markera minst en elev.");
            return;
        }
        const params = new URLSearchParams();
        checkboxes.forEach(checkbox => {
            params.append("student_ids", checkbox.value);
        });
        window.location.href =
            `/assignments/new?${params.toString()}`;
    });
}

// ============================================================
// MODALER
// ============================================================
// Tar bort fokus från element inne i en Bootstrap-modal innan den stängs.
function setupModalListeners() {
    document.addEventListener("hide.bs.modal", event => {
        if (event.target.contains(document.activeElement)) {
            document.activeElement.blur();
        }
    });
    document.body.addEventListener("htmx:afterRequest", event => {
        if (!event.detail.successful) return;
        const element = event.target;
        if (!element.matches("[data-modal-close]")) return;
        const modalElement = element.closest(".modal");
        if (!modalElement) return;
        const modal =
            bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    });
}

// ============================================================
// TOASTS
// ============================================================
// ------------------------------------------------------------
// Bootstrap → Alpine
// ------------------------------------------------------------

document.body.addEventListener("showToast", event => {
    window.dispatchEvent(
        new CustomEvent("toast", {
            detail: event.detail
        })
    );
});

// Alpine-komponenten för programmatiska toast-meddelanden.
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

// Visar Bootstrap-toast-meddelanden som redan finns i DOM.
function setupBootstrapToasts() {
    document.querySelectorAll(".toast").forEach(toastElement => {
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
    });
}

// Tar bort alert-meddelanden efter angiven tid.
function setupAutoDismissAlerts() {
    document
        .querySelectorAll(".alert[data-auto-dismiss]")
        .forEach(alert => {
            setTimeout(() => alert.remove(), 4000);
        });
}

// ============================================================
// GLOBALA LYSSNARE
// ============================================================

// ------------------------------------------------------------
// Tabellsortering
// ------------------------------------------------------------
// Sorterar tabeller när en rubrik med .sortable klickas.
document.addEventListener("click", event => {
    const header = event.target.closest(".sortable");
    if (!header) return;
    const table = header.closest("table");
    if (!table) return;
    const tbody = table.tBodies[0];
    if (!tbody) return;
    const rows = Array.from(tbody.rows);
    const column = header.cellIndex;
    const ascending = header.dataset.sort !== "asc";
    header.dataset.sort = ascending ? "asc" : "desc";
    table.querySelectorAll(".sortable").forEach(th => {
        if (th !== header) {
            delete th.dataset.sort;
        }
    });
    table.querySelectorAll(".sortable i").forEach(icon => {
        icon.className = "bi bi-chevron-expand ms-1";
    });
    const icon = header.querySelector("i");
    if (icon) {
        icon.className = ascending
            ? "bi bi-caret-down-fill ms-1"
            : "bi bi-caret-up-fill ms-1";
    }
    rows.sort((a, b) => {
        const aValue = a.cells[column].textContent.trim();
        const bValue = b.cells[column].textContent.trim();
        return ascending
            ? aValue.localeCompare(bValue, "sv")
            : bValue.localeCompare(aValue, "sv");
    });
    rows.forEach(row => tbody.appendChild(row));
});

// ------------------------------------------------------------
// Elevcheckrutor
// ------------------------------------------------------------
// Synkroniserar den gamla globala "selectAll"-kontrollen på studentsidan.
document.addEventListener("change", event => {
    if (event.target.id !== "selectAll") return;
    document.querySelectorAll(".student-checkbox").forEach(cb => {
        cb.checked = event.target.checked;
    });
});

// ============================================================
// INITIERING
// ============================================================
// Initierar funktioner som hör till den aktuella sidan.
document.addEventListener("DOMContentLoaded", () => {
    initTomSelects();
    setupBootstrapToasts();
    setupAutoDismissAlerts();
    setupModalListeners();
    setupQuestionPreview();
    setupQuestionPlainText();
    setupQuestionFullRender();
    setupQuestionAnswerFields();
    setupImageReferences();
    setupMediaEdit();
    setupMediaSelection();
    setupAssignmentStudents();
    setupStudentAssignmentButton();
});

// Initierar funktioner efter att HTMX har ersatt en del av sidan.
document.body.addEventListener("htmx:afterSwap", event => {
    initTomSelects(event.target);
    setupQuestionPlainText(event.detail.target);
    setupQuestionFullRender(event.detail.target);
});