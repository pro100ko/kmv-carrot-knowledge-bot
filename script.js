// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Search functionality
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.querySelector('.search-btn');
    
    if (searchInput && searchBtn) {
        // Search on button click
        searchBtn.addEventListener('click', performSearch);
        
        // Search on Enter key press
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
    
    // Smooth scrolling for navigation links
    const navLinks = document.querySelectorAll('.nav-link[href^="#"]');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Active navigation highlighting
    window.addEventListener('scroll', function() {
        const sections = document.querySelectorAll('section[id]');
        const navLinks = document.querySelectorAll('.nav-link');
        
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (pageYOffset >= sectionTop - 200) {
                current = section.getAttribute('id');
            }
        });
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    });
    
    // Category card hover effects
    const categoryCards = document.querySelectorAll('.category-card');
    categoryCards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Feature card animations
    const featureCards = document.querySelectorAll('.feature-card');
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    featureCards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });
    
    // Search functionality
    function performSearch() {
        const searchTerm = searchInput.value.trim();
        if (searchTerm) {
            // For now, we'll just show an alert
            // In a real implementation, this would search through the knowledge base
            alert(`Searching for: "${searchTerm}"\n\nThis would search through all products and categories in the knowledge base.`);
            
            // You could implement actual search functionality here:
            // - Search through product data
            // - Filter category cards
            // - Redirect to search results page
            // - Use a search API
        }
    }
    
    // Add loading animation for category cards
    const categoryGrid = document.querySelector('.category-grid');
    if (categoryGrid) {
        const cards = categoryGrid.querySelectorAll('.category-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = `opacity 0.6s ease ${index * 0.1}s, transform 0.6s ease ${index * 0.1}s`;
            
            setTimeout(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 100 + (index * 100));
        });
    }
    
    // Mobile menu toggle (if needed in the future)
    function setupMobileMenu() {
        const header = document.querySelector('.header');
        const nav = document.querySelector('.nav');
        
        // Add mobile menu button if needed
        if (window.innerWidth <= 768 && !document.querySelector('.mobile-menu-btn')) {
            const mobileBtn = document.createElement('button');
            mobileBtn.className = 'mobile-menu-btn';
            mobileBtn.innerHTML = '<i class="fas fa-bars"></i>';
            mobileBtn.style.display = 'none';
            
            mobileBtn.addEventListener('click', function() {
                nav.classList.toggle('mobile-open');
            });
            
            header.querySelector('.header-content').appendChild(mobileBtn);
        }
    }
    
    // Initialize mobile menu
    setupMobileMenu();
    
    // Handle window resize
    window.addEventListener('resize', setupMobileMenu);
    
    // Add some interactive features
    console.log('Knowledge Base loaded successfully!');
    console.log('Features available:');
    console.log('- Search functionality');
    console.log('- Smooth scrolling navigation');
    console.log('- Category card hover effects');
    console.log('- Responsive design');
    console.log('- Intersection Observer animations');
}); 