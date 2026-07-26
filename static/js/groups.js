function initGroupsManage() {
    if (!document.getElementById("manageGroups")) {
        return;
    }

const editModal =
    document.getElementById(
        "editSelectedModal"
    );

if (editModal) {

    editModal.addEventListener(
        "show.bs.modal",
        function () {
            const selected =
                document.querySelectorAll(
                    'input[name="students_ids"]:checked'
                );

            document.getElementById(
                "selected-count"
            ).textContent =
                selected.length;

            const container =
                document.getElementById(
                    "selected-container"
                );

            container.innerHTML = "";
            selected.forEach(student => {
                container.insertAdjacentHTML(
                    "beforeend",
                    `
                    <input 
                        type="hidden"
                        name="students_ids"
                        value="${student.value}">
                    `
                );
            });
        }
    );
}




// =================================
// Group management (hur kopplar koden nedan till raderna ova???
// =================================

function editGroup(id, name, isActive, next) {
    document.getElementById("groupForm").action = "/groups/edit_group";
    document.getElementById("groupModalTitle").innerText = "Ändra klass";
    document.getElementById("groupNext").value = next;
    document.getElementById("groupId").value = id;
    document.getElementById("groupName").value = name;
    document.getElementById("groupArchived").checked = !isActive;
}

let studentChanged = false;


document.querySelectorAll(".group-select").forEach(select => {

    select.addEventListener("change", async function(){

        const studentId = this.dataset.studentId;

        await fetch(
            `/students/change_group/${studentId}`,
            {
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify({
                    group_id:this.value
                })
            }
        );

        studentChanged=true;

    });

});

document.getElementById("newGroupBtn")
    .addEventListener("click", function () {
        newGroup(
            this.dataset.next
        );
    });

function newGroup(next) {
    document.getElementById("groupForm").action = "/groups/create_group";
    document.getElementById("groupModalTitle").innerText = "Ny klass";
    document.getElementById("groupNext").value = next;
    document.getElementById("groupId").value = "";
    document.getElementById("groupName").value = "";
    document.getElementById("groupArchived").checked = false;
}

document.querySelectorAll(".edit-group-btn").forEach(button => {
    button.addEventListener("click", function () {
        editGroup(
            this.dataset.id,
            this.dataset.name,
            JSON.parse(this.dataset.active),
            this.dataset.next
        );
    });
});

function editGroup(id, name, isActive, next) {
    document.getElementById("groupForm").action = "/groups/edit_group";
    document.getElementById("groupModalTitle").innerText = "Ändra klass";
    document.getElementById("groupNext").value = next;
    document.getElementById("groupId").value = id;
    document.getElementById("groupName").value = name;
    document.getElementById("groupArchived").checked = !isActive;
}

document.getElementById("newTeamBtn").addEventListener("click", function () {
    newTeam(
        this.dataset.next
    );
});

function newTeam(next){
    document.getElementById("teamForm").action = "/groups/create_team";
    document.getElementById("teamModalTitle").innerText = "Ny grupp";
    document.getElementById("teamNext").value = next;
    document.getElementById("teamId").value="";
    document.getElementById("teamName").value="";
    document.getElementById("teamDescription").value="";
}

document.querySelectorAll(".edit-team-btn").forEach(button => {
    button.addEventListener("click", function () {
        editTeam(
            this.dataset.id,
            this.dataset.name,
            this.dataset.description,
            this.dataset.next
        );
    });
});

function editTeam(id, name, description, next) {
    document.getElementById("teamForm").action = "/groups/edit_team";
    document.getElementById("teamModalTitle").innerText = "Ändra grupp";
    document.getElementById("teamNext").value = next;
    document.getElementById("teamId").value = id;
    document.getElementById("teamName").value = name;
    document.getElementById("teamDescription").value = description;
}}
