
// ============================================================
// TOM SELECT
// ============================================================

function initTomSelects(root = document) {
    initCreateTomSelects(root);
    initFilterTomSelects(root);
}

function getElements(root, selector) {
    const elements = [];

    if (root instanceof Element && root.matches(selector)) {
        elements.push(root);
    }

    elements.push(...root.querySelectorAll(selector));

    return elements;
}


// ------------------------------------------------------------
// TomSelect: skapa nya värden
// ------------------------------------------------------------

function initCreateTomSelects(root) {
    getElements(root, ".tomselect-create").forEach(select => {
        if (select.tomselect) return;

        const tom = new TomSelect(select, {
            create: true,
            createOnBlur: true,
            persist: false,
            dropdownParent: "body"
        });

        const button = select
            .closest(".input-group")
            ?.querySelector(".add-tomselect-btn");

        if (!button) return;

        tom.control_input.addEventListener("keydown", event => {
            if (event.key !== "Enter") return;

            event.preventDefault();
            event.stopPropagation();

            select.dispatchEvent(
                new Event("change", { bubbles: true })
            );

            button.click();
        });
    });
}


// ------------------------------------------------------------
// TomSelect: filtrering / befintliga värden
// ------------------------------------------------------------

function initFilterTomSelects(root) {
    getElements(root, ".tomselect-filter").forEach(select => {
        if (select.tomselect) return;

        const tom = new TomSelect(select, {
            create: false,
            allowEmptyOption: true,
            dropdownParent:
                ["questionTags", "mediaTags"].includes(select.id)
                    ? "body"
                    : undefined
        });

        if (select.id === "questionTags") {
            initTagSelect(tom, "question");
        }

        if (select.id === "mediaTags") {
            initTagSelect(tom, "media");
        }
    });
}


// ============================================================
// TAGGHANTERING
// ============================================================

const tagStyles = {
    SUBJECT: "text-bg-primary",
    AREA: "text-bg-secondary",
    DECK: "text-bg-info",
    OTHER: "text-bg-dark"
};

function initTagSelect(tom, type) {
    const prefix = type === "media" ? "media" : "question";

    const badges = document.querySelector(`#${prefix}TagBadges`);
    const button = document.querySelector(`#add${capitalize(prefix)}TagBtn`);

    if (!badges || !button) return;

    const removeClass = `${prefix}-tag-remove`;
    const modalContent = `#${prefix}TagModalContent`;

    function getOption(id) {
        const option = tom.options[String(id)];

        if (!option) return null;

        const original = tom.input.querySelector(
            `option[value="${CSS.escape(String(id))}"]`
        );

        if (original) {
            option.tag_type = original.dataset.tagType;
        }

        return option;
    }

    function addBadge(id) {
        id = String(id);

        if (badges.querySelector(`[data-tag-id="${CSS.escape(id)}"]`)) {
            return;
        }

        const option = getOption(id);
        if (!option) return;

        const badge = document.createElement("span");
        badge.className = `badge me-1 ${tagStyles[option.tag_type] || "text-bg-light"}`;
        badge.dataset.tagId = id;

        const label = document.createTextNode(option.text.trim());

        const removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className =
            `btn-close btn-close-white ms-1 ${removeClass}`;
        removeButton.setAttribute(
            "aria-label",
            `Ta bort taggen ${option.text.trim()}`
        );
        removeButton.dataset.tagId = id;

        badge.append(label, removeButton);
        badges.appendChild(badge);
    }

    function removeBadge(id) {
        badges
            .querySelector(`[data-tag-id="${CSS.escape(String(id))}"]`)
            ?.remove();
    }

    tom.on("item_add", addBadge);
    tom.on("item_remove", removeBadge);

    badges.addEventListener("click", event => {
        const removeButton = event.target.closest(`.${removeClass}`);
        if (!removeButton) return;

        tom.removeItem(removeButton.dataset.tagId);
    });

    function updateAddButton() {
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

    updateAddButton();

    tom.control_input.addEventListener("input", updateAddButton);
    tom.on("dropdown_open", updateAddButton);

    let tagName = "";

    button.addEventListener("mousedown", () => {
        tagName = tom.control_input.value.trim();
    });

    button.onclick = () => {
        if (!tagName) return;

        const url = new URL(button.dataset.url, window.location.origin);
        url.searchParams.set("name", tagName);

        htmx.ajax("GET", url.toString(), {
            target: modalContent,
            swap: "innerHTML"
        });
    };
}

function capitalize(value) {
    return value.charAt(0).toUpperCase() + value.slice(1);
}


// ============================================================
// SKAPA NY TAGG
// ============================================================

function handleCreatedTag(event, type) {
    const data = event.detail;
    const prefix = type === "media" ? "media" : "question";

    const select = document.querySelector(`#${prefix}Tags`);

    if (!select?.tomselect) return;

    const tom = select.tomselect;
    const id = String(data.id);

    tom.addOption({
        value: id,
        text: data.name
    });

    tom.options[id].tag_type = data.tag_type;

    tom.addItem(id);
    tom.refreshOptions(false);

    const modal = document.getElementById(`${prefix}TagModal`);

    if (modal) {
        bootstrap.Modal.getOrCreateInstance(modal).hide();
    }
}

document.body.addEventListener("media-tag-created", event => {
    handleCreatedTag(event, "media");
});

document.body.addEventListener("question-tag-created", event => {
    handleCreatedTag(event, "question");
});


// ============================================================
// MEDIAREDIGERING
// ============================================================

function setupMediaEdit() {
    const modal = document.getElementById("editMediaModal");

    if (!modal || modal.dataset.initialized) return;

    modal.dataset.initialized = "true";

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
        nameInput.value = mediaName || "";

        const tom = tagSelect?.tomselect;
        if (!tom) return;

        tom.clear(true);
        tom.setValue(mediaTags);
    });
}


// ============================================================
// HTMX: VISA TAGG-MODALER
// ============================================================

function showTagModal(targetId, modalId) {
    const modalContent = document.getElementById(targetId);

    if (!modalContent) return;

    const modal = document.getElementById(modalId);

    if (modal) {
        bootstrap.Modal.getOrCreateInstance(modal).show();
    }
}


// ============================================================
// FRÅGOR
// ============================================================

// ------------------------------------------------------------
// Frågepreview
// ------------------------------------------------------------

function setupQuestionPreview() {
    const textarea = document.getElementById("questionText");
    const preview = document.getElementById("questionPreview");

    if (!textarea || !preview || textarea.dataset.previewInitialized) {
        return;
    }

    textarea.dataset.previewInitialized = "true";

    function updatePreview() {
        if (window.MathJax?.typesetClear) {
            MathJax.typesetClear([preview]);
        }

        let html = marked.parse(textarea.value);

        html = replaceMediaReferences(html);

        preview.innerHTML = DOMPurify.sanitize(html);

        if (window.MathJax?.typesetPromise) {
            MathJax.typesetPromise([preview]);
        }
    }

    textarea.addEventListener("input", updatePreview);
    updatePreview();
}


// ------------------------------------------------------------
// Ersätt bildreferenser
// ------------------------------------------------------------

function replaceMediaReferences(html) {
    return html.replace(
        /\[([^\[\]:]+)(?::(\d+))?\]/g,
        (match, mediaName, size) => {
            const mediaId = mediaMap[mediaName];

            if (!mediaId) return match;

            const width = size ? `${size}%` : "100%";

            return `<img
                src="/media/file/${mediaId}"
                class="question-image my-2"
                style="width: ${width};"
                alt="${escapeHTML(mediaName)}">`;
        }
    );
}

function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}


// ------------------------------------------------------------
// Full rendering av frågor
// ------------------------------------------------------------

function setupQuestionFullRender(container = document) {
    getElements(container, ".question-rendered").forEach(rendered => {
        const cell = rendered.closest(".question-cell");
        const source = cell?.querySelector(".question-source");

        if (!source) return;

        let html = marked.parse(source.value);
        html = replaceMediaReferences(html);

        rendered.innerHTML = DOMPurify.sanitize(html);

        if (window.MathJax?.typesetPromise) {
            MathJax.typesetPromise([rendered]);
        }
    });
}


// ------------------------------------------------------------
// Ren text för frågetabellen
// ------------------------------------------------------------

function setupQuestionPlainText(container = document) {
    getElements(container, ".question-cell").forEach(cell => {
        const source = cell.querySelector(".question-source");
        const target = cell.querySelector(".question-table-text");

        if (!source || !target) return;

        let text = source.value;

        text = text.replace(/\[([^\[\]:]+)(?::(\d+))?\]/g, "[$1]");
        text = text.replace(/!\[[^\]]*\]\([^)]*\)/g, "[bild]");
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

function insertImageReference(questionText, mediaName) {
    if (!questionText || !mediaName) return;

    const reference = `[${mediaName}]`;
    const start = questionText.selectionStart;
    const end = questionText.selectionEnd;

    questionText.value =
        questionText.value.slice(0, start) +
        reference +
        questionText.value.slice(end);

    const cursorPosition = start + reference.length;

    questionText.focus();
    questionText.setSelectionRange(cursorPosition, cursorPosition);

    questionText.dispatchEvent(
        new Event("input", { bubbles: true })
    );
}

function setupImageReferences() {
    document.addEventListener("click", event => {
        const button = event.target.closest(".insert-image-reference");

        if (!button) return;

        insertImageReference(
            document.getElementById("questionText"),
            button.dataset.mediaName
        );
    });
}

function setupMediaSelection() {
    document.addEventListener("click", event => {
        const button = event.target.closest(".media-select-btn");

        if (!button) return;

        insertImageReference(
            document.getElementById("questionText"),
            button.dataset.mediaName
        );
    });
}


// ============================================================
// FRÅGETYPER OCH SVARSFÄLT
// ============================================================

function setupQuestionAnswerFields() {
    const questionType = document.getElementById("questionType");
    const answerFields = document.getElementById("answerFields");

    if (!questionType || !answerFields ||
        questionType.dataset.initialized) {
        return;
    }

    questionType.dataset.initialized = "true";

    const dataElement = document.getElementById("questionData");

    const questionData = dataElement
        ? JSON.parse(dataElement.textContent)
        : null;

    function addTextAnswer(value = "") {
        const row = document.createElement("div");
        row.className = "input-group mb-2";

        const input = document.createElement("input");
        input.type = "text";
        input.name = "correct_answers";
        input.className = "form-control";
        input.value = value;
        input.placeholder = "Rätt svar";

        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-outline-danger remove-answer";
        button.textContent = "Ta bort";

        button.addEventListener("click", () => row.remove());

        row.append(input, button);
        answerFields.querySelector("#textAnswerList").appendChild(row);
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

        document.getElementById("addTextAnswer")
            .addEventListener("click", () => addTextAnswer());

        const answers = questionData?.expected_answer?.answers ?? [];

        if (answers.length) {
            answers.forEach(addTextAnswer);
        } else {
            addTextAnswer();
        }
    }

    function renderNumberAnswer() {
        const value = questionData?.expected_answer?.answer ?? "";

        answerFields.innerHTML = `
            <div class="row g-3">
                <div class="col-12 col-md-6">
                    <label for="correctNumber" class="form-label">
                        Rätt svar
                    </label>
                    <input
                        id="correctNumber"
                        type="number"
                        step="any"
                        name="correct_number"
                        class="form-control"
                        value="${escapeHTML(value)}">
                </div>
            </div>
        `;
    }

    function renderBooleanAnswer() {
        const value = questionData?.expected_answer?.answer;

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
                <label class="form-check-label" for="correctTrue">
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
                <label class="form-check-label" for="correctFalse">
                    Falskt
                </label>
            </div>
        `;
    }

    function renderDateAnswer() {
        const value = questionData?.expected_answer?.answer ?? "";

        answerFields.innerHTML = `
            <div class="col-12 col-md-6">
                <label for="correctDate" class="form-label">
                    Rätt datum
                </label>
                <input
                    id="correctDate"
                    type="date"
                    name="correct_date"
                    class="form-control"
                    value="${escapeHTML(value)}">
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
                    <label for="sliderMin" class="form-label">Minvärde</label>
                    <input
                        id="sliderMin"
                        type="number"
                        name="slider_min"
                        class="form-control"
                        value="0">
                </div>
                <div class="col-12 col-md-4">
                    <label for="sliderMax" class="form-label">Maxvärde</label>
                    <input
                        id="sliderMax"
                        type="number"
                        name="slider_max"
                        class="form-control"
                        value="100">
                </div>
                <div class="col-12 col-md-4">
                    <label for="sliderStep" class="form-label">Steg</label>
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
                    <label for="correctSliderValue" class="form-label">
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

        const list = document.getElementById("choiceAnswerList");

        function updateChoiceIndexes() {
            list.querySelectorAll(".choice-answer-row")
                .forEach((row, index) => {
                    const input = row.querySelector(
                        "input[type='radio'], input[type='checkbox']"
                    );

                    input.value = index;
                });
        }

        function addChoiceAnswer(value = "", isCorrect = false) {
            const row = document.createElement("div");
            row.className = "input-group mb-2 choice-answer-row";

            const wrapper = document.createElement("div");
            wrapper.className = "input-group-text";

            const correctInput = document.createElement("input");
            correctInput.className = "form-check-input mt-0";
            correctInput.type = answerType;
            correctInput.name = correctName;
            correctInput.setAttribute("aria-label", "Rätt svar");
            correctInput.checked = isCorrect;

            wrapper.appendChild(correctInput);

            const textInput = document.createElement("input");
            textInput.type = "text";
            textInput.name = "choice_options";
            textInput.className = "form-control";
            textInput.value = value;
            textInput.placeholder = "Svarsalternativ";

            const removeButton = document.createElement("button");
            removeButton.type = "button";
            removeButton.className =
                "btn btn-outline-danger remove-choice";
            removeButton.textContent = "Ta bort";

            removeButton.addEventListener("click", () => {
                row.remove();
                updateChoiceIndexes();
            });

            row.append(wrapper, textInput, removeButton);
            list.appendChild(row);

            updateChoiceIndexes();
        }

        document.getElementById("addChoiceAnswer")
            .addEventListener("click", () => addChoiceAnswer());

        const choices = questionData?.choices ?? [];

        if (choices.length) {
            choices.forEach(choice => {
                addChoiceAnswer(choice.text, choice.is_correct);
            });
        } else {
            addChoiceAnswer();
            addChoiceAnswer();
        }
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
        const renderers = {
            TEXT: renderTextAnswers,
            NUMBER: renderNumberAnswer,
            BOOLEAN: renderBooleanAnswer,
            DATE: renderDateAnswer,
            SLIDER: renderSliderAnswer,
            SINGLE_CHOICE: () => renderChoiceAnswers(false),
            MULTIPLE_CHOICE: () => renderChoiceAnswers(true),
            FILE_UPLOAD: renderFileUploadAnswer
        };

        answerFields.innerHTML = "";

        renderers[questionType.value]?.();
    }

    questionType.addEventListener("change", renderAnswerFields);
    renderAnswerFields();
}


// ============================================================
// UPPGIFTER
// ============================================================

function setupAssignmentStudents() {
    const table = document.getElementById("assignmentStudentsTable");

    if (!table || table.dataset.initialized) return;

    table.dataset.initialized = "true";

    const search = document.getElementById("assignmentStudentSearch");
    const group = document.getElementById("assignmentStudentGroup");
    const team = document.getElementById("assignmentStudentTeam");
    const selectAll = document.getElementById("assignmentSelectAll");
    const selectVisible = document.getElementById("assignmentSelectVisible");
    const studentCount = document.getElementById("assignmentStudentCount");
    const selectedStudentCount =
        document.getElementById("assignmentSelectedStudentCount");

    if (!search || !group || !team || !selectAll ||
        !selectVisible || !studentCount || !selectedStudentCount) {
        return;
    }

    function getRows() {
        return [
            ...table.querySelectorAll("tbody tr[data-assignment-student]")
        ];
    }

    function getVisibleRows() {
        const searchText = search.value.trim().toLowerCase();
        const groupId = group.value;
        const teamId = team.value;

        return getRows().filter(row => {
            const name = (row.dataset.name || "").toLowerCase();
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
            row.style.display = visibleRows.includes(row) ? "" : "none";
        });

        studentCount.textContent = visibleRows.length;

        const checkboxes = rows
            .map(row => row.querySelector(".student-checkbox"))
            .filter(Boolean);

        selectedStudentCount.textContent =
            checkboxes.filter(cb => cb.checked).length;

        const visibleCheckboxes = visibleRows
            .map(row => row.querySelector(".student-checkbox"))
            .filter(Boolean);

        const visibleSelected =
            visibleCheckboxes.filter(cb => cb.checked);

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
            const checkbox = row.querySelector(".student-checkbox");

            if (checkbox) {
                checkbox.checked = selectAll.checked;
            }
        });

        update();
    });

    selectVisible.addEventListener("click", () => {
        getVisibleRows().forEach(row => {
            const checkbox = row.querySelector(".student-checkbox");

            if (checkbox) checkbox.checked = true;
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

function setupStudentAssignmentButton() {
    const button = document.getElementById("createAssignmentFromSelected");

    if (!button || button.dataset.initialized) return;

    button.dataset.initialized = "true";

    button.addEventListener("click", () => {
        const checkboxes =
            document.querySelectorAll(".student-checkbox:checked");

        if (!checkboxes.length) {
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

        bootstrap.Modal.getInstance(modalElement)?.hide();
    });
}


// ============================================================
// TOASTS OCH ALERTS
// ============================================================

// HTMX skickar showToast. Alpine tar emot toast-eventet.
document.body.addEventListener("showToast", event => {
    window.dispatchEvent(
        new CustomEvent("toast", {
            detail: event.detail
        })
    );
});

function setupBootstrapToasts() {
    document.querySelectorAll(".toast").forEach(toastElement => {
        bootstrap.Toast.getOrCreateInstance(toastElement).show();
    });
}

function setupAutoDismissAlerts() {
    document.querySelectorAll(".alert[data-auto-dismiss]").forEach(alert => {
        setTimeout(() => alert.remove(), 4000);
    });
}


// ============================================================
// TABELLSORTERING
// ============================================================

document.addEventListener("click", event => {
    const header = event.target.closest(".sortable");

    if (!header) return;

    const table = header.closest("table");
    const tbody = table?.tBodies[0];

    if (!tbody) return;

    const rows = Array.from(tbody.rows);
    const column = header.cellIndex;
    const ascending = header.dataset.sort !== "asc";

    header.dataset.sort = ascending ? "asc" : "desc";

    table.querySelectorAll(".sortable").forEach(th => {
        if (th !== header) delete th.dataset.sort;
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
        const aValue = a.cells[column]?.textContent.trim() || "";
        const bValue = b.cells[column]?.textContent.trim() || "";

        return ascending
            ? aValue.localeCompare(bValue, "sv")
            : bValue.localeCompare(aValue, "sv");
    });

    rows.forEach(row => tbody.appendChild(row));
});


// ============================================================
// HTMX-EVENT
// ============================================================

document.body.addEventListener("htmx:afterSwap", event => {
    const target = event.detail.target;

    if (!target) return;

    initTomSelects(target);

    setupQuestionPlainText(target);
    setupQuestionFullRender(target);

    if (target.id === "mediaTagModalContent") {
        showTagModal("mediaTagModalContent", "mediaTagModal");
    }

    if (target.id === "questionTagModalContent") {
        showTagModal("questionTagModalContent", "questionTagModal");
    }
});


// ============================================================
// MODAL: RENSNING
// ============================================================

document.addEventListener("hidden.bs.modal", event => {
    if (event.target.id !== "studentModal") return;

    const content = document.getElementById("studentModalContent");

    if (content) {
        content.innerHTML = "";
    }
});


// ============================================================
// INITIERING
// ============================================================

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
