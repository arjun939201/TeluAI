const chatContainer =
    document.getElementById("chatContainer");

const welcome =
    document.getElementById("welcome");

const chatForm =
    document.getElementById("chatForm");

const messageInput =
    document.getElementById("messageInput");

const sendButton =
    document.getElementById("sendButton");

const clearButton =
    document.getElementById("clearButton");

const mobileNewChat =
    document.getElementById("mobileNewChat");

const standardMode =
    document.getElementById("standardMode");

const melimiMode =
    document.getElementById("melimiMode");

const modelName =
    document.getElementById("modelName");


let mode = "melimi";

let history = [];

let isSending = false;


// ============================================================
// MODE
// ============================================================

function setMode(newMode) {

    if (
        newMode !== "standard" &&
        newMode !== "melimi"
    ) {
        return;
    }


    const changed =
        mode !== newMode;


    mode = newMode;


    // --------------------------------------------------------
    // Update buttons
    // --------------------------------------------------------

    if (standardMode) {

        standardMode.classList.toggle(
            "active",
            mode === "standard"
        );

    }


    if (melimiMode) {

        melimiMode.classList.toggle(
            "active",
            mode === "melimi"
        );

    }


    // --------------------------------------------------------
    // Update header / placeholder
    // --------------------------------------------------------

    if (mode === "melimi") {

        if (modelName) {

            modelName.textContent =
                "మేలిమి తెలుగు AI";

        }


        messageInput.placeholder =
            "మేలిమి తెలుగులో అడుగు...";

    } else {

        if (modelName) {

            modelName.textContent =
                "తెలుగు AI";

        }


        messageInput.placeholder =
            "తెలుగులో అడుగు...";

    }


    // --------------------------------------------------------
    // IMPORTANT:
    // A mode change starts a fresh conversation.
    //
    // Otherwise Standard-mode history would be sent into
    // Melimi mode and vice versa.
    // --------------------------------------------------------

    if (changed) {

        resetChat();

    }

}


// ============================================================
// MODE BUTTONS
// ============================================================

if (standardMode) {

    standardMode.addEventListener(
        "click",
        function() {

            setMode(
                "standard"
            );

        }
    );

}


if (melimiMode) {

    melimiMode.addEventListener(
        "click",
        function() {

            setMode(
                "melimi"
            );

        }
    );

}


// ============================================================
// MESSAGE
// ============================================================

function addMessage(
    text,
    role,
    melimi = false
) {

    const wrapper =
        document.createElement(
            "div"
        );


    wrapper.className =
        `message ${role}`;


    if (
        role === "assistant" &&
        melimi
    ) {

        wrapper.classList.add(
            "melimi"
        );

    }


    const content =
        document.createElement(
            "div"
        );


    content.className =
        "message-content";


    content.textContent =
        text;


    wrapper.appendChild(
        content
    );


    chatContainer.appendChild(
        wrapper
    );


    scrollToBottom();
}


// ============================================================
// TYPING
// ============================================================

function showTyping() {

    const wrapper =
        document.createElement(
            "div"
        );


    wrapper.id =
        "typingIndicator";


    wrapper.className =
        "typing-message";


    wrapper.innerHTML = `
        <div class="typing">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;


    chatContainer.appendChild(
        wrapper
    );


    scrollToBottom();
}


function removeTyping() {

    const typing =
        document.getElementById(
            "typingIndicator"
        );


    if (typing) {

        typing.remove();

    }

}


// ============================================================
// ERROR
// ============================================================

function addError(text) {

    const wrapper =
        document.createElement(
            "div"
        );


    wrapper.className =
        "error-message";


    const error =
        document.createElement(
            "div"
        );


    error.className =
        "error";


    error.textContent =
        text;


    wrapper.appendChild(
        error
    );


    chatContainer.appendChild(
        wrapper
    );


    scrollToBottom();
}


// ============================================================
// SCROLL
// ============================================================

function scrollToBottom() {

    requestAnimationFrame(
        function() {

            chatContainer.scrollTop =
                chatContainer.scrollHeight;

        }
    );

}


// ============================================================
// TEXTAREA
// ============================================================

function resizeInput() {

    messageInput.style.height =
        "auto";


    const height =
        Math.min(
            messageInput.scrollHeight,
            160
        );


    messageInput.style.height =
        `${height}px`;

}


messageInput.addEventListener(
    "input",
    resizeInput
);


// ============================================================
// SEND
// ============================================================

async function sendMessage() {

    if (isSending) {

        return;

    }


    const text =
        messageInput.value.trim();


    if (!text) {

        return;

    }


    isSending = true;


    sendButton.disabled =
        true;


    messageInput.value =
        "";


    resizeInput();


    if (welcome) {

        welcome.style.display =
            "none";

    }


    // --------------------------------------------------------
    // Show user message
    // --------------------------------------------------------

    addMessage(
        text,
        "user"
    );


    // --------------------------------------------------------
    // Copy current history BEFORE adding this turn.
    // --------------------------------------------------------

    const previousHistory =
        [...history];


    showTyping();


    try {

        const response =
            await fetch(
                "/chat",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            {

                                message:
                                    text,

                                mode:
                                    mode,

                                history:
                                    previousHistory

                            }
                        )

                }
            );


        const data =
            await response
                .json()
                .catch(
                    () => ({})
                );


        removeTyping();


        if (!response.ok) {

            addError(
                data.detail ||
                `సర్వర్ లోపం: ${response.status}`
            );

            return;

        }


        const reply =
            data.reply;


        if (!reply) {

            addError(
                "AI నుండి సమాధానం రాలేదు."
            );

            return;

        }


        // ----------------------------------------------------
        // Show response using CURRENT mode
        // ----------------------------------------------------

        addMessage(
            reply,
            "assistant",
            mode === "melimi"
        );


        // ----------------------------------------------------
        // Save current conversation
        // ----------------------------------------------------

        history.push(
            {
                role: "user",
                content: text
            }
        );


        history.push(
            {
                role: "assistant",
                content: reply
            }
        );


    } catch (error) {

        removeTyping();


        console.error(
            "TeluAI error:",
            error
        );


        addError(
            "సర్వర్‌ను చేరుకోలేకపోయాము. మళ్లీ ప్రయత్నించు."
        );


    } finally {

        isSending =
            false;


        sendButton.disabled =
            false;


        messageInput.focus();

    }

}


// ============================================================
// FORM SUBMIT
// ============================================================

chatForm.addEventListener(
    "submit",
    function(event) {

        event.preventDefault();

        sendMessage();

    }
);


// ============================================================
// ENTER
// ============================================================

messageInput.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {

            event.preventDefault();

            sendMessage();

        }

    }
);


// ============================================================
// SUGGESTIONS
// ============================================================

document
    .querySelectorAll(
        ".suggestion"
    )
    .forEach(
        function(button) {

            button.addEventListener(
                "click",
                function() {

                    const text =
                        this.dataset.message;


                    if (!text) {

                        return;

                    }


                    messageInput.value =
                        text;


                    resizeInput();


                    sendMessage();

                }
            );

        }
    );


// ============================================================
// RESET CHAT
// ============================================================

function resetChat() {

    history = [];


    const messages =
        chatContainer.querySelectorAll(
            ".message, .error-message, .typing-message"
        );


    messages.forEach(
        function(message) {

            message.remove();

        }
    );


    if (welcome) {

        welcome.style.display =
            "";

    }


    messageInput.value =
        "";


    resizeInput();


    messageInput.focus();

}


// ============================================================
// NEW CHAT
// ============================================================

function newChat() {

    resetChat();

}


if (clearButton) {

    clearButton.addEventListener(
        "click",
        newChat
    );

}


if (mobileNewChat) {

    mobileNewChat.addEventListener(
        "click",
        newChat
    );

}


// ============================================================
// START
// ============================================================

setMode(
    "melimi"
);


resizeInput();


messageInput.focus();
