// Global state
let currentUser = {
    email: null,
    credits: 3,
    isPremium: false
};

// Utility Functions
function scrollToTools() {
    document.querySelector('.email-section').scrollIntoView({ 
        behavior: 'smooth',
        block: 'center'
    });
}

function switchTab(tabName) {
    // Remove active class from all tabs and content
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    // Add active class to selected tab and content
    event.target.closest('.tab').classList.add('active');
    document.getElementById(tabName).classList.add('active');
}

// Email Submission
async function handleEmailSubmit() {
    const email = document.getElementById('email').value.trim();
    
    if (!email || !isValidEmail(email)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/user/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        
        if (!response.ok) throw new Error('Failed to login');
        
        const data = await response.json();
        
        // Update global state
        currentUser.email = email;
        currentUser.credits = data.credits;
        currentUser.isPremium = data.is_premium;
        
        // Update UI
        updateCreditsDisplay();
        showNotification('Welcome! You can now use all tools.', 'success');
        
    } catch (error) {
        console.error('Login error:', error);
        showNotification('Error logging in. Please try again.', 'error');
    }
}

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function updateCreditsDisplay() {
    const display = document.getElementById('credits-display');
    if (currentUser.isPremium) {
        display.innerHTML = '<i class="fas fa-infinity"></i> Premium: Unlimited';
    } else {
        display.innerHTML = `<i class="fas fa-bolt"></i> ${currentUser.credits} Free Resumes Left`;
    }
}

// Job Validation
async function validateJob() {
    const jobDesc = document.getElementById('val-job-desc').value.trim();
    const company = document.getElementById('val-company').value.trim();
    const title = document.getElementById('val-title').value.trim();
    
    if (!jobDesc) {
        showNotification('Please paste a job description', 'error');
        return;
    }
    
    if (!currentUser.email) {
        showNotification('Please enter your email first', 'error');
        scrollToTools();
        return;
    }
    
    try {
        const response = await fetch('/api/validate-job', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: currentUser.email,
                job_description: jobDesc,
                company_name: company,
                job_title: title
            })
        });
        
        if (!response.ok) throw new Error('Validation failed');
        
        const data = await response.json();
        
        // Show results
        const resultsDiv = document.getElementById('validation-results');
        const contentDiv = document.getElementById('validation-content');
        
        resultsDiv.classList.add('active');
        contentDiv.innerHTML = formatValidationResults(data);
        
    } catch (error) {
        console.error('Validation error:', error);
        showNotification('Error validating job posting. Please try again.', 'error');
    }
}

function formatValidationResults(data) {
    const scoreColor = data.score >= 80 ? '#10b981' : data.score >= 50 ? '#f59e0b' : '#ef4444';
    
    return `
        <div style="background: white; padding: 2rem; border-radius: 8px; margin-bottom: 1rem;">
            <div style="text-align: center; margin-bottom: 2rem;">
                <div style="font-size: 3rem; font-weight: 700; color: ${scoreColor};">
                    ${data.score}/100
                </div>
                <p style="color: var(--gray); margin-top: 0.5rem;">Legitimacy Score</p>
            </div>
            <div style="border-top: 1px solid var(--gray-light); padding-top: 1.5rem;">
                <h4 style="color: var(--navy); margin-bottom: 1rem;">Analysis Summary</h4>
                <div style="color: var(--gray); line-height: 1.8;">
                    ${data.summary || data.report}
                </div>
            </div>
        </div>
    `;
}

// Resume Optimization
async function optimizeResume() {
    const fileInput = document.getElementById('resume-file');
    const jobDesc = document.getElementById('opt-job-desc').value.trim();
    const company = document.getElementById('opt-company').value.trim();
    
    if (!fileInput.files[0] || !jobDesc) {
        showNotification('Please upload your resume and paste the job description', 'error');
        return;
    }
    
    if (!currentUser.email) {
        showNotification('Please enter your email first', 'error');
        scrollToTools();
        return;
    }
    
    // Check credits
    if (!currentUser.isPremium && currentUser.credits <= 0) {
        showUpgradePrompt();
        return;
    }
    
    // Show loading
    document.getElementById('loading-optimizer').classList.add('active');
    document.getElementById('optimizer-results').classList.remove('active');
    
    const formData = new FormData();
    formData.append('resume', fileInput.files[0]);
    formData.append('job_description', jobDesc);
    formData.append('company_name', company);
    formData.append('email', currentUser.email);
    
    try {
        const response = await fetch('/api/optimize-resume', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Optimization failed');
        
        const data = await response.json();
        
        // Hide loading
        document.getElementById('loading-optimizer').classList.remove('active');
        
        // Update credits
        if (!currentUser.isPremium) {
            currentUser.credits = data.credits_remaining;
            updateCreditsDisplay();
        }
        
        // Show results
        displayResumeResults(data);
        
    } catch (error) {
        console.error('Optimization error:', error);
        document.getElementById('loading-optimizer').classList.remove('active');
        showNotification('Error optimizing resume. Please try again.', 'error');
    }
}

function displayResumeResults(data) {
    const resultsDiv = document.getElementById('optimizer-results');
    const contentDiv = document.getElementById('optimizer-content');
    
    // Update scores
    document.getElementById('original-score').textContent = data.original_score || '--';
    document.getElementById('optimized-score').textContent = data.optimized_score || '--';
    
    // Display optimized resume
    contentDiv.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px; margin-bottom: 1rem;">
            <h4 style="color: var(--navy); margin-bottom: 1rem;">Optimized Resume Preview</h4>
            <div style="white-space: pre-wrap; line-height: 1.8; color: var(--gray);">
                ${data.optimized_resume || data.resume_preview}
            </div>
        </div>
        ${data.suggestions ? `
        <div style="background: #eff6ff; padding: 1.5rem; border-radius: 8px; border-left: 4px solid var(--blue);">
            <h4 style="color: var(--navy); margin-bottom: 1rem;"><i class="fas fa-lightbulb"></i> Suggestions</h4>
            <div style="color: var(--gray); line-height: 1.8;">
                ${data.suggestions}
            </div>
        </div>
        ` : ''}
    `;
    
    // Store for download
    window.currentOptimizedResume = data;
    
    resultsDiv.classList.add('active');
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function downloadResume() {
    if (!window.currentOptimizedResume) {
        showNotification('No resume to download', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/download-resume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                resume_content: window.currentOptimizedResume.optimized_resume,
                company_name: document.getElementById('opt-company').value
            })
        });
        
        if (!response.ok) throw new Error('Download failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `optimized_resume_${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('Download error:', error);
        showNotification('Error downloading resume. Please try again.', 'error');
    }
}

// Cover Letter Generation
async function generateCoverLetter() {
    const fileInput = document.getElementById('cover-resume');
    const jobDesc = document.getElementById('cover-job-desc').value.trim();
    const company = document.getElementById('cover-company').value.trim();
    
    if (!fileInput.files[0] || !jobDesc) {
        showNotification('Please upload your resume and paste the job description', 'error');
        return;
    }
    
    if (!currentUser.email) {
        showNotification('Please enter your email first', 'error');
        scrollToTools();
        return;
    }
    
    // Show loading
    document.getElementById('loading-cover').classList.add('active');
    document.getElementById('cover-results').classList.remove('active');
    
    const formData = new FormData();
    formData.append('resume', fileInput.files[0]);
    formData.append('job_description', jobDesc);
    formData.append('company_name', company);
    formData.append('email', currentUser.email);
    
    try {
        const response = await fetch('/api/generate-cover-letter', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('Generation failed');
        
        const data = await response.json();
        
        // Hide loading
        document.getElementById('loading-cover').classList.remove('active');
        
        // Show results
        displayCoverLetterResults(data);
        
    } catch (error) {
        console.error('Cover letter error:', error);
        document.getElementById('loading-cover').classList.remove('active');
        showNotification('Error generating cover letter. Please try again.', 'error');
    }
}

function displayCoverLetterResults(data) {
    const resultsDiv = document.getElementById('cover-results');
    const contentDiv = document.getElementById('cover-content');
    
    contentDiv.innerHTML = `
        <div style="background: white; padding: 2rem; border-radius: 8px;">
            <h4 style="color: var(--navy); margin-bottom: 1rem;">Your Cover Letter</h4>
            <textarea 
                rows="20" 
                style="width: 100%; padding: 1rem; border: 2px solid var(--gray-light); 
                       border-radius: 8px; font-family: inherit; font-size: 1rem;"
                id="cover-letter-text"
            >${data.cover_letter}</textarea>
            <p style="color: var(--gray); margin-top: 1rem; font-size: 0.9rem;">
                <i class="fas fa-info-circle"></i> Feel free to edit the cover letter above before downloading.
            </p>
        </div>
    `;
    
    // Store for download
    window.currentCoverLetter = data;
    
    resultsDiv.classList.add('active');
    resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function downloadCoverLetter() {
    const coverLetterText = document.getElementById('cover-letter-text');
    
    if (!coverLetterText) {
        showNotification('No cover letter to download', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/download-cover-letter', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                cover_letter: coverLetterText.value,
                company_name: document.getElementById('cover-company').value
            })
        });
        
        if (!response.ok) throw new Error('Download failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `cover_letter_${Date.now()}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('Download error:', error);
        showNotification('Error downloading cover letter. Please try again.', 'error');
    }
}

// Notification System
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existing = document.querySelector('.notification');
    if (existing) existing.remove();
    
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Upgrade Prompt
function showUpgradePrompt() {
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    `;
    
    overlay.innerHTML = `
        <div style="background: white; padding: 3rem; border-radius: 12px; max-width: 500px; text-align: center;">
            <h3 style="color: var(--navy); margin-bottom: 1rem; font-size: 1.75rem;">
                You've Used All Free Resumes
            </h3>
            <p style="color: var(--gray); margin-bottom: 2rem; font-size: 1.1rem;">
                Upgrade to Premium for unlimited AI-powered resume optimization
            </p>
            <div style="font-size: 2.5rem; font-weight: 700; color: var(--green); margin-bottom: 0.5rem;">
                $5.99/month
            </div>
            <p style="color: var(--gray); margin-bottom: 2rem;">
                Cancel anytime. No questions asked.
            </p>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <a href="/api/create-checkout" class="btn btn-primary" style="text-decoration: none;">
                    Upgrade Now
                </a>
                <button class="btn btn-secondary" onclick="this.closest('div').parentElement.remove()">
                    Maybe Later
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
}

// File Input Visual Feedback
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="file"]').forEach(input => {
        input.addEventListener('change', function() {
            const label = this.parentElement.querySelector('.file-input-label span');
            if (this.files.length > 0) {
                label.innerHTML = `<i class="fas fa-check-circle" style="color: var(--green);"></i> ${this.files[0].name}`;
            }
        });
    });
    
    // Add CSS animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
});