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
                persist: false,
                dropdownParent: "body"
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
    root.querySelectorAll(".tomselect-filter")
        .forEach(el => {

            if (el.tomselect) return;

            new TomSelect(el, {
                create: false,
                allowEmptyOption: true
            });
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

// ===============================
// Question editor
// ===============================

function setupQuestionPreview() {
    const textarea = document.getElementById("questionText");
    const preview = document.getElementById("questionPreview");

    if (!textarea || !preview) {
        return;
    }

    function updatePreview() {
        if (window.MathJax && MathJax.typesetClear) {
            MathJax.typesetClear([preview]);
        }

        let html = marked.parse(textarea.value);

        html = html.replace(
            /\[([^\[\]:]+)(?::(\d+))?\]/g,
            (match, mediaName, size) => {
                const mediaId = mediaMap[mediaName];

                if (!mediaId) {
                    return match;
                }

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

function setupQuestionFullRender(container = document) {
    const renderedQuestions = container.querySelectorAll(
        ".question-rendered"
    );

    renderedQuestions.forEach((rendered) => {
        const source = rendered
            .closest(".question-cell")
            .querySelector(".question-source");

        if (!source) {
            return;
        }

        // Rendera Markdown
        let html = marked.parse(source.value);

        html = html.replace(
            /\[([^\[\]:]+)(?::(\d+))?\]/g,
            (match, mediaName, size) => {
                const mediaId = mediaMap[mediaName];

                if (!mediaId) {
                    return match;
                }

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

function setupQuestionPlainText(container = document) {
    const cells = container.querySelectorAll(
        ".question-cell"
    );
    cells.forEach((cell) => {
        const source = cell.querySelector(".question-source");
        const target = cell.querySelector(".question-table-text");
        if (!source || !target) {
            return;
        }
        let text = source.value;
        // Bildreferenser → [bild]
        text = text.replace(
            /\[([^\[\]:]+)(?::(\d+))?\]/g,
            "[$1]"
        );
        // Markdown-bilder → [bild]
        text = text.replace(
            /!\[[^\]]*\]\([^)]*\)/g,
            "[bild]"
        );
        // Fetstil
        text = text.replace(
            /\*\*(.*?)\*\*/g,
            "$1"
        );
        text = text.replace(
            /__(.*?)__/g,
            "$1"
        );
        // Kursiv
        text = text.replace(
            /\*(.*?)\*/g,
            "$1"
        );
        text = text.replace(
            /_(.*?)_/g,
            "$1"
        );
        // Inline code
        text = text.replace(
            /`([^`]+)`/g,
            "$1"
        );
        // Markdown-rubriker
        text = text.replace(
            /^#{1,6}\s+/gm,
            ""
        );
        // Markdown-listor
        text = text.replace(
            /^\s*[-*+]\s+/gm,
            ""
        );
        // Blockquotes
        text = text.replace(
            /^\s*>\s?/gm,
            ""
        );
        // LaTeX $$...$$
        text = text.replace(
            /\$\$([\s\S]*?)\$\$/g,
            "$1"
        );
        // LaTeX $...$
        text = text.replace(
            /\$([^$\n]+)\$/g,
            "$1"
        );
        // Radbrytningar → mellanslag
        text = text.replace(
            /\s*\n\s*/g,
            " "
        );
        // Flera mellanslag → ett
        text = text.replace(
            /\s+/g,
            " "
        );
        text = text.trim();
        // Begränsa texten i frågetabellen
        const maxLength = 180;
        if (text.length > maxLength) {
            text = text.substring(0, maxLength).trimEnd() + "…";
        }
        target.textContent = text;
    });
}

function setupImageReferences() {
    const questionText = document.getElementById("questionText");

    if (!questionText) {
        return;
    }

    document
        .querySelectorAll(".insert-image-reference")
        .forEach(button => {
            button.addEventListener("click", () => {
                const mediaName = button.dataset.mediaName;

                if (!mediaName) {
                    return;
                }

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

function setupMediaEdit() {
    const modal = document.getElementById("editMediaModal");

    if (!modal) {
        return;
    }

    const form = document.getElementById("editMediaForm");
    const nameInput = document.getElementById("mediaName");
    const tagSelect = document.getElementById("mediaTags");

    modal.addEventListener("show.bs.modal", (event) => {
        const button = event.relatedTarget;

        if (!button) {
            return;
        }

        const mediaId = button.dataset.mediaId;
        const mediaName = button.dataset.mediaName;
        const mediaTags = button.dataset.mediaTags
            ? button.dataset.mediaTags.split(",")
            : [];

        console.log("Media tags:", mediaTags);
        console.log("Select options:", Array.from(tagSelect.options).map(option => ({
            value: option.value,
            text: option.text
        })));

        form.action = `/media/${mediaId}/edit`;
        nameInput.value = mediaName;

        const tomSelect = tagSelect.tomselect;

        if (tomSelect) {
            tomSelect.clear(true);
            tomSelect.setValue(mediaTags, true);
        } else {
            Array.from(tagSelect.options).forEach((option) => {
                option.selected = mediaTags.includes(option.value);
            });
        }
    });
}

function setupMediaSelection() {
    const questionText = document.getElementById("questionText");

    if (!questionText) {
        return;
    }

    document.addEventListener("click", (event) => {
        const button = event.target.closest(".media-select-btn");

        if (!button) {
            return;
        }

        const mediaName = button.dataset.mediaName;

        if (!mediaName) {
            return;
        }

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

// ===============================
// Question answer fields
// ===============================

function setupQuestionAnswerFields() {
    const questionType = document.getElementById("questionType");
    const answerFields = document.getElementById("answerFields");

    if (!questionType || !answerFields) {
        return;
    }

    const questionDataElement =
        document.getElementById("questionData");

    const questionData = questionDataElement
        ? JSON.parse(questionDataElement.textContent)
        : null;

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
            .addEventListener("click", () => {
                row.remove();
            });

        answerFields
            .querySelector("#textAnswerList")
            .appendChild(row);
    }

    function renderTextAnswers() {
        answerFields.innerHTML = `
            <label class="form-label">
                Rätt svar
            </label>

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
            .addEventListener("click", () => {
                addTextAnswer();
            });

        const answers =
            questionData?.expected_answer?.answers ?? [];

        if (answers.length > 0) {
            answers.forEach(answer => {
                addTextAnswer(answer);
            });
        } else {
            addTextAnswer();
        }
    }

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

    function renderBooleanAnswer() {
        const value =
            questionData?.expected_answer?.answer;

        answerFields.innerHTML = `
            <label class="form-label">
                Rätt svar
            </label>

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

    function renderSliderAnswer() {
        answerFields.innerHTML = `
            <div class="row g-3 mb-4">

                <div class="col-12">
                    <h6>Sliderinställningar</h6>
                </div>

                <div class="col-12 col-md-4">
                    <label
                        for="sliderMin"
                        class="form-label">
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
                    <label
                        for="sliderMax"
                        class="form-label">
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
                    <label
                        for="sliderStep"
                        class="form-label">
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

    function renderChoiceAnswers(multiple = false) {
        const answerType = multiple
            ? "checkbox"
            : "radio";

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
                <h6 class="mb-1">
                    ${title}
                </h6>

                <p class="text-muted mb-3">
                    ${helpText}
                </p>

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
            const rows = answerFields.querySelectorAll(
                ".choice-answer-row"
            );

            rows.forEach((row, index) => {
                const correctInput = row.querySelector(
                    "input[type='radio'], input[type='checkbox']"
                );

                correctInput.value = index;
            });
        }

        function addChoiceAnswer(
            value = "",
            isCorrect = false
        ) {
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
            .addEventListener("click", () => {
                addChoiceAnswer();
            });
        const choices =
            questionData?.choices ?? [];

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

    function renderFileUploadAnswer() {
        answerFields.innerHTML = `
            <div class="text-muted">
                Den här frågetypen har normalt inget
                automatiskt rätt svar. Eleven lämnar sitt
                svar genom att ladda upp en eller flera filer.
            </div>
        `;
    }

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

    questionType.addEventListener(
        "change",
        renderAnswerFields
    );

    renderAnswerFields();
}

function setupAssignmentStudents() {

const table = document.getElementById(
    "assignmentStudentsTable"
);

if (!table) {
    return;
}

const search = document.getElementById(
    "assignmentStudentSearch"
);

const group = document.getElementById(
    "assignmentStudentGroup"
);

const team = document.getElementById(
    "assignmentStudentTeam"
);

const selectAll = document.getElementById(
    "assignmentSelectAll"
);

const selectVisible = document.getElementById(
    "assignmentSelectVisible"
);

const studentCount = document.getElementById(
    "assignmentStudentCount"
);

const selectedStudentCount = document.getElementById(
    "assignmentSelectedStudentCount"
);


function getRows() {

    return [
        ...table.querySelectorAll(
            "tbody tr[data-assignment-student]"
        )
    ];

}


function getVisibleRows() {

    const searchText = search.value
        .trim()
        .toLowerCase();

    const groupId = group.value;
    const teamId = team.value;

    return getRows().filter(row => {

        const name = row.dataset.name || "";
        const rowGroup = row.dataset.group || "";

        const rowTeams = row.dataset.teams
            ? row.dataset.teams.split(",")
            : [];

        const matchesSearch =
            !searchText ||
            name.includes(searchText);

        const matchesGroup =
            !groupId ||
            rowGroup === groupId;

        const matchesTeam =
            !teamId ||
            rowTeams.includes(teamId);

        return (
            matchesSearch &&
            matchesGroup &&
            matchesTeam
        );

    });

}


function update() {

    const rows = getRows();
    const visibleRows = getVisibleRows();

    rows.forEach(row => {

        row.style.display =
            visibleRows.includes(row)
                ? ""
                : "none";

    });

    studentCount.textContent =
        visibleRows.length;

    const checkboxes = getRows()
        .map(row =>
            row.querySelector(
                ".student-checkbox"
            )
        )
        .filter(Boolean);

    const selected = checkboxes.filter(
        checkbox => checkbox.checked
    );

    selectedStudentCount.textContent =
        selected.length;

    const visibleCheckboxes =
        visibleRows
            .map(row =>
                row.querySelector(
                    ".student-checkbox"
                )
            )
            .filter(Boolean);

    const visibleSelected =
        visibleCheckboxes.filter(
            checkbox => checkbox.checked
        );

    selectAll.checked =
        visibleCheckboxes.length > 0 &&
        visibleSelected.length ===
            visibleCheckboxes.length;

    selectAll.indeterminate =
        visibleSelected.length > 0 &&
        visibleSelected.length <
            visibleCheckboxes.length;

}


search.addEventListener(
    "input",
    update
);

group.addEventListener(
    "change",
    update
);

team.addEventListener(
    "change",
    update
);


selectAll.addEventListener(
    "change",
    () => {

        getVisibleRows().forEach(row => {

            const checkbox =
                row.querySelector(
                    ".student-checkbox"
                );

            if (checkbox) {
                checkbox.checked =
                    selectAll.checked;
            }

        });

        update();

    }
);


selectVisible.addEventListener(
    "click",
    () => {

        getVisibleRows().forEach(row => {

            const checkbox =
                row.querySelector(
                    ".student-checkbox"
                );

            if (checkbox) {
                checkbox.checked = true;
            }

        });

        update();

    }
);


table.addEventListener(
    "change",
    event => {

        if (
            event.target.matches(
                ".student-checkbox"
            )
        ) {
            update();
        }

    }
);


update();

}

// ============================================================
// GE UPPGIFT TILL FLERA ELEVER SAMTIDIGT PÅ STUDENTSIDAN
// ============================================================
function setupStudentAssignmentButton() {
    const button = document.getElementById(
        "createAssignmentFromSelected"
    );

    if (!button) {
        return;
    }

    button.addEventListener("click", function () {
        const checkboxes = document.querySelectorAll(
            ".student-checkbox:checked"
        );

        if (checkboxes.length === 0) {
            alert("Markera minst en elev.");
            return;
        }

        const params = new URLSearchParams();

        checkboxes.forEach(function (checkbox) {
            params.append(
                "student_ids",
                checkbox.value
            );
        });

        window.location.href =
            `/assignments/new?${params.toString()}`;
    });
}

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

document.body.addEventListener("htmx:afterSwap", (event) => {
    initTomSelects(event.target);
});

document.body.addEventListener("htmx:afterSwap", (event) => {
    setupQuestionPlainText(event.detail.target);
    setupQuestionFullRender(event.detail.target);
});