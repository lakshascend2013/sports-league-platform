/**
 * Sports League Visual Effects & Sports Animations
 * Lightweight, 60fps, respect prefers-reduced-motion
 * Guaranteed visibility: Never leaves elements hidden or stuck at opacity:0
 */

document.addEventListener('DOMContentLoaded', () => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) return;

    // Check if on Admin page - Admin panel must remain 100% visible without animation delays
    const isAdmin = document.body.classList.contains('admin-body') || document.querySelector('.admin-layout');

    if (!isAdmin) {
        initCounterAnimations();
        init3DTiltEffects();
        initHeroBallInteractive();
        initSafeScrollReveal();
    }
    
    // Live match pulses apply everywhere
    initLivePulseGlow();
});

/**
 * 1. Animated Numerical Counters (Count-Up with Easing)
 */
function initCounterAnimations() {
    const counters = document.querySelectorAll('[data-counter]');
    if (!counters.length) return;

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const targetVal = parseInt(el.getAttribute('data-counter'), 10) || 0;
                animateNumber(el, targetVal, 1400);
                obs.unobserve(el);
            }
        });
    }, { threshold: 0.1 });

    counters.forEach(counter => observer.observe(counter));
}

function animateNumber(element, target, duration) {
    let startTimestamp = null;
    const startVal = 0;

    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        // easeOutExpo easing curve
        const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
        const currentVal = Math.floor(easeProgress * (target - startVal) + startVal);
        
        element.textContent = currentVal.toLocaleString();

        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            element.textContent = target.toLocaleString();
        }
    };

    window.requestAnimationFrame(step);
}

/**
 * 2. 3D Tilt Effect on Team, Player, and Venue Cards (Public pages only)
 */
function init3DTiltEffects() {
    const tiltCards = document.querySelectorAll('.team-card, .player-card, .venue-card, .glass-card:not(.match-card)');
    
    tiltCards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            const rotateX = ((y - centerY) / centerY) * -4;
            const rotateY = ((x - centerX) / centerX) * 4;
            
            card.style.transform = `perspective(800px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-4px)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });
}

/**
 * 3. Interactive Hero Soccer Ball & Mouse Parallax
 */
function initHeroBallInteractive() {
    const ballContainer = document.querySelector('.hero-ball-container');
    const ballSphere = document.querySelector('.ball-sphere');
    const pedestal = document.querySelector('.pitch-pedestal');
    if (!ballContainer || !ballSphere) return;

    ballContainer.addEventListener('mousemove', (e) => {
        const rect = ballContainer.getBoundingClientRect();
        const relX = (e.clientX - rect.left) / rect.width - 0.5;
        const relY = (e.clientY - rect.top) / rect.height - 0.5;

        ballSphere.style.transform = `translate(${relX * 25}px, ${relY * 20}px) rotate(${relX * 45}deg)`;
        if (pedestal) {
            pedestal.style.transform = `rotateX(65deg) translate(${relX * 15}px, 0)`;
        }
    });

    ballContainer.addEventListener('mouseleave', () => {
        ballSphere.style.transform = '';
        if (pedestal) {
            pedestal.style.transform = '';
        }
    });
}

/**
 * 4. Safe Scroll Reveal (Only for specifically tagged items, NEVER hides tables or venues)
 */
function initSafeScrollReveal() {
    // Only animate hero elements or explicitly tagged elements; never blanket hide .section-wrapper or tables
    const items = document.querySelectorAll('[data-reveal]');
    if (!items.length) return;

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                obs.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    items.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(15px)';
        el.style.transition = 'opacity 0.4s ease-out, transform 0.4s ease-out';
        observer.observe(el);
    });
}

/**
 * 5. Live Scoreboard Pulse & Highlight transitions
 */
function initLivePulseGlow() {
    const liveBadges = document.querySelectorAll('.badge-live');
    if (!liveBadges.length) return;

    liveBadges.forEach(badge => {
        setInterval(() => {
            badge.style.boxShadow = '0 0 15px rgba(255, 42, 95, 0.6)';
            setTimeout(() => {
                badge.style.boxShadow = '';
            }, 800);
        }, 2000);
    });
}
