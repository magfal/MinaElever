// =================================
// Starta JavaScript när sidan laddats
// =================================

//document.addEventListener("DOMContentLoaded", () => {
//   initGroupsManage();
//    initQuestionsPage();
//});

console.log("init.js laddad");

document.addEventListener("DOMContentLoaded", () => {
    initToasts();
    if (typeof initStudentsManage === "function") {
        initStudentsManage();
    }
    if (typeof initGroupsManage === "function") {
        initGroupsManage();
    }
    if (typeof initQuestionsPage === "function") {
        initQuestionsPage();
    }
    if (typeof initTemplatesPage === "function") {
        initTemplatesPage();
    }
    if (typeof initStatisticsPage === "function") {
        initStatisticsPage();
    }
});