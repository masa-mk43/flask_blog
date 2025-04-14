// スクロール時のナビゲーションバーの影を調整
window.addEventListener('scroll', function() {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.05)';
    }
});

// 現在のページのナビゲーションリンクにactiveクラスを追加
document.addEventListener('DOMContentLoaded', function() {
    const currentLocation = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        const linkPath = link.getAttribute('href');
        if (linkPath === currentLocation || (currentLocation === '/' && linkPath === '/')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
});