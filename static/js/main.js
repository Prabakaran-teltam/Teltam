// Teltam AI - Main Interactive Logic (Translator Simulator, Form Validators, Pricing and FAQs)

document.addEventListener("DOMContentLoaded", () => {
    // 1. Interactive Translation Simulator Dictionary
    const translationDb = {
        "hello": {
            es: { trans: "Hola" },
            fr: { trans: "Bonjour" },
            de: { trans: "Hallo" },
            ta: { trans: "வணக்கம் (Vanakkam)" }
        },
        "hello, how are you?": {
            es: { trans: "Hola, ¿cómo estás?" },
            fr: { trans: "Bonjour, comment allez-vous?" },
            de: { trans: "Hallo, wie geht es dir?" },
            ta: { trans: "வணக்கம், நீங்கள் எப்படி இருக்கிறீர்கள்?" }
        },
        "ai-powered translation is amazing": {
            es: { trans: "La traducción impulsada por IA es increíble" },
            fr: { trans: "La traduction alimentée par l'IA est incroyable" },
            de: { trans: "KI-gestützte Übersetzung ist erstaunlich" },
            ta: { trans: "AI-இயங்கும் மொழிபெயர்ப்பு அற்புதம்" }
        }
    };

    // Translator Logic (Home & AI Tools Page)
    // Helper to get CSRF Token from cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Debounce function to limit rapid API requests
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // Translator Logic (Home & AI Tools Page)
    const translateBtn = document.getElementById("translateBtn");
    const sourceText = document.getElementById("sourceText");
    const sourceLang = document.getElementById("sourceLanguage");
    const targetLang = document.getElementById("targetLanguage");
    const outputText = document.getElementById("outputText");
    const translationSpinner = document.getElementById("translationSpinner");

    if (translateBtn && sourceText && targetLang && outputText) {
        const triggerTranslation = (isLive = false) => {
            const query = sourceText.value.trim();
            const src = sourceLang ? sourceLang.value : 'auto';
            const tgt = targetLang.value;

            if (!query) {
                outputText.value = "";
                outputText.innerText = ""; // compatibility
                return;
            }

            // Show Loading Spinner
            if (translationSpinner) translationSpinner.classList.remove("d-none");
            
            // Set initial state for explicit clicks (non-live)
            if (!isLive) {
                outputText.value = "Translating with Teltam LLM...";
                outputText.innerText = "Translating with Teltam LLM...";
            }

            const csrftoken = getCookie('csrftoken') || '';

            fetch('/api/translate/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    text: query,
                    source_lang: src,
                    target_lang: tgt
                })
            })
            .then(response => {
                if (translationSpinner) translationSpinner.classList.add("d-none");
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.error || 'Server error'); });
                }
                return response.json();
            })
            .then(data => {
                // Update text areas
                outputText.value = data.translated_text;
                outputText.innerText = data.translated_text; // compatibility
            })
            .catch(error => {
                if (translationSpinner) translationSpinner.classList.add("d-none");
                outputText.value = `Error: ${error.message}`;
                outputText.innerText = `Error: ${error.message}`; // compatibility
                console.error("Translation request failed:", error);
            });
        };

        // Attach debounced translate for typing in textarea
        const debouncedTranslate = debounce(() => triggerTranslation(true), 500);

        sourceText.addEventListener("input", () => {
            if (sourceText.value.trim().length > 0) {
                debouncedTranslate();
            } else {
                outputText.value = "";
                outputText.innerText = "";
            }
        });

        // Attach immediate translate for dropdown select changes
        if (sourceLang) {
            sourceLang.addEventListener("change", () => {
                if (sourceText.value.trim().length > 0) {
                    triggerTranslation(false);
                }
            });
        }

        if (targetLang) {
            targetLang.addEventListener("change", () => {
                if (sourceText.value.trim().length > 0) {
                    triggerTranslation(false);
                }
            });
        }

        // Attach explicit button click
        translateBtn.addEventListener("click", () => {
            if (!sourceText.value.trim()) {
                Swal.fire({
                    toast: true,
                    position: 'top-end',
                    icon: 'warning',
                    title: 'Please enter some text to translate.',
                    showConfirmButton: false,
                    timer: 3000,
                    timerProgressBar: true
                });
                return;
            }
            triggerTranslation(false);
        });

        // Trigger translate on pressing enter (Ctrl + Enter)
        sourceText.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && e.ctrlKey) {
                e.preventDefault();
                triggerTranslation(false);
            }
        });
    }

    // Speech synthesis mock (Pronunciation Speaker Button)
    const speakBtn = document.getElementById("speakBtn");
    if (speakBtn && outputText) {
        speakBtn.addEventListener("click", () => {
            const textToSpeak = outputText.innerText;
            if (textToSpeak && !textToSpeak.includes("Translating")) {
                if ('speechSynthesis' in window) {
                    const utterance = new SpeechSynthesisUtterance(textToSpeak);
                    // Try to match voice code based on selected lang
                    const langCodeMap = { es: "es-ES", fr: "fr-FR", de: "de-DE", ta: "ta-IN" };
                    if (targetLang && langCodeMap[targetLang.value]) {
                        utterance.lang = langCodeMap[targetLang.value];
                    }
                    window.speechSynthesis.speak(utterance);
                    
                    // Add active button animation class
                    speakBtn.classList.add("text-indigo-600");
                    setTimeout(() => speakBtn.classList.remove("text-indigo-600"), 1000);
                } else {
                    Swal.fire({
                        icon: 'error',
                        title: 'Not Supported',
                        text: 'Text-to-speech not supported in this browser.',
                        confirmButtonColor: '#ef4444',
                        customClass: {
                            confirmButton: 'btn btn-danger rounded-pill px-4'
                        },
                        buttonsStyling: false
                    });
                }
            }
        });
    }

    // Copy to clipboard
    const copyBtn = document.getElementById("copyBtn");
    if (copyBtn && outputText) {
        copyBtn.addEventListener("click", () => {
            const text = outputText.innerText;
            if (text && !text.includes("Translating")) {
                navigator.clipboard.writeText(text).then(() => {
                    const origIcon = copyBtn.innerHTML;
                    copyBtn.innerHTML = `<i class="fas fa-check text-success"></i>`;
                    setTimeout(() => { copyBtn.innerHTML = origIcon; }, 1500);
                });
            }
        });
    }

    // 2. Custom FAQ Accordion Functionality
    const faqButtons = document.querySelectorAll(".accordion-button-custom");
    faqButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const collapseId = btn.getAttribute("aria-controls");
            const collapseEl = document.getElementById(collapseId);
            
            if (collapseEl) {
                const isActive = btn.classList.contains("active");
                
                // Close all other accordions
                faqButtons.forEach(otherBtn => {
                    if (otherBtn !== btn) {
                        otherBtn.classList.remove("active");
                        const otherCollapse = document.getElementById(otherBtn.getAttribute("aria-controls"));
                        if (otherCollapse) otherCollapse.style.maxHeight = null;
                    }
                });

                if (isActive) {
                    btn.classList.remove("active");
                    collapseEl.style.maxHeight = null;
                } else {
                    btn.classList.add("active");
                    collapseEl.style.maxHeight = collapseEl.scrollHeight + "px";
                }
            }
        });
    });

    // 3. Pricing Plan Switch Toggle (Monthly vs Yearly)
    const pricingSwitch = document.getElementById("billingSwitch");
    if (pricingSwitch) {
        pricingSwitch.addEventListener("change", () => {
            const isYearly = pricingSwitch.checked;
            document.querySelectorAll(".monthly-price-block").forEach(el => {
                if (isYearly) {
                    el.classList.add("d-none");
                } else {
                    el.classList.remove("d-none");
                }
            });
            document.querySelectorAll(".yearly-price-block").forEach(el => {
                if (isYearly) {
                    el.classList.remove("d-none");
                } else {
                    el.classList.add("d-none");
                }
            });
        });
    }

    // 4. Contact Us Form Validation
    const contactForm = document.getElementById("teltamContactForm");
    if (contactForm) {
        contactForm.addEventListener("submit", (e) => {
            const name = document.getElementById("contactName").value.trim();
            const email = document.getElementById("contactEmail").value.trim();
            const phone = document.getElementById("contactPhone").value.trim();
            const subject = document.getElementById("contactSubject").value.trim();
            const message = document.getElementById("contactMessage").value.trim();
            
            let isValid = true;
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            
            if (!name || name.length < 2) {
                showInputErr("contactName", "Please enter a valid name (min 2 characters)");
                isValid = false;
            } else {
                clearInputErr("contactName");
            }

            if (!emailRegex.test(email)) {
                showInputErr("contactEmail", "Please enter a valid email address");
                isValid = false;
            } else {
                clearInputErr("contactEmail");
            }

            if (phone && phone.length < 7) {
                showInputErr("contactPhone", "Please enter a valid phone number");
                isValid = false;
            } else {
                clearInputErr("contactPhone");
            }

            if (!subject) {
                showInputErr("contactSubject", "Please enter a subject line");
                isValid = false;
            } else {
                clearInputErr("contactSubject");
            }

            if (!message || message.length < 10) {
                showInputErr("contactMessage", "Please enter a message (min 10 characters)");
                isValid = false;
            } else {
                clearInputErr("contactMessage");
            }

            if (!isValid) {
                e.preventDefault();
                Swal.fire({
                    icon: 'warning',
                    title: 'Form Validation Error',
                    text: 'Please check the highlighted fields and try again.',
                    confirmButtonColor: '#4f46e5',
                    customClass: {
                        confirmButton: 'btn btn-primary rounded-pill px-4'
                    },
                    buttonsStyling: false
                });
            }
        });
    }

    // 5. Login / Register Form Validations
    const loginForm = document.getElementById("teltamLoginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", (e) => {
            const email = document.getElementById("loginEmail").value.trim();
            const pass = document.getElementById("loginPassword").value;
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            let isValid = true;

            if (!emailRegex.test(email)) {
                showInputErr("loginEmail", "Please enter a valid email address");
                isValid = false;
            } else {
                clearInputErr("loginEmail");
            }

            if (!pass || pass.length < 6) {
                showInputErr("loginPassword", "Password must be at least 6 characters");
                isValid = false;
            } else {
                clearInputErr("loginPassword");
            }

            if (!isValid) {
                e.preventDefault();
                Swal.fire({
                    icon: 'warning',
                    title: 'Form Validation Error',
                    text: 'Please check your inputs and try again.',
                    confirmButtonColor: '#4f46e5',
                    customClass: {
                        confirmButton: 'btn btn-primary rounded-pill px-4'
                    },
                    buttonsStyling: false
                });
            }
        });
    }

    const registerForm = document.getElementById("teltamRegisterForm");
    if (registerForm) {
        registerForm.addEventListener("submit", (e) => {
            const name = document.getElementById("registerName").value.trim();
            const email = document.getElementById("registerEmail").value.trim();
            const pass = document.getElementById("registerPassword").value;
            const confirmPass = document.getElementById("registerConfirmPassword").value;
            const agreeTerms = document.getElementById("registerTerms").checked;
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            let isValid = true;

            if (!name || name.length < 2) {
                showInputErr("registerName", "Please enter a valid name");
                isValid = false;
            } else {
                clearInputErr("registerName");
            }

            if (!emailRegex.test(email)) {
                showInputErr("registerEmail", "Please enter a valid email address");
                isValid = false;
            } else {
                clearInputErr("registerEmail");
            }

            if (!pass || pass.length < 6) {
                showInputErr("registerPassword", "Password must be at least 6 characters");
                isValid = false;
            } else {
                clearInputErr("registerPassword");
            }

            if (pass !== confirmPass) {
                showInputErr("registerConfirmPassword", "Passwords do not match");
                isValid = false;
            } else {
                clearInputErr("registerConfirmPassword");
            }

            if (!agreeTerms) {
                Swal.fire({
                    icon: 'warning',
                    title: 'Terms of Service',
                    text: 'You must agree to the Terms of Service.',
                    confirmButtonColor: '#fbbf24',
                    customClass: {
                        confirmButton: 'btn btn-warning text-white rounded-pill px-4'
                    },
                    buttonsStyling: false
                });
                isValid = false;
            }

            if (!isValid) {
                e.preventDefault();
                if (agreeTerms) {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Form Validation Error',
                        text: 'Please check the highlighted fields and try again.',
                        confirmButtonColor: '#4f46e5',
                        customClass: {
                            confirmButton: 'btn btn-primary rounded-pill px-4'
                        },
                        buttonsStyling: false
                    });
                }
            }
        });
    }

    // Helper functions for showing/clearing form input error messages
    function showInputErr(id, message) {
        const inputEl = document.getElementById(id);
        if (inputEl) {
            inputEl.classList.add("is-invalid");
            let feedback = inputEl.nextElementSibling;
            if (feedback && feedback.classList.contains("invalid-feedback")) {
                feedback.innerText = message;
            } else {
                const div = document.createElement("div");
                div.className = "invalid-feedback";
                div.innerText = message;
                inputEl.after(div);
            }
        }
    }

    function clearInputErr(id) {
        const inputEl = document.getElementById(id);
        if (inputEl) {
            inputEl.classList.remove("is-invalid");
        }
    }
});
