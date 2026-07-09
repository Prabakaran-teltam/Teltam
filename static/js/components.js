// Teltam AI - Reusable Header and Footer Injector

document.addEventListener("DOMContentLoaded", () => {
    // 1. Inject Header
    const headerElement = document.getElementById("global-header");
    if (headerElement) {
        const isAuthenticated = headerElement.getAttribute("data-authenticated") === "true";
        const userName = headerElement.getAttribute("data-user-name") || "User";

        const authSectionHtml = isAuthenticated ? `
        <div class="dropdown">
            <button class="btn btn-primary-gradient text-white dropdown-toggle px-3 shadow-sm" type="button" id="userMenuDropdown" data-bs-toggle="dropdown" aria-expanded="false" style="font-size: 0.9rem;">
                <i class="fas fa-user-circle me-1.5"></i> Hi, ${userName}
            </button>
            <ul class="dropdown-menu dropdown-menu-end border-0 shadow-lg rounded-3 mt-2 p-2" aria-labelledby="userMenuDropdown" style="min-width: 180px;">
                <li><a class="dropdown-item rounded-2 py-2" href="/user/dashboard/"><i class="fas fa-chart-pie me-2 text-primary"></i>Dashboard</a></li>
                <li><a class="dropdown-item rounded-2 py-2" href="/user/profile/"><i class="fas fa-user-gear me-2 text-secondary"></i>Settings</a></li>
                <li><hr class="dropdown-divider"></li>
                <li><a class="dropdown-item rounded-2 py-2 text-danger" href="/logout/"><i class="fas fa-arrow-right-from-bracket me-2"></i>Sign Out</a></li>
            </ul>
        </div>
        ` : `
        <div class="d-flex align-items-center gap-3">
            <a href="/login/" class="btn btn-outline-custom border-0 text-dark">Sign In</a>
            <a href="/register/" class="btn btn-primary-gradient text-white">Get Started</a>
        </div>
        `;

        headerElement.innerHTML = `
        <nav class="navbar navbar-expand-lg glass-navbar fixed-top py-3">
            <div class="container">
                <a class="navbar-brand d-flex align-items-center gap-2" href="/">
                    <span class="d-flex align-items-center justify-content-center bg-indigo-600 rounded-3 text-white" style="width: 38px; height: 38px; background: var(--brand-primary-gradient); box-shadow: 0 4px 12px rgba(124, 58, 237, 0.3);">
                        <i class="fas fa-language" style="font-size: 1.3rem;"></i>
                    </span>
                    <span class="fs-4 fw-bold" style="font-family: var(--font-headings); letter-spacing: -0.5px; color: var(--color-slate-900);">Teltam<span class="text-indigo-600" style="color: #7c3aed;">.ai</span></span>
                </a>
                
                <button class="navbar-toggler border-0 shadow-none" type="button" data-bs-toggle="collapse" data-bs-target="#teltamNavbar" aria-controls="teltamNavbar" aria-expanded="false" aria-label="Toggle navigation">
                    <span class="fas fa-bars text-dark" style="font-size: 1.25rem;"></span>
                </button>
                
                <div class="collapse navbar-collapse" id="teltamNavbar">
                    <ul class="navbar-nav mx-auto mb-2 mb-lg-0 gap-1 gap-lg-2">
                        <li class="nav-item">
                            <a class="nav-link px-3 fw-500 text-dark" href="/">Home</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link px-3 fw-500 text-dark" href="/about/">About</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link px-3 fw-500 text-dark" href="/pricing/">Pricing</a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link px-3 fw-500 text-dark" href="/ai-tools/">AI Tools</a>
                        </li>
                        <li class="nav-item dropdown">
                            <a class="nav-link dropdown-toggle px-3 fw-500 text-dark" href="#" id="resourcesDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                                Learning
                            </a>
                            <ul class="dropdown-menu border-0 shadow-sm rounded-3 mt-2 p-2" aria-labelledby="resourcesDropdown">
                                <li><a class="dropdown-item rounded-2 py-2" href="/blog/"><i class="fas fa-blog me-2 text-primary"></i>Blog Articles</a></li>
                                <li><a class="dropdown-item rounded-2 py-2" href="/videos/"><i class="fab fa-youtube me-2 text-danger"></i>Video Tutorials</a></li>
                            </ul>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link px-3 fw-500 text-dark" href="/contact/">Contact</a>
                        </li>
                    </ul>
                    <div class="d-flex align-items-center mt-3 mt-lg-0">
                        ${authSectionHtml}
                    </div>
                </div>
            </div>
        </nav>
        `;
    }

    // 2. Inject Footer
    const footerElement = document.getElementById("global-footer");
    if (footerElement) {
        footerElement.innerHTML = `
        <footer class="bg-dark-gradient py-5 mt-5">
            <div class="container py-4">
                <div class="row g-4">
                    <div class="col-lg-4 col-md-6">
                        <div class="d-flex align-items-center gap-2 mb-3">
                            <span class="d-flex align-items-center justify-content-center rounded-3 text-white" style="width: 36px; height: 36px; background: var(--brand-primary-gradient);">
                                <i class="fas fa-language" style="font-size: 1.15rem;"></i>
                            </span>
                            <span class="fs-4 fw-bold text-white" style="font-family: var(--font-headings); letter-spacing: -0.5px;">Teltam<span style="color: #a78bfa;">.ai</span></span>
                        </div>
                        <p class="text-slate-400 mb-4" style="color: #94a3b8; line-height: 1.6;">
                            Empowering global connection through state-of-the-art LLM translation, contextual transliteration, and real-time pronunciation engine. Translate your content accurately.
                        </p>
                        <div class="d-flex gap-2">
                            <a href="#" class="btn btn-outline-light rounded-circle d-flex align-items-center justify-content-center" style="width: 38px; height: 38px;"><i class="fab fa-twitter"></i></a>
                            <a href="#" class="btn btn-outline-light rounded-circle d-flex align-items-center justify-content-center" style="width: 38px; height: 38px;"><i class="fab fa-facebook-f"></i></a>
                            <a href="#" class="btn btn-outline-light rounded-circle d-flex align-items-center justify-content-center" style="width: 38px; height: 38px;"><i class="fab fa-linkedin-in"></i></a>
                            <a href="#" class="btn btn-outline-light rounded-circle d-flex align-items-center justify-content-center" style="width: 38px; height: 38px;"><i class="fab fa-github"></i></a>
                        </div>
                    </div>
                    <div class="col-lg-2 col-md-6 col-6">
                        <h5 class="text-white mb-3" style="font-family: var(--font-headings);">Quick Links</h5>
                        <ul class="list-unstyled d-flex flex-column gap-2">
                            <li><a href="/" class="footer-link">Home</a></li>
                            <li><a href="/about/" class="footer-link">About Us</a></li>
                            <li><a href="/services/" class="footer-link">Services</a></li>
                            <li><a href="/pricing/" class="footer-link">Pricing Plans</a></li>
                            <li><a href="/contact/" class="footer-link">Contact Us</a></li>
                        </ul>
                    </div>
                    <div class="col-lg-2 col-md-6 col-6">
                        <h5 class="text-white mb-3" style="font-family: var(--font-headings);">AI Features</h5>
                        <ul class="list-unstyled d-flex flex-column gap-2">
                            <li><a href="/ai-tools/" class="footer-link">Text Translation</a></li>
                            <li><a href="/ai-tools/" class="footer-link">Transliteration</a></li>
                            <li><a href="/ai-tools/" class="footer-link">Grammar Checker</a></li>
                            <li><a href="/ai-tools/" class="footer-link">Voice Synthesis</a></li>
                            <li><a href="/ai-tools/" class="footer-link">Doc Translator</a></li>
                        </ul>
                    </div>
                    <div class="col-lg-4 col-md-6">
                        <h5 class="text-white mb-3" style="font-family: var(--font-headings);">Subscribe to Newsletter</h5>
                        <p class="text-slate-400 mb-3" style="color: #94a3b8;">Stay up to date with the latest AI translation advancements, articles, and product releases.</p>
                        <form id="newsletterForm" class="d-flex gap-2">
                            <input type="email" class="form-control rounded-pill border-0 px-3 bg-white" placeholder="Enter your email" required style="outline:none; box-shadow: none;">
                            <button type="submit" class="btn btn-primary-gradient border-0 px-4 rounded-pill">Join</button>
                        </form>
                    </div>
                </div>
                <hr class="my-4" style="border-color: rgba(255,255,255,0.1);">
                <div class="row align-items-center">
                    <div class="col-md-6 text-center text-md-start">
                        <p class="mb-0 text-slate-400" style="color: #64748b; font-size: 0.9rem;">&copy; 2026 Teltam AI. All rights reserved. Created with passion for linguistic precision.</p>
                    </div>
                    <div class="col-md-6 text-center text-md-end mt-2 mt-md-0">
                        <a href="#" class="footer-link me-3" style="font-size: 0.9rem;">Privacy Policy</a>
                        <a href="#" class="footer-link" style="font-size: 0.9rem;">Terms of Service</a>
                    </div>
                </div>
            </div>
        </footer>
        `;

        // Add handler for newsletter submission
        const newsletterForm = document.getElementById("newsletterForm");
        if (newsletterForm) {
            newsletterForm.addEventListener("submit", (e) => {
                e.preventDefault();
                const emailInput = newsletterForm.querySelector("input[type='email']");
                if (emailInput && emailInput.value) {
                    Swal.fire({
                        toast: true,
                        position: 'top-end',
                        icon: 'success',
                        title: `Thank you for subscribing!`,
                        text: emailInput.value,
                        showConfirmButton: false,
                        timer: 3000,
                        timerProgressBar: true
                    });
                    emailInput.value = "";
                }
            });
        }
    }

    // 3. Auto-Highlight Active Navigation Link
    const currentPathname = window.location.pathname;
    const navLinks = document.querySelectorAll(".navbar-nav .nav-link, .navbar-nav .dropdown-item");

    navLinks.forEach(link => {
        const href = link.getAttribute("href");
        if (href === currentPathname || (currentPathname === "/" && href === "/")) {
            link.classList.add("active");
            // Highlight parent dropdown if active link is a dropdown item
            if (link.classList.contains("dropdown-item")) {
                const parentDropdown = link.closest(".dropdown").querySelector(".nav-link");
                if (parentDropdown) {
                    parentDropdown.classList.add("active");
                }
            }
        }
    });
});
