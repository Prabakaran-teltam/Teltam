/**
 * AI Career & Productivity Assistant JS Engine
 * Handles AI Career Chatbot, Resume Evaluator, and AI Personal Assistant
 */

document.addEventListener('DOMContentLoaded', () => {

    // Helper: Retrieve CSRF Token from cookie or DOM
    function getCsrfToken() {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, 10) === ('csrftoken=')) {
                    cookieValue = decodeURIComponent(cookie.substring(10));
                    break;
                }
            }
        }
        return cookieValue || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    // Helper: Scroll chat window to bottom
    function scrollToBottom(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    // =========================================================================
    // 1. AI CAREER CHATBOT LOGIC
    // =========================================================================
    const careerChatMessages = document.getElementById('careerChatMessages');
    const careerChatForm = document.getElementById('careerChatForm');
    const careerInput = document.getElementById('careerInput');
    const careerTypingIndicator = document.getElementById('careerTypingIndicator');
    const clearCareerChatBtn = document.getElementById('clearCareerChatBtn');

    function appendCareerMessage(role, content) {
        if (!careerChatMessages) return;
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message-item ${role}`;
        
        if (role === 'user') {
            msgDiv.innerHTML = `
                <div class="msg-content-box shadow-sm">${escapeHtml(content)}</div>
            `;
        } else {
            msgDiv.innerHTML = `
                <div class="d-flex gap-2">
                    <div class="msg-avatar">🎯</div>
                    <div class="msg-content-box shadow-sm">${formatMessageContent(content)}</div>
                </div>
            `;
        }
        careerChatMessages.appendChild(msgDiv);
        scrollToBottom('careerChatMessages');
    }

    function sendCareerMessage(messageText) {
        if (!messageText || !messageText.trim()) return;

        appendCareerMessage('user', messageText);
        if (careerInput) careerInput.value = '';
        if (careerTypingIndicator) careerTypingIndicator.classList.remove('d-none');
        scrollToBottom('careerChatMessages');

        fetch('/api/ai/career/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ message: messageText })
        })
        .then(res => res.json())
        .then(data => {
            if (careerTypingIndicator) careerTypingIndicator.classList.add('d-none');
            if (data.success) {
                appendCareerMessage('assistant', data.response);
            } else {
                appendCareerMessage('assistant', '⚠️ ' + (data.error || 'Failed to get career advice.'));
            }
        })
        .catch(err => {
            console.error("Career Chat API Error:", err);
            if (careerTypingIndicator) careerTypingIndicator.classList.add('d-none');
            appendCareerMessage('assistant', '⚠️ Connection error. Please try again.');
        });
    }

    if (careerChatForm) {
        careerChatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = careerInput.value;
            sendCareerMessage(text);
        });
    }

    // Quick Action Career Pills Click Listener
    document.addEventListener('click', (e) => {
        if (e.target && e.target.classList.contains('career-pill')) {
            const careerRole = e.target.getAttribute('data-career');
            sendCareerMessage(`Tell me about a career as a ${careerRole}. What skills, learning roadmap, and projects do I need?`);
        }
    });

    if (clearCareerChatBtn) {
        clearCareerChatBtn.addEventListener('click', () => {
            fetch('/api/ai/clear-chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ type: 'career' })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success && careerChatMessages) {
                    careerChatMessages.innerHTML = `
                        <div class="chat-message-item assistant mb-3">
                            <div class="d-flex gap-2">
                                <div class="msg-avatar">🎯</div>
                                <div class="msg-content-box shadow-sm">
                                    <p class="mb-2">Hi! 👋 I'm your AI Career Advisor.</p>
                                    <p class="mb-2">I can help you explore AI career opportunities and create a learning roadmap.</p>
                                    <p class="mb-0 fw-semibold text-indigo-700">Choose a career path or ask me a question:</p>
                                </div>
                            </div>
                        </div>
                        <div class="quick-action-pills d-flex flex-wrap gap-2 ms-4 ps-2 mb-4" id="careerQuickPills">
                            <button type="button" class="btn btn-sm btn-outline-primary rounded-pill career-pill" data-career="Machine Learning Engineer">⚡ Machine Learning Engineer</button>
                            <button type="button" class="btn btn-sm btn-outline-primary rounded-pill career-pill" data-career="Data Scientist">⚡ Data Scientist</button>
                            <button type="button" class="btn btn-sm btn-outline-primary rounded-pill career-pill" data-career="AI Engineer">⚡ AI Engineer</button>
                            <button type="button" class="btn btn-sm btn-outline-primary rounded-pill career-pill" data-career="Generative AI Engineer">⚡ Generative AI Engineer</button>
                            <button type="button" class="btn btn-sm btn-outline-primary rounded-pill career-pill" data-career="Data Engineer">⚡ Data Engineer</button>
                        </div>
                    `;
                }
            });
        });
    }

    // =========================================================================
    // 2. RESUME EVALUATOR LOGIC
    // =========================================================================
    const resumeFileInput = document.getElementById('resumeFileInput');
    const resumeDropzone = document.getElementById('resumeDropzone');
    const browseResumeBtn = document.getElementById('browseResumeBtn');
    const selectedResumeFile = document.getElementById('selectedResumeFile');
    const resumeFileName = document.getElementById('resumeFileName');
    const resumeFileSize = document.getElementById('resumeFileSize');
    const removeResumeFileBtn = document.getElementById('removeResumeFileBtn');
    const targetRoleInput = document.getElementById('targetRoleInput');
    const resumeUploadForm = document.getElementById('resumeUploadForm');
    const resumeUploadSection = document.getElementById('resumeUploadSection');
    const resumeLoadingState = document.getElementById('resumeLoadingState');
    const resumeResultsSection = document.getElementById('resumeResultsSection');
    const evalAnotherResumeBtn = document.getElementById('evalAnotherResumeBtn');

    function handleFileSelection(file) {
        if (!file) return;
        const name = file.name;
        const ext = name.substring(name.lastIndexOf('.')).toLowerCase();
        if (ext !== '.pdf' && ext !== '.docx') {
            alert('Please select a PDF or DOCX resume file.');
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            alert('File size exceeds 10MB limit.');
            return;
        }

        if (resumeFileName) resumeFileName.innerText = name;
        if (resumeFileSize) resumeFileSize.innerText = `(${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
        if (selectedResumeFile) selectedResumeFile.classList.remove('d-none');
        if (resumeDropzone) resumeDropzone.classList.add('d-none');
    }

    if (browseResumeBtn && resumeFileInput) {
        browseResumeBtn.addEventListener('click', () => resumeFileInput.click());
    }

    if (resumeFileInput) {
        resumeFileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelection(e.target.files[0]);
            }
        });
    }

    if (resumeDropzone) {
        ['dragenter', 'dragover'].forEach(evt => {
            resumeDropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                resumeDropzone.style.borderColor = '#6366f1';
            });
        });
        ['dragleave', 'drop'].forEach(evt => {
            resumeDropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                resumeDropzone.style.borderColor = '#cbd5e1';
            });
        });
        resumeDropzone.addEventListener('drop', (e) => {
            if (e.dataTransfer.files.length > 0) {
                resumeFileInput.files = e.dataTransfer.files;
                handleFileSelection(e.dataTransfer.files[0]);
            }
        });
    }

    if (removeResumeFileBtn) {
        removeResumeFileBtn.addEventListener('click', () => {
            if (resumeFileInput) resumeFileInput.value = '';
            if (selectedResumeFile) selectedResumeFile.classList.add('d-none');
            if (resumeDropzone) resumeDropzone.classList.remove('d-none');
        });
    }

    if (resumeUploadForm) {
        resumeUploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (!resumeFileInput.files || resumeFileInput.files.length === 0) {
                alert('Please upload a PDF or DOCX resume file first.');
                return;
            }

            const formData = new FormData();
            formData.append('file', resumeFileInput.files[0]);
            if (targetRoleInput) formData.append('target_role', targetRoleInput.value);

            if (resumeUploadSection) resumeUploadSection.classList.add('d-none');
            if (resumeLoadingState) resumeLoadingState.classList.remove('d-none');

            fetch('/api/ai/resume/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken()
                },
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (resumeLoadingState) resumeLoadingState.classList.add('d-none');
                if (data.success) {
                    renderResumeResults(data);
                    if (resumeResultsSection) resumeResultsSection.classList.remove('d-none');
                } else {
                    if (resumeUploadSection) resumeUploadSection.classList.remove('d-none');
                    alert('Error: ' + (data.error || 'Failed to evaluate resume.'));
                }
            })
            .catch(err => {
                console.error("Resume Evaluator API Error:", err);
                if (resumeLoadingState) resumeLoadingState.classList.add('d-none');
                if (resumeUploadSection) resumeUploadSection.classList.remove('d-none');
                alert('Network connection error. Please try again.');
            });
        });
    }

    function renderResumeResults(data) {
        const evalData = data.evaluation || {};
        const score = evalData.score || 0;

        const overallScoreNum = document.getElementById('overallScoreNum');
        if (overallScoreNum) overallScoreNum.innerText = score;

        const scoreGradeTitle = document.getElementById('scoreGradeTitle');
        if (scoreGradeTitle) {
            if (score >= 85) scoreGradeTitle.innerText = "🌟 Excellent Resume";
            else if (score >= 70) scoreGradeTitle.innerText = "👍 Strong Resume";
            else if (score >= 55) scoreGradeTitle.innerText = "⚖️ Average Resume";
            else scoreGradeTitle.innerText = "⚠️ Needs Improvement";
        }

        const evaluatedRoleText = document.getElementById('evaluatedRoleText');
        if (evaluatedRoleText) evaluatedRoleText.innerText = `Evaluated for: ${data.target_role}`;

        const resumeSummaryText = document.getElementById('resumeSummaryText');
        if (resumeSummaryText) resumeSummaryText.innerText = evalData.summary || '';

        // Render Category Breakdown Grid
        const grid = document.getElementById('categoryBreakdownGrid');
        if (grid && evalData.breakdown) {
            const b = evalData.breakdown;
            grid.innerHTML = `
                <div class="col-6"><div class="p-2.5 bg-light rounded-3 text-center"><small class="text-muted d-block mb-1">Structure</small><strong class="h6 mb-0 text-slate-900">${b.structure || 0}%</strong></div></div>
                <div class="col-6"><div class="p-2.5 bg-light rounded-3 text-center"><small class="text-muted d-block mb-1">Skills Relevance</small><strong class="h6 mb-0 text-slate-900">${b.skills || 0}%</strong></div></div>
                <div class="col-6"><div class="p-2.5 bg-light rounded-3 text-center"><small class="text-muted d-block mb-1">Experience</small><strong class="h6 mb-0 text-slate-900">${b.experience || 0}%</strong></div></div>
                <div class="col-6"><div class="p-2.5 bg-light rounded-3 text-center"><small class="text-muted d-block mb-1">Projects</small><strong class="h6 mb-0 text-slate-900">${b.projects || 0}%</strong></div></div>
                <div class="col-6"><div class="p-2.5 bg-light rounded-3 text-center"><small class="text-muted d-block mb-1">Keywords</small><strong class="h6 mb-0 text-slate-900">${b.keywords || 0}%</strong></div></div>
                <div class="col-6"><div class="p-2.5 bg-light rounded-3 text-center"><small class="text-muted d-block mb-1">Content Quality</small><strong class="h6 mb-0 text-slate-900">${b.content_quality || 0}%</strong></div></div>
            `;
        }

        // Existing Skills
        const existingBadges = document.getElementById('existingSkillsBadges');
        if (existingBadges) {
            const skills = evalData.existing_skills || [];
            existingBadges.innerHTML = skills.length > 0 
                ? skills.map(s => `<span class="badge bg-success-subtle text-success border border-success-subtle rounded-pill px-2.5 py-1">${escapeHtml(s)}</span>`).join(' ')
                : '<span class="text-muted small">No specific technical skills detected.</span>';
        }

        // Missing Skills
        const missingBadges = document.getElementById('missingSkillsBadges');
        if (missingBadges) {
            const missing = evalData.missing_skills || [];
            missingBadges.innerHTML = missing.length > 0 
                ? missing.map(s => `<span class="badge bg-danger-subtle text-danger border border-danger-subtle rounded-pill px-2.5 py-1">${escapeHtml(s)}</span>`).join(' ')
                : '<span class="text-muted small">No critical missing skills.</span>';
        }

        // Strengths List
        const strengthsList = document.getElementById('strengthsList');
        if (strengthsList) {
            const items = evalData.strengths || [];
            strengthsList.innerHTML = items.map(st => `<li class="mb-1.5"><i class="fas fa-check text-success me-2"></i> ${escapeHtml(st)}</li>`).join('');
        }

        // Weaknesses List
        const weaknessesList = document.getElementById('weaknessesList');
        if (weaknessesList) {
            const items = evalData.weaknesses || [];
            weaknessesList.innerHTML = items.map(w => `<li class="mb-1.5"><i class="fas fa-times text-danger me-2"></i> ${escapeHtml(w)}</li>`).join('');
        }

        // Recommendations List
        const recommendationsList = document.getElementById('recommendationsList');
        if (recommendationsList) {
            const items = evalData.recommendations || [];
            recommendationsList.innerHTML = items.map((r, i) => `<li class="mb-2 d-flex gap-2"><strong>${i+1}.</strong> <span>${escapeHtml(r)}</span></li>`).join('');
        }
    }

    if (evalAnotherResumeBtn) {
        evalAnotherResumeBtn.addEventListener('click', () => {
            if (resumeResultsSection) resumeResultsSection.classList.add('d-none');
            if (resumeUploadSection) resumeUploadSection.classList.remove('d-none');
            if (resumeFileInput) resumeFileInput.value = '';
            if (selectedResumeFile) selectedResumeFile.classList.add('d-none');
            if (resumeDropzone) resumeDropzone.classList.remove('d-none');
        });
    }

    // =========================================================================
    // 3. AI PERSONAL ASSISTANT LOGIC
    // =========================================================================
    const assistantChatMessages = document.getElementById('assistantChatMessages');
    const assistantChatForm = document.getElementById('assistantChatForm');
    const assistantInput = document.getElementById('assistantInput');
    const assistantTypingIndicator = document.getElementById('assistantTypingIndicator');
    const clearAssistantChatBtn = document.getElementById('clearAssistantChatBtn');

    function appendAssistantMessage(role, content) {
        if (!assistantChatMessages) return;
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message-item ${role}`;
        
        if (role === 'user') {
            msgDiv.innerHTML = `
                <div class="msg-content-box shadow-sm">${escapeHtml(content)}</div>
            `;
        } else {
            msgDiv.innerHTML = `
                <div class="d-flex gap-2">
                    <div class="msg-avatar">🤖</div>
                    <div class="msg-content-box shadow-sm">${formatMessageContent(content)}</div>
                </div>
            `;
        }
        assistantChatMessages.appendChild(msgDiv);
        scrollToBottom('assistantChatMessages');
    }

    function sendAssistantMessage(messageText) {
        if (!messageText || !messageText.trim()) return;

        appendAssistantMessage('user', messageText);
        if (assistantInput) assistantInput.value = '';
        if (assistantTypingIndicator) assistantTypingIndicator.classList.remove('d-none');
        scrollToBottom('assistantChatMessages');

        fetch('/api/ai/assistant/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ message: messageText })
        })
        .then(res => res.json())
        .then(data => {
            if (assistantTypingIndicator) assistantTypingIndicator.classList.add('d-none');
            if (data.success) {
                appendAssistantMessage('assistant', data.response);
            } else {
                appendAssistantMessage('assistant', '⚠️ ' + (data.error || 'Failed to process request.'));
            }
        })
        .catch(err => {
            console.error("Personal Assistant API Error:", err);
            if (assistantTypingIndicator) assistantTypingIndicator.classList.add('d-none');
            appendAssistantMessage('assistant', '⚠️ Connection error. Please try again.');
        });
    }

    if (assistantChatForm) {
        assistantChatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = assistantInput.value;
            sendAssistantMessage(text);
        });
    }

    // Quick Action Shortcuts Click Listener
    document.addEventListener('click', (e) => {
        if (e.target && e.target.classList.contains('assistant-pill')) {
            const promptText = e.target.getAttribute('data-prompt');
            sendAssistantMessage(promptText);
        }
    });

    if (clearAssistantChatBtn) {
        clearAssistantChatBtn.addEventListener('click', () => {
            fetch('/api/ai/clear-chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ type: 'assistant' })
            })
            .then(res => res.json())
            .then(data => {
                if (data.success && assistantChatMessages) {
                    assistantChatMessages.innerHTML = `
                        <div class="chat-message-item assistant mb-3">
                            <div class="d-flex gap-2">
                                <div class="msg-avatar">🤖</div>
                                <div class="msg-content-box shadow-sm">
                                    <p class="mb-2">Hello! 👋 I'm your AI Personal Assistant.</p>
                                    <p class="mb-0">How can I assist you today? I can help write emails, answer general questions, summarize articles, explain concepts, or brainstorm ideas.</p>
                                </div>
                            </div>
                        </div>
                        <div class="quick-action-pills d-flex flex-wrap gap-2 ms-4 ps-2 mb-4" id="assistantQuickPills">
                            <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill assistant-pill" data-prompt="Write an email requesting 2 days leave for medical reasons.">✉️ Draft an email</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill assistant-pill" data-prompt="Explain Machine Learning in simple terms for a beginner.">💡 Explain ML simply</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill assistant-pill" data-prompt="Give me 3 unique Python web development project ideas for a portfolio.">🚀 Python project ideas</button>
                            <button type="button" class="btn btn-sm btn-outline-secondary rounded-pill assistant-pill" data-prompt="Summarize the core benefits of using Django for web applications.">📝 Summarize Django</button>
                        </div>
                    `;
                }
            });
        });
    }

    // Utility: HTML Escaper
    function escapeHtml(str) {
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Utility: Format AI Message Markdown (bold, linebreaks, code snippets)
    function formatMessageContent(str) {
        let escaped = escapeHtml(str);
        // Replace bold **text**
        escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Replace bullet points
        escaped = escaped.replace(/^[\*\-] (.*$)/gim, '• $1');
        // Convert double linebreaks to paragraphs/br
        return escaped.replace(/\n/g, '<br>');
    }

});
