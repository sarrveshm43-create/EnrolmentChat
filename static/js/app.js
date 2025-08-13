/**
 * MSU Enrollment Assistant - Main JavaScript
 */

// Function to update translations on the page
function updatePageTranslations(lang) {
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(element => {
        // Skip elements marked as static English
        if (element.hasAttribute('data-static-english')) {
            return;
        }
        const key = element.getAttribute('data-i18n');
        if (translations[lang] && translations[lang][key]) {
            // Handle input placeholders
            if (element.hasAttribute('placeholder')) {
                element.placeholder = translations[lang][key];
            } else {
                element.textContent = translations[lang][key];
            }
        }
    });
}

// Function to show only suggested questions for the selected language
function updateSuggestedQuestions(lang) {
    console.log(`Updating suggested questions for language: ${lang}`);
    const allQuestions = document.querySelectorAll('.suggested-question-btn');
    
    // First hide all questions
    allQuestions.forEach(question => {
        question.style.display = 'none';
    });
    
    // Then show only questions for the selected language
    const langQuestions = document.querySelectorAll(`.suggested-question-btn[data-language="${lang}"]`);
    langQuestions.forEach(question => {
        question.style.display = 'block';
    });
    
    console.log(`Found ${langQuestions.length} questions for language: ${lang}`);
}

document.addEventListener('DOMContentLoaded', function () {
    // Handle language selection
    const languageOptions = document.querySelectorAll('.language-option');
    if (languageOptions.length > 0) {
        languageOptions.forEach(option => {
            option.addEventListener('click', function (e) {
                e.preventDefault();
                const lang = this.getAttribute('data-lang');
                localStorage.setItem('preferred_language', lang);

                // Update language on server if we're on the chat page
                if (window.location.pathname === '/' || window.location.pathname === '/index.html') {
                    updateLanguageOnServer(lang);
                }

                // Update active language in UI
                document.querySelectorAll('.language-option').forEach(opt => {
                    opt.classList.remove('active');
                });
                this.classList.add('active');

                // Reinitialize click handlers for suggested questions after translation
                const suggestedQuestions = document.querySelectorAll('.suggested-question-btn');
                suggestedQuestions.forEach(question => {
                    // Remove any existing click handlers
                    question.onclick = null;
                    // Add new click handler
                    question.onclick = function(e) {
                        e.preventDefault(); // Prevent any default behavior
                        const text = this.textContent;
                        const messageInput = document.getElementById('message-input');
                        if (messageInput) {
                            messageInput.value = text;
                            const chatForm = document.getElementById('chat-form');
                            if (chatForm && !chatForm.submitting) {
                                chatForm.submitting = true; // Set flag to prevent double submission
                                chatForm.dispatchEvent(new Event('submit'));
                                setTimeout(() => {
                                    chatForm.submitting = false; // Reset flag after submission
                                }, 1000);
                            }
                            messageInput.value = '';
                        }
                    };
                });

                // Update translations on the page
                updatePageTranslations(lang);
                
                // STRICT LANGUAGE ENFORCEMENT
                // Update suggested questions for the selected language
                updateSuggestedQuestions(lang);
                
                // Store the strict language setting in localStorage for persistence
                localStorage.setItem('strict_language', lang);
                console.log(`STRICT ENFORCEMENT: Language set to ${lang} and will be strictly enforced`);

                // Update language dropdown text
                const dropdownButton = document.getElementById('languageDropdown');
                if (dropdownButton) {
                    const langText = translations[lang]?.language || 'English';
                    dropdownButton.innerHTML = `<i class="bi bi-translate me-1"></i> ${langText}`;
                }
            });
        });

        // Set active language based on localStorage
        const currentLang = localStorage.getItem('preferred_language') || 'en';
        const activeOption = document.querySelector(`.language-option[data-lang="${currentLang}"]`);
        if (activeOption) {
            activeOption.classList.add('active');
            // Update translations for initial page load
            updatePageTranslations(currentLang);
            // Update suggested questions for initial page load
            updateSuggestedQuestions(currentLang);
            // Update dropdown text
            const dropdownButton = document.getElementById('languageDropdown');
            if (dropdownButton) {
                const langText = translations[currentLang]?.language || 'English';
                dropdownButton.innerHTML = `<i class="bi bi-translate me-1"></i> ${langText}`;
            }
        }
    }

    // Function to update language preference on the server
    function updateLanguageOnServer(lang) {
        fetch('/language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ language: lang })
        })
            .then(response => response.json())
            .then(data => {
                console.log('Language updated on server:', data);
            })
            .catch(error => {
                console.error('Error updating language:', error);
            });
    }

    // Handle flash message dismissal
    const flashMessages = document.querySelectorAll('.alert-dismissible');
    if (flashMessages.length > 0) {
        flashMessages.forEach(alert => {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.addEventListener('click', function () {
                    alert.classList.add('fade');
                    setTimeout(() => {
                        alert.remove();
                    }, 300);
                });

                // Auto-dismiss success messages after 5 seconds
                if (alert.classList.contains('alert-success')) {
                    setTimeout(() => {
                        closeButton.click();
                    }, 5000);
                }
            }
        });
    }

    // Handle file input custom styling
    const fileInputs = document.querySelectorAll('input[type="file"]');
    if (fileInputs.length > 0) {
        fileInputs.forEach(input => {
            input.addEventListener('change', function () {
                const fileName = this.files[0]?.name;
                if (fileName) {
                    const label = this.nextElementSibling;
                    if (label && label.classList.contains('form-file-label')) {
                        label.textContent = fileName;
                    }
                }
            });
        });
    }

    // Mobile navigation improvements
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarNav = document.querySelector('#navbarNav');
    if (navbarToggler && navbarNav) {
        document.addEventListener('click', function (event) {
            const isNavbarOpen = navbarNav.classList.contains('show');
            if (isNavbarOpen && !navbarNav.contains(event.target) && event.target !== navbarToggler) {
                // Close navbar when clicking outside
                navbarToggler.click();
            }
        });
    }

    // Set active nav item based on current page
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (currentPath === link.getAttribute('href')) {
            link.classList.add('active');
        }
    });
}); 