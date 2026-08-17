/* Student PMS — UI interactions */
(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {

        /* ---- Sidebar collapse toggle ---- */
        var sidebar = document.getElementById("appSidebar");
        var toggle = document.getElementById("sidebarToggle");
        var body = document.body;
        if (sidebar && toggle) {
            if (localStorage.getItem("sidebar-collapsed") === "true") {
                body.classList.add("sidebar-collapsed");
            }
            toggle.addEventListener("click", function () {
                body.classList.toggle("sidebar-collapsed");
                localStorage.setItem("sidebar-collapsed", body.classList.contains("sidebar-collapsed"));
                var tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
                tooltips.forEach(function (el) {
                    var instance = bootstrap.Tooltip.getInstance(el);
                    if (instance) instance.dispose();
                });
                if (body.classList.contains("sidebar-collapsed")) {
                    initTooltips();
                }
            });
        }

        function initTooltips() {
            if (!body.classList.contains("sidebar-collapsed")) return;
            var els = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            els.forEach(function (el) {
                if (!bootstrap.Tooltip.getInstance(el)) {
                    new bootstrap.Tooltip(el, { trigger: "hover", delay: { show: 400, hide: 100 } });
                }
            });
        }
        initTooltips();

        /* ---- Button ripple effect ---- */
        var buttons = document.querySelectorAll(".btn:not(.btn-link)");
        for (var i = 0; i < buttons.length; i++) {
            buttons[i].addEventListener("click", function (e) {
                var rippleEl = this.querySelector(".ripple");
                if (rippleEl) rippleEl.remove();

                var rect = this.getBoundingClientRect();
                var size = Math.max(rect.width, rect.height) * 2;
                var ripple = document.createElement("span");
                ripple.className = "ripple";
                ripple.style.width = size + "px";
                ripple.style.height = size + "px";
                ripple.style.left = e.clientX - rect.left - size / 2 + "px";
                ripple.style.top = e.clientY - rect.top - size / 2 + "px";

                var light = this.classList.contains("btn-primary") ||
                            this.classList.contains("btn-danger") ||
                            this.classList.contains("btn-success") ||
                            this.classList.contains("btn-warning") ||
                            this.classList.contains("btn-info") ||
                            this.classList.contains("btn-dark");
                ripple.style.background = light ? "rgba(255, 255, 255, .45)" : "rgba(16, 24, 40, .15)";
                this.appendChild(ripple);

                var self = this;
                window.setTimeout(function () {
                    var r = self.querySelector(".ripple");
                    if (r) r.remove();
                }, 650);
            });
        }

        /* ---- Scroll reveal ---- */
        function setupReveal(selector, stagger) {
            var els = document.querySelectorAll(selector);
            if (!els.length) return;

            if (!("IntersectionObserver" in window)) {
                for (var i = 0; i < els.length; i++) els[i].classList.add("revealed");
                return;
            }

            if (stagger) {
                for (var j = 0; j < els.length; j++) {
                    els[j].style.transitionDelay = j * 70 + "ms";
                }
            }

            var observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("revealed");
                        entry.target.style.transitionDelay = "0s";
                        observer.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.12 });

            for (var k = 0; k < els.length; k++) observer.observe(els[k]);
        }

        setupReveal(".reveal");
        setupReveal(".stat-card", true);
        setupReveal(".feature-card", true);
    });
})();
