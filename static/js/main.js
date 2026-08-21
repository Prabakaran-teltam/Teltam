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

    if (sourceText && targetLang && outputText) {
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

                // Populate linguistic insights if container exists
                const activeDetails = document.getElementById("activeDetailsContainer");
                if (activeDetails) {
                    activeDetails.classList.remove("d-none");
                    const translitEl = document.getElementById("outputTranslit");
                    const pronEl = document.getElementById("outputPron");
                    const grammarEl = document.getElementById("outputGrammar");
                    if (translitEl) translitEl.innerText = data.transliteration || "-";
                    if (pronEl) pronEl.innerText = data.pronunciation || "-";
                    if (grammarEl) grammarEl.innerText = data.grammar_analysis || "No grammar issues detected.";
                }

                // Reveal Translate Another button if present
                const newTransBtn = document.getElementById("newTransBtn") || document.getElementById("textNewTransBtn");
                if (newTransBtn) {
                    newTransBtn.classList.remove("d-none");
                }
            })
            .catch(error => {
                if (translationSpinner) translationSpinner.classList.add("d-none");
                outputText.value = `Error: ${error.message}`;
                outputText.innerText = `Error: ${error.message}`; // compatibility
                console.error("Translation request failed:", error);
            });
        };

        // Reset & Translate Another Handler
        const resetForNewTranslation = () => {
            if (sourceText) {
                sourceText.value = "";
                sourceText.focus();
            }
            if (outputText) {
                outputText.value = "";
                outputText.innerText = "";
            }
            const charCount = document.getElementById("charCount") || document.getElementById("charCounter");
            if (charCount) charCount.innerText = "0 / 5000";

            const clearBtn = document.getElementById("clearSourceBtn");
            if (clearBtn) clearBtn.classList.add("d-none");

            const activeDetails = document.getElementById("activeDetailsContainer");
            if (activeDetails) activeDetails.classList.add("d-none");

            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    toast: true,
                    position: 'top-end',
                    icon: 'info',
                    title: 'Ready for new translation!',
                    showConfirmButton: false,
                    timer: 1500
                });
            }
        };

        // Attach new translation button click
        document.querySelectorAll("#newTransBtn, #textNewTransBtn").forEach(btn => {
            btn.addEventListener("click", resetForNewTranslation);
        });

        // Attach debounced translate for typing in textarea
        const debouncedTranslate = debounce(() => triggerTranslation(true), 800);

        sourceText.addEventListener("input", () => {
            if (sourceText.value.trim().length > 0) {
                debouncedTranslate();
            } else {
                outputText.value = "";
                outputText.innerText = "";
            }
        });

        // Keyboard Shortcut: Ctrl + Enter to Translate, Ctrl + Shift + X to Clear/New
        document.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                if (document.activeElement === sourceText || sourceText.value.trim().length > 0) {
                    e.preventDefault();
                    triggerTranslation(false);
                }
            }
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'x') {
                e.preventDefault();
                resetForNewTranslation();
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
        if (translateBtn) {
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
        }

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
            const textToSpeak = outputText.value || outputText.innerText;
            if (textToSpeak && !textToSpeak.includes("Translating")) {
                // Cancel any ongoing local speech synthesis
                if ('speechSynthesis' in window) {
                    window.speechSynthesis.cancel();
                }
                
                // Identify target language code
                const langCode = targetLang ? targetLang.value : 'en';
                const langCodeMap = { 
                    en: "en", 
                    es: "es", 
                    fr: "fr", 
                    de: "de", 
                    ta: "ta",
                    hi: "hi",
                    te: "te"
                };
                const tl = langCodeMap[langCode] || langCode;

                // Animate button
                speakBtn.classList.add("text-indigo-600");
                setTimeout(() => speakBtn.classList.remove("text-indigo-600"), 1000);

                // Try playing via Google Translate TTS for highly clear native voice
                try {
                    const encodedText = encodeURIComponent(textToSpeak);
                    const ttsUrl = `https://translate.google.com/translate_tts?ie=UTF-8&tl=${tl}&client=tw-ob&q=${encodedText}`;
                    
                    if (window.currentTtsAudio) {
                        window.currentTtsAudio.pause();
                    }
                    
                    const audio = new Audio(ttsUrl);
                    window.currentTtsAudio = audio;
                    
                    const playPromise = audio.play();
                    if (playPromise !== undefined) {
                        playPromise.catch(err => {
                            console.warn("Google TTS play failed. Falling back to local Web Speech API.", err);
                            speakWithWebSpeechFallback(textToSpeak, tl);
                        });
                    }
                } catch (e) {
                    console.warn("Google TTS setup failed. Falling back to local Web Speech API.", e);
                    speakWithWebSpeechFallback(textToSpeak, tl);
                }
            }
        });
    }

    // Local Web Speech Fallback helper
    function speakWithWebSpeechFallback(text, langCode) {
        if (!('speechSynthesis' in window)) return;
        const utterance = new SpeechSynthesisUtterance(text);
        const localeMap = {
            en: "en-US",
            es: "es-ES",
            fr: "fr-FR",
            de: "de-DE",
            ta: "ta-IN",
            hi: "hi-IN",
            te: "te-IN"
        };
        const targetLocale = localeMap[langCode] || langCode;
        utterance.lang = targetLocale;

        const voices = window.speechSynthesis.getVoices();
        let bestVoice = null;
        if (voices && voices.length > 0) {
            const matchLocale = targetLocale.toLowerCase().replace('_', '-');
            const langPrefix = matchLocale.split('-')[0];
            const localeMatches = voices.filter(v => v.lang.toLowerCase().replace('_', '-').startsWith(langPrefix));
            if (localeMatches.length > 0) {
                bestVoice = localeMatches.find(v => 
                    v.name.includes("Google") || 
                    v.name.includes("Natural") || 
                    v.name.includes("Premium") || 
                    v.name.includes("Microsoft")
                );
                if (!bestVoice) {
                    bestVoice = localeMatches.find(v => v.lang.toLowerCase().replace('_', '-').startsWith(matchLocale));
                }
                if (!bestVoice) {
                    bestVoice = localeMatches[0];
                }
            }
        }
        if (bestVoice) {
            utterance.voice = bestVoice;
        }
        window.speechSynthesis.speak(utterance);
    }

    // Copy to clipboard
    const copyBtn = document.getElementById("copyBtn");
    if (copyBtn && outputText) {
        copyBtn.addEventListener("click", () => {
            const text = outputText.value || outputText.innerText;
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
