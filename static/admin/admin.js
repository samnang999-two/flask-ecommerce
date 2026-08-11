/* ==========================================
   Admin Dashboard JavaScript
========================================== */

document.addEventListener("DOMContentLoaded", function () {
    console.log("Admin Dashboard Loaded");

    /* ===========================
        Sidebar Toggle
    =========================== */
    const toggle = document.getElementById("sidebarToggle");
    const sidebar = document.querySelector(".sidebar");
    const main = document.querySelector(".main-wrapper");

    if (toggle) {
        toggle.addEventListener("click", function () {
            sidebar.classList.toggle("sidebar-hide");
            main.classList.toggle("main-expand");
        });
    }

    /* ===========================
        Active Menu
    =========================== */
    const currentUrl = window.location.href;
    document.querySelectorAll(".sidebar-menu a").forEach(link => {
        if (link.href === currentUrl) {
            link.classList.add("active");
        }
    });

    /* ===========================
        Tooltips
    =========================== */
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
});

/* ==========================================
    SweetAlert Delete
========================================== */
function deleteConfirm() {
    Swal.fire({
        title: "Delete this record?",
        text: "You won't be able to recover it.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#4f46e5",
        cancelButtonColor: "#ef4444",
        confirmButtonText: "Yes, Delete",
        cancelButtonText: "Cancel"
    }).then((result) => {
        if (result.isConfirmed) {
            Swal.fire({
                icon: "success",
                title: "Deleted!",
                text: "Demo UI only.",
                timer: 1500,
                showConfirmButton: false
            });
        }
    });
}

/* ==========================================
    Success Toast
========================================== */
function successToast(message) {
    Swal.fire({
        toast: true,
        icon: "success",
        title: message,
        position: "top-end",
        timer: 2500,
        showConfirmButton: false
    });
}

/* ==========================================
    Error Toast
========================================== */
function errorToast(message) {
    Swal.fire({
        toast: true,
        icon: "error",
        title: message,
        position: "top-end",
        timer: 2500,
        showConfirmButton: false
    });
}

/* ==========================================
    Loading
========================================== */
function loading() {
    Swal.fire({
        title: "Loading...",
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
}

/* ==========================================
    Close Loading
========================================== */
function closeLoading() {
    Swal.close();
}

/* ==========================================
    Sales Chart (Chart.js)
========================================== */
const canvas = document.getElementById("salesChart");

if (canvas) {
    const ctx = canvas.getContext("2d");

    new Chart(ctx, {
        type: "line",
        data: {
            labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"],
            datasets: [{
                label: "Sales",
                data: [1200, 1800, 1600, 2200, 2600, 3000, 3400],
                borderColor: "#4F46E5",
                backgroundColor: "rgba(79,70,229,.15)",
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}