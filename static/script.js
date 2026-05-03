document.addEventListener('DOMContentLoaded', () => {
    const tasksContainer = document.getElementById('tasks-container');
    const addTaskBtn = document.getElementById('add-task-btn');
    const generateBtn = document.getElementById('generate-btn');
    const resultSection = document.getElementById('result-section');
    const promptOutput = document.getElementById('prompt-output');
    const copyBtn = document.getElementById('copy-btn');

    // Function to handle removing a task
    const handleRemoveTask = (e) => {
        const wrapper = e.currentTarget.closest('.task-input-wrapper');
        const allWrappers = tasksContainer.querySelectorAll('.task-input-wrapper');
        if (allWrappers.length > 1) {
            wrapper.remove();
        }
        updateRemoveButtons();
    };

    // Function to update the disabled state of remove buttons
    const updateRemoveButtons = () => {
        const removeBtns = tasksContainer.querySelectorAll('.remove-task');
        if (removeBtns.length === 1) {
            removeBtns[0].disabled = true;
        } else {
            removeBtns.forEach(btn => btn.disabled = false);
        }
    };

    // Add new task input
    addTaskBtn.addEventListener('click', () => {
        const newWrapper = document.createElement('div');
        newWrapper.className = 'task-input-wrapper';
        newWrapper.innerHTML = `
            <input type="text" class="task-input" placeholder="Another task...">
            <button class="icon-btn remove-task" aria-label="Remove task">
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;
        
        // Add event listener to the new remove button
        const removeBtn = newWrapper.querySelector('.remove-task');
        removeBtn.addEventListener('click', handleRemoveTask);
        
        tasksContainer.appendChild(newWrapper);
        newWrapper.querySelector('input').focus();
        
        updateRemoveButtons();
    });

    // Initial setup for the first remove button
    const initialRemoveBtn = tasksContainer.querySelector('.remove-task');
    initialRemoveBtn.addEventListener('click', handleRemoveTask);
    updateRemoveButtons();

    // Generate Prompt
    generateBtn.addEventListener('click', () => {
        const domain = document.getElementById('domain').value;
        const audience = document.getElementById('audience').value;
        const idea = document.getElementById('idea').value.trim();
        const achievement = document.getElementById('achievement').value.trim();
        const constraints = document.getElementById('constraints').value.trim();
        
        // Collect all non-empty tasks
        const taskInputs = tasksContainer.querySelectorAll('.task-input');
        const tasks = Array.from(taskInputs)
            .map(input => input.value.trim())
            .filter(val => val !== '');

        if (!idea && tasks.length === 0 && !achievement) {
            alert('Please fill in at least the core idea, a task, or a goal.');
            return;
        }

        // Build the prompt using rigorous formatting
        let promptText = `**Role**: Act as a leading expert in ${domain}.\n`;
        promptText += `**Target Audience**: Your response should be tailored for a ${audience}.\n\n`;

        if (idea) {
            promptText += `### Context / Core Idea\n${idea}\n\n`;
        }

        if (tasks.length > 0) {
            promptText += `### Required Tasks\nPlease accomplish the following specific tasks:\n`;
            tasks.forEach(task => {
                promptText += `- ${task}\n`;
            });
            promptText += `\n`;
        }

        if (achievement) {
            promptText += `### Ultimate Goal\n${achievement}\n\n`;
        }

        if (constraints) {
            promptText += `### Constraints & Formatting Rules\nYou must strictly adhere to the following constraints:\n${constraints}\n\n`;
        }

        promptText += `### Additional Instructions\nProvide a comprehensive, highly accurate, and rigorous response. If you require further clarification to provide the best possible output, please state your questions before answering.`;

        // Display loading state
        promptOutput.textContent = "Connecting to AI... Please wait...";
        resultSection.classList.remove('hidden');
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';

        // Call the backend API
        fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt: promptText })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                promptOutput.textContent = "Error: " + data.error;
            } else {
                promptOutput.textContent = data.result;
            }
        })
        .catch(err => {
            promptOutput.textContent = "Error connecting to server. Is the backend running?";
            console.error(err);
        })
        .finally(() => {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Precision Prompt';
        });
    });

    // Copy to Clipboard
    copyBtn.addEventListener('click', () => {
        const textToCopy = promptOutput.textContent;
        navigator.clipboard.writeText(textToCopy).then(() => {
            // Visual feedback
            const icon = copyBtn.querySelector('i');
            const tooltip = copyBtn.querySelector('.tooltip-text');
            
            icon.classList.remove('fa-regular', 'fa-copy');
            icon.classList.add('fa-solid', 'fa-check');
            icon.style.color = 'var(--success-color)';
            tooltip.textContent = 'Copied!';
            
            setTimeout(() => {
                icon.classList.remove('fa-solid', 'fa-check');
                icon.classList.add('fa-regular', 'fa-copy');
                icon.style.color = '';
                tooltip.textContent = 'Copy';
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            alert('Failed to copy to clipboard.');
        });
    });
});
