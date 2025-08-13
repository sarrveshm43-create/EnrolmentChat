/**
 * MSU Enrollment Assistant Chat Interface
 * Handles user interactions, message sending, and chat display
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get DOM elements
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const chatForm = document.getElementById('chat-form');
    const loadingIndicator = document.getElementById('loading-indicator');
    const suggestedQuestions = document.querySelectorAll('.suggested-question-btn');
    const clearChatButton = document.getElementById('clear-chat');
    const sendButton = document.getElementById('send-button');
    const languageDropdown = document.getElementById('languageDropdown');

    // State variables
    let isMessageInProgress = false;

    // Debug element presence
    console.log('Elements found:', {
        chatMessages: !!chatMessages,
        messageInput: !!messageInput,
        chatForm: !!chatForm,
        loadingIndicator: !!loadingIndicator,
        clearChatButton: !!clearChatButton,
        suggestedQuestions: suggestedQuestions.length,
        sendButton: !!sendButton,
        languageDropdown: !!languageDropdown
    });

    /**
     * Add a message to the chat
     * @param {string} text - The message text
     * @param {boolean} isUser - Whether the message is from the user
     */
    function addMessage(text, isUser) {
        if (!chatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Format bot messages as HTML if they contain HTML tags
        if (!isUser && text.includes('<')) {
            contentDiv.innerHTML = text;
        } else {
            contentDiv.textContent = text;
        }
        
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    /**
     * Scroll chat window to bottom
     */
    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    /**
     * Get current language from dropdown
     */
    function getCurrentLanguage() {
        if (languageDropdown) {
            // Get language code based on button text content
            const buttonText = languageDropdown.textContent.trim();
            
            // Map button text to language code
            if (buttonText.includes('中文')) {
                return 'zh';
            } else if (buttonText.includes('Español')) {
                return 'es';
            } else if (buttonText.includes('Bahasa')) {
                return 'ms';
            } else {
                return 'en'; // Default to English
            }
        }
        return 'en'; // Default to English
    }

    /**
     * Show welcome message in current language
     */
    function showWelcomeMessage() {
        // Check if welcome message already exists
        const welcomeSpan = document.querySelector('span[data-i18n="welcome_message"]');
        if (welcomeSpan) {
            console.log('Welcome message already exists');
            return;
        }
        
        // Create welcome message if it doesn't exist
        const currentLanguage = getCurrentLanguage();
        const translations = window.translations ? (window.translations[currentLanguage] || window.translations['en']) : {};
        const welcomeMessage = translations['welcome_message'] || 'Welcome to MSU\'s 24/7 Enrollment Advisor!';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const span = document.createElement('span');
        span.setAttribute('data-i18n', 'welcome_message');
        span.textContent = welcomeMessage;
        
        contentDiv.appendChild(span);
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
    }

    /**
     * Debounce function to prevent multiple rapid clicks
     */
    function debounce(func, wait) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    }

    /**
     * Initialize chat session
     */
    async function initializeSession() {
        try {
            // Show welcome message
            showWelcomeMessage();
            
            // Initialize session with server
            const currentLanguage = getCurrentLanguage();
            const response = await fetch('/api/chat/initialize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    language: currentLanguage
                }),
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error('Failed to initialize session');
            }
            
            const data = await response.json();
            console.log('Session initialized:', data);
        } catch (error) {
            console.error('Error initializing session:', error);
        }
    }

    /**
     * Clear chat history
     */
    async function clearChat() {
        if (isMessageInProgress) return;
        
        isMessageInProgress = true;
        const currentLanguage = getCurrentLanguage();
        const translations = window.translations ? (window.translations[currentLanguage] || window.translations['en']) : {};
        
        try {
            // Find welcome message
            const welcomeMessage = Array.from(chatMessages.children).find(child => {
                return child.querySelector('span[data-i18n="welcome_message"]');
            });
            
            // Clear all messages
            chatMessages.innerHTML = '';
            
            // Restore welcome message if it existed
            if (welcomeMessage) {
                chatMessages.appendChild(welcomeMessage);
            }
            
            // Show success message
            const successDiv = document.createElement('div');
            successDiv.className = 'alert alert-success';
            successDiv.textContent = translations.clear_success || 'Chat history cleared successfully';
            chatMessages.insertBefore(successDiv, chatMessages.firstChild);
            
            // Remove success message after 3 seconds
            setTimeout(() => {
                successDiv.remove();
            }, 3000);
            
            // Clear on server side
            const response = await fetch('/api/chat/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error('Failed to clear chat history');
            }
            
            // Clear session storage if needed
            sessionStorage.removeItem('chatHistory');
            console.log('Chat history cleared successfully');
            
        } catch (error) {
            console.error('Error clearing chat history:', error);
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger';
            errorDiv.textContent = translations.clear_error || 'Failed to clear chat history';
            chatMessages.insertBefore(errorDiv, chatMessages.firstChild);
        } finally {
            isMessageInProgress = false;
        }
    }

    /**
     * Send a message to the server
     * @param {string} message - Message text to send
     * @param {boolean} isUserMessage - Whether this is from the user or suggested
     */
    async function sendMessage(message, isUserMessage = true) {
        if (isMessageInProgress || !message) return;
        isMessageInProgress = true;
        
        // STRICT LANGUAGE ENFORCEMENT
        // Get current language from dropdown - this is the mandatory language for all interactions
        const currentLanguage = getCurrentLanguage();
        const translations = window.translations ? (window.translations[currentLanguage] || window.translations['en']) : {};
        
        console.log(`STRICT ENFORCEMENT: Sending message with mandatory language: ${currentLanguage}`);
        
        // Store the strict language setting in localStorage for persistence
        localStorage.setItem('strict_language', currentLanguage);
        
        // Add user message to chat if it's a user message
        if (isUserMessage) {
            addMessage(message, true);
        }
        
        try {
            // Show loading indicator
            if (loadingIndicator) {
                loadingIndicator.style.display = 'block';
            }
            
            // Send message to server
            const response = await fetch('/api/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    language: currentLanguage
                }),
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            
            const data = await response.json();
            console.log('Server response:', data);
            
            // Hide loading indicator
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            
            // Add bot response to chat
            if (data && data.bot_response && data.bot_response.text) {
                addMessage(data.bot_response.text, false);
                scrollToBottom();
            }
            
        } catch (error) {
            console.error('Error sending message:', error);
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
            
            // Show error message
            const errorMessage = translations.error_message || 'An error occurred. Please try again.';
            addMessage(errorMessage, false);
        } finally {
            isMessageInProgress = false;
        }
    }

    /**
     * Setup suggested questions click handlers
     */
    function setupSuggestedQuestions() {
        const buttons = document.querySelectorAll('.suggested-question-btn');
        buttons.forEach(button => {
            // Remove any existing listeners to avoid duplicates
            const newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
            
            // Add click handler
            newButton.addEventListener('click', async function() {
                if (isMessageInProgress) return;
                
                const question = this.textContent.trim();
                if (question) {
                    // STRICT LANGUAGE ENFORCEMENT for suggested questions
                    // Get the language attribute from the button - this is mandatory
                    const buttonLanguage = this.getAttribute('data-language');
                    
                    if (!buttonLanguage) {
                        console.error('STRICT ENFORCEMENT ERROR: Suggested question missing language attribute');
                        return; // Don't proceed if no language attribute is found
                    }
                    
                    // Enforce the language from the button attribute
                    // This ensures suggested questions always use their specified language
                    let originalLanguage = null;
                    if (languageDropdown) {
                        originalLanguage = languageDropdown.value;
                        languageDropdown.value = buttonLanguage;
                        console.log(`STRICT ENFORCEMENT: Using button's mandatory language: ${buttonLanguage} for suggested question`);
                        
                        // Store the strict language setting in localStorage for persistence
                        localStorage.setItem('strict_language', buttonLanguage);
                    }
                    
                    this.disabled = true;
                    try {
                        // Send the message with the current language (which may have been set from the button)
                        await sendMessage(question, true);
                    } catch (error) {
                        console.error('Error sending suggested question:', error);
                    } finally {
                        // Restore original language if we changed it
                        if (originalLanguage !== null && languageDropdown) {
                            languageDropdown.value = originalLanguage;
                        }
                        this.disabled = false;
                    }
                }
            });
        });
    }

    // Set up event listeners
    // ----------------------

    // Handle form submission
    if (chatForm) {
        chatForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            if (!messageInput || isMessageInProgress) return;

            const message = messageInput.value.trim();
            if (message) {
                // Disable form during submission
                messageInput.disabled = true;
                if (sendButton) sendButton.disabled = true;

                try {
                    await sendMessage(message, true);
                    messageInput.value = ''; // Clear input after sending
                } catch (error) {
                    console.error('Error sending message:', error);
                } finally {
                    // Re-enable form
                    messageInput.disabled = false;
                    if (sendButton) sendButton.disabled = false;
                    messageInput.focus();
                }
            }
        });
    }

    // Handle clear chat button
    if (clearChatButton) {
        const debouncedClearChat = debounce(clearChat, 500);
        clearChatButton.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled || isMessageInProgress) return;
            
            this.disabled = true;
            debouncedClearChat();
            setTimeout(() => {
                this.disabled = false;
            }, 1000); // Re-enable after 1 second
        });
    }

    // Initialize
    setupSuggestedQuestions();
    initializeSession();
});
