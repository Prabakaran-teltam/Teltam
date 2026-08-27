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
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item rounded-2 py-2 fw-semibold text-indigo-600" href="/api-docs/"><i class="fas fa-code me-2 text-indigo-600"></i>Developer API Docs</a></li>
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
                            <a href="https://www.facebook.com/people/Teltam/61576516457281/" target="_blank" rel="noopener noreferrer" class="btn btn-outline-light rounded-circle d-flex align-items-center justify-content-center" style="width: 38px; height: 38px;" title="Facebook"><i class="fab fa-facebook-f"></i></a>
                            <a href="https://www.instagram.com/teltam.ai" target="_blank" rel="noopener noreferrer" class="btn btn-outline-light rounded-circle d-flex align-items-center justify-content-center" style="width: 38px; height: 38px;" title="Instagram"><i class="fab fa-instagram"></i></a>
                            <a href="https://www.linkedin.com/company/teltamaitranslator/" target="_blank" rel="noopener noreferrer" class="btn btn-outline-light rounded-circle d-flex align-items-center justify-content-center" style="width: 38px; height: 38px;" title="LinkedIn"><i class="fab fa-linkedin-in"></i></a>
                            <a href="https://www.youtube.com/@somethingtalk125" target="_blank" rel="noopener noreferrer" class="btn btn-outline-light rounded-circle d-flex align-items-center justify-content-center" style="width: 38px; height: 38px;" title="YouTube"><i class="fab fa-youtube"></i></a>
                        </div>
                    </div>
                    <div class="col-lg-2 col-md-6 col-6">
                        <h5 class="text-white mb-3" style="font-family: var(--font-headings);">Quick Links</h5>
                        <ul class="list-unstyled d-flex flex-column gap-2">
                            <li><a href="/" class="footer-link">Home</a></li>
                            <li><a href="/about/" class="footer-link">About Us</a></li>
                            <li><a href="/services/" class="footer-link">Services</a></li>
                            <li><a href="/pricing/" class="footer-link">Pricing Plans</a></li>
                            <li><a href="/terms/" class="footer-link">Terms &amp; Conditions</a></li>
                            <li><a href="/contact/" class="footer-link">Contact Us</a></li>
                        </ul>
                    </div>
                    <div class="col-lg-2 col-md-6 col-6">
                        <h5 class="text-white mb-3" style="font-family: var(--font-headings);">AI Features</h5>
                        <ul class="list-unstyled d-flex flex-column gap-2">
                            <li><a href="/ai-tools/" class="footer-link">Text Translation</a></li>
                            <li><a href="/ai-tools/" class="footer-link">Doc Translator</a></li>
                            <li><a href="/ai-tools/" class="footer-link">Voice Translator</a></li>
                            <li><a href="/api-docs/" class="footer-link">REST API Integration</a></li>
                            <li><a href="/user/api-keys/" class="footer-link">API Keys Dashboard</a></li>
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
                        <a href="/privacy/" class="footer-link me-3" style="font-size: 0.9rem;">Privacy Policy</a>
                        <a href="/terms/" class="footer-link me-3" style="font-size: 0.9rem;">Terms of Service</a>
                        <a href="/refund-policy/" class="footer-link" style="font-size: 0.9rem;">Refund Policy</a>
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

    // Normalize path by removing trailing slashes for standard comparison
    const normalizePath = (path) => {
        if (!path) return '';
        return path === '/' ? '/' : path.replace(/\/+$/, "");
    };

    const currentNormalized = normalizePath(currentPathname);

    navLinks.forEach(link => {
        const href = link.getAttribute("href");
        if (!href || href === "#") return;
        
        const hrefNormalized = normalizePath(href);
        let isMatch = false;
        
        if (hrefNormalized === '/') {
            isMatch = currentNormalized === '/';
        } else {
            isMatch = currentNormalized === hrefNormalized || currentNormalized.startsWith(hrefNormalized + '/');
        }

        if (isMatch) {
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

    // 4. Inject AI Class Enquiry Floater & Modal if not present on page
    if (!document.getElementById("joinAiClassesFloater")) {
        const container = document.createElement("div");
        container.id = "aiClassEnquiryComponentContainer";
        container.innerHTML = `
<style>
  @keyframes pulseBlinkGlow {
    0% {
      transform: scale(1);
      box-shadow: 0 0 0 0 rgba(236, 72, 153, 0.7), 0 8px 24px rgba(139, 92, 246, 0.4);
    }
    50% {
      transform: scale(1.06);
      box-shadow: 0 0 0 14px rgba(236, 72, 153, 0), 0 12px 28px rgba(139, 92, 246, 0.6);
    }
    100% {
      transform: scale(1);
      box-shadow: 0 0 0 0 rgba(236, 72, 153, 0), 0 8px 24px rgba(139, 92, 246, 0.4);
    }
  }

  .btn-join-ai-classes-floating {
    position: fixed;
    bottom: 24px;
    left: 24px;
    z-index: 1050;
    background: linear-gradient(135deg, #ef4444 0%, #ec4899 50%, #8b5cf6 100%);
    color: #ffffff !important;
    font-weight: 800;
    font-size: 0.92rem;
    padding: 10px 20px;
    border-radius: 50px;
    border: 2px solid #ffffff;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    animation: pulseBlinkGlow 2s infinite ease-in-out;
    transition: all 0.3s ease;
    text-decoration: none;
    line-height: 1;
    letter-spacing: 0.5px;
  }
  .btn-join-ai-classes-floating:hover {
    transform: scale(1.08) translateY(-2px);
    box-shadow: 0 14px 32px rgba(236, 72, 153, 0.6);
    color: #ffffff !important;
  }
</style>

<button type="button" class="btn-join-ai-classes-floating shadow-lg" data-bs-toggle="modal" data-bs-target="#aiClassEnquiryModal" id="joinAiClassesFloater">
  <i class="fas fa-circle text-warning fa-pulse" style="font-size: 0.55rem;"></i>
  <i class="fas fa-graduation-cap fs-6"></i>
  <span>Live</span>
</button>

<div class="modal fade" id="aiClassEnquiryModal" tabindex="-1" aria-labelledby="aiClassEnquiryModalLabel" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content border-0 shadow-lg rounded-4 overflow-hidden">
      <div class="modal-header text-white p-4" style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);">
        <div>
          <div class="d-flex align-items-center gap-2 mb-1.5">
            <span class="badge px-2.5 py-1 rounded-pill" style="background-color: rgba(239, 68, 68, 0.25); color: #fca5a5; font-size: 0.75rem; font-weight: 700;">
              <i class="fas fa-sparkles text-warning me-1"></i> Interactive Masterclass
            </span>
          </div>
          <h5 class="modal-title fw-bold text-white mb-0" id="aiClassEnquiryModalLabel" style="font-family: 'Outfit', sans-serif;">
            Join Teltam AI Masterclass
          </h5>
          <p class="small mb-0 mt-1" style="color: #cbd5e1; font-size: 0.82rem;">Master LLM Prompt Engineering, AI Translation & Fine-Tuning.</p>
        </div>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>

      <div class="modal-body p-4 bg-white">
        <form id="aiClassEnquiryForm" novalidate>
          <div class="mb-3">
            <label class="form-label small fw-bold text-slate-700">Full Name <span class="text-danger">*</span></label>
            <div class="input-group">
              <span class="input-group-text bg-light border-end-0 text-slate-500"><i class="fas fa-user"></i></span>
              <input type="text" class="form-control border-start-0 ps-0 shadow-none" id="enquiryFullName" required placeholder="Enter your full name">
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label small fw-bold text-slate-700">Email Address <span class="text-danger">*</span></label>
            <div class="input-group">
              <span class="input-group-text bg-light border-end-0 text-slate-500"><i class="fas fa-envelope"></i></span>
              <input type="email" class="form-control border-start-0 ps-0 shadow-none" id="enquiryEmail" required placeholder="name@example.com">
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label small fw-bold text-slate-700">Phone Number <span class="text-danger">*</span></label>
            <div class="input-group">
              <span class="input-group-text bg-light border-end-0 text-slate-500"><i class="fas fa-phone"></i></span>
              <input type="tel" class="form-control border-start-0 ps-0 shadow-none" id="enquiryPhone" required placeholder="+91 98765 43210">
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label small fw-bold text-slate-700">Message / Learning Goals <span class="text-muted small">(Optional)</span></label>
            <textarea class="form-control shadow-none" id="enquiryMessage" rows="3" placeholder="Tell us about your learning objectives or preferred batch timings..."></textarea>
          </div>

          <button type="submit" id="enquirySubmitBtn" class="btn btn-primary w-100 py-2.5 rounded-pill fw-bold text-white shadow-md border-0" style="background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);">
            <i class="fas fa-paper-plane me-1.5"></i> Submit Class Enquiry
          </button>
        </form>
      </div>
    </div>
  </div>
</div>
        `;
        document.body.appendChild(container);

        // Bind form submit listener
        const enquiryForm = document.getElementById("aiClassEnquiryForm");
        if (enquiryForm) {
            enquiryForm.addEventListener("submit", function(e) {
                e.preventDefault();
                const fullName = document.getElementById("enquiryFullName")?.value.trim();
                const email = document.getElementById("enquiryEmail")?.value.trim();
                const phone = document.getElementById("enquiryPhone")?.value.trim();
                const message = document.getElementById("enquiryMessage")?.value.trim();
                const submitBtn = document.getElementById("enquirySubmitBtn");

                if (!fullName || !email || !phone) {
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({
                            icon: 'warning',
                            title: 'Missing Fields',
                            text: 'Please fill in all required fields (Full Name, Email Address, Phone Number).',
                            confirmButtonColor: '#f59e0b'
                        });
                    } else {
                        alert('Please fill in all required fields (Full Name, Email Address, Phone Number).');
                    }
                    return;
                }

                const origHtml = submitBtn.innerHTML;
                submitBtn.disabled = true;
                submitBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status"></span> Submitting...`;

                const getCsrf = () => {
                    const cookieVal = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1];
                    const inputVal = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
                    return cookieVal || inputVal || '';
                };

                fetch('/api/enquiry/ai-classes/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrf()
                    },
                    body: JSON.stringify({
                        full_name: fullName,
                        email: email,
                        phone_number: phone,
                        message: message
                    })
                })
                .then(res => res.json())
                .then(data => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = origHtml;
                    if (data.status === 'success') {
                        const modalEl = document.getElementById('aiClassEnquiryModal');
                        if (modalEl && typeof bootstrap !== 'undefined') {
                            const modalInstance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
                            if (modalInstance) modalInstance.hide();
                        }

                        enquiryForm.reset();

                        if (typeof Swal !== 'undefined') {
                            Swal.fire({
                                icon: 'success',
                                title: 'Enquiry Received!',
                                text: data.message,
                                confirmButtonColor: '#4f46e5',
                                customClass: {
                                    confirmButton: 'btn btn-primary rounded-pill px-4'
                                }
                            });
                        } else {
                            alert(data.message);
                        }
                    } else {
                        if (typeof Swal !== 'undefined') {
                            Swal.fire({
                                icon: 'error',
                                title: 'Submission Error',
                                text: data.error || 'Failed to submit enquiry.',
                                confirmButtonColor: '#ef4444'
                            });
                        } else {
                            alert(data.error || 'Failed to submit enquiry.');
                        }
                    }
                })
                .catch(err => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = origHtml;
                    if (typeof Swal !== 'undefined') {
                        Swal.fire({
                            icon: 'error',
                            title: 'Connection Error',
                            text: 'Network issue: ' + err.message,
                            confirmButtonColor: '#ef4444'
                        });
                    } else {
                        alert('Network issue: ' + err.message);
                    }
                });
            });
        }
    }
});
