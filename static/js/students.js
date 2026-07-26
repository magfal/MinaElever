let selectedTeams = [];
let allTeams = [];

function initStudentsManage() {
    if (!document.getElementById("studentTable")) {
        return;
    }
    initStudentTable();
    initStudentModal();
    initStudentActions();
    initStudentSorting()
    initAddTeam();
}

function initStudentTable() {
    rememberSelectedStudents("studentsIds");
    setupSelectAll(
        "selectAll",
        "studentsIds",
        "studentTable"
    );
    rememberInput("studentSearch");
    rememberInput("groupFilter");
    setupTableFilter({
        tableId: "studentTable",
        searchId: "studentSearch",
        filters: [
            {
                id: "groupFilter",
                data: "group"
            }
        ]
    });
}

function initStudentModal() {

    document
    .querySelectorAll(".edit-student-btn")
    .forEach(button => {

        button.addEventListener(
            "click",
            function(){

                document.getElementById("studentId").value =
                    this.dataset.id;

                document.getElementById("studentName").value =
                    this.dataset.name;

                document.getElementById("studentGroup").value =
                    this.dataset.groupId;

                document.getElementById("accessCode").value =
                    this.dataset.code;


                selectedTeams =
                    JSON.parse(
                        this.dataset.teams || "[]"
                    );


                renderStudentTeams();
                updateAvailableTeams();

            }
        );

    });
}

function updateAvailableTeams(){

    const select =
        document.getElementById("availableTeams");


    [...select.options].forEach(option => {

        if(!option.value) return;


        const exists =
            selectedTeams.some(
                team => team.id == option.value
            );


        option.hidden = exists;

    });

}

function initStudentActions() {
    initChangeName();
    initChangeGroup();
    initGenerateCode();
    initChangeCode();
    initLogoutStudent();
}

function initChangeName() {
    const button =
        document.getElementById("changeStudentNameBtn");
    if (!button) return;
    button.addEventListener(
        "click",
        () => {
            fetch("/students/change_name", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    student_id:
                        document.getElementById("studentId").value,

                    name:
                        document.getElementById("studentName").value
                })
            })
            .then(response => {

                if (response.ok) {
                    location.reload();
                }
            });
        }
    );
}

function initChangeGroup() {
    const button =
        document.getElementById("changeStudentGroupBtn");
    if (!button) return;
    button.addEventListener(
        "click",
        function () {
            fetch("/students/change_group", {
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify({
                    student_id:
                        document.getElementById("studentId").value,

                    group_id:
                        document.getElementById("studentGroup").value
                })
            })
            .then(response => response.json())
            .then(data => {
                if(data.success){
                    const modalElement =
                        document.getElementById("studentModal");
                    const modal =
                        bootstrap.Modal.getInstance(modalElement);
                    modal.hide();
                    setTimeout(() => {
                        location.reload();
                    }, 150);
                }
            });
        }
    );
}

function initGenerateCode() {
    const button =
        document.getElementById("generateCodeBtn");
    if (!button) return;
    const studentTable =
        document.getElementById("studentTable");
    if (!studentTable) return;
    const newCodeUrl =
        studentTable.dataset.newCodeUrl;
    button.addEventListener(
        "click",
        () => {
            const studentId =
                document.getElementById("studentId").value;
            generateNewCode(newCodeUrl);
        }
    );
}

async function generateNewCode(url){
    const response =
        await fetch(url);
    const data =
        await response.json();
    document.getElementById("accessCode").value =
        data.code;
}

function initChangeCode() {
    const button =
        document.getElementById("changeCodeBtn");
    if (!button) return;
    button.addEventListener(
        "click",
        () => {
            fetch("/students/change_code", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    student_id:
                        document.getElementById("studentId").value,
                    name:
                        document.getElementById("studentName").value,
                    access_code:
                        document.getElementById("accessCode").value
                })
            })
            .then(response => {
                if (response.ok) {
                    location.reload();
                }
            });
        }
    );
}

function renderStudentTeams(){

    const container =
        document.getElementById("studentTeams");


    container.innerHTML = "";


    selectedTeams.forEach(team => {


        const badge =
            document.createElement("span");


        badge.className =
            "badge border border-primary text-primary me-2";


        badge.innerHTML =
            `${team.name}
            <button 
            type="button"
            class="btn-close ms-2">
            </button>`;


        badge
        .querySelector("button")
        .onclick = () => {


            const studentId =
                document.getElementById(
                    "studentId"
                ).value;


            fetch("/students/remove_team", {

                method:"POST",

                headers:{
                    "Content-Type":"application/json"
                },

                body:JSON.stringify({

                    student_id: studentId,
                    team_id: team.id

                })

            })

            .then(response => response.json())

            .then(data => {


                if(data.success){


                    selectedTeams =
                        selectedTeams.filter(
                            t => t.id !== team.id
                        );


                    renderStudentTeams();
                    updateAvailableTeams();

                }

            });

        };


        container.appendChild(badge);

    });

}

function initLogoutStudent() {
    const button =
        document.getElementById("studentLogout");
    if (!button) return;
    const studentTable =
    document.getElementById("studentTable");
    if (!studentTable) return;
    const logoutUrl =
        studentTable.dataset.logoutUrl;
    button.addEventListener(
        "click",
        () => {
            const studentId =
                document.getElementById("studentId").value;
            logoutStudent(
                studentId,
                logoutUrl
            );
        }
    );
}

async function logoutStudent(studentId, url){
    const response =
        await fetch(
            url.replace("0", studentId),
            {
                method:"POST"
            }
        );
    const data =
        await response.json();
    const box =
        document.getElementById("studentMessage");
    box.textContent =
        data.message;
    box.classList.remove("d-none");
}

function initStudentSorting(){
    document.querySelectorAll(".sortable").forEach(header => {
        header.addEventListener("click", () => {
            const table = header.closest("table");
            const tbody = table.querySelector("tbody");
            const rows = Array.from(tbody.querySelectorAll("tr"));
            const index = Array.from(header.parentNode.children)
                .indexOf(header);
            const ascending = header.dataset.order !== "asc";
            rows.sort((a, b) => {
                const aText = a.children[index].innerText.toLowerCase();
                const bText = b.children[index].innerText.toLowerCase();
                return ascending
                    ? aText.localeCompare(bText)
                    : bText.localeCompare(aText);
            });
            rows.forEach(row => tbody.appendChild(row));
            header.dataset.order = ascending ? "asc" : "desc";
        });
    });
}

function initAddTeam(){

    const button =
        document.getElementById("addTeamBtn");

    if(!button) return;


    button.addEventListener(
        "click",
        ()=>{

            const select =
                document.getElementById(
                    "availableTeams"
                );


            const teamId =
                select.value;


            const teamName =
                select.options[
                    select.selectedIndex
                ].text;


            const studentId =
                document.getElementById(
                    "studentId"
                ).value;


            if(!teamId) return;

            if (
                selectedTeams.some(
                team => Number(team.id) === Number(teamId)
                )
            ) {
                return;
            }

            fetch("/students/add_team", {

                method:"POST",

                headers:{
                    "Content-Type":"application/json"
                },

                body:JSON.stringify({

                    student_id: studentId,
                    team_id: teamId

                })

            })

            .then(response => response.json())

            .then(data => {

                if(data.success){

                    location.reload();

                }

            });;

        }
    );
}