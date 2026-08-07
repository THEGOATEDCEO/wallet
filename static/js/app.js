document.addEventListener('DOMContentLoaded', () => {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach((alert, index) => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.4s ease';
            setTimeout(() => alert.remove(), 400);
        }, 4000 + index * 300);
    });

    const updateLivePrice = async () => {
        try {
            const response = await fetch('/api/wallet-settings');
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            const priceElements = document.querySelectorAll('[data-live-price]');
            priceElements.forEach((element) => {
                element.textContent = `💰 1 PERK = ₹${data.perk_price}`;
            });
            document.body.dataset.perkRate = data.perk_price;
            const requestedInput = document.getElementById('requested_perks');
            const displayPerks = document.getElementById('display-perks');
            const displayTotal = document.getElementById('display-total');
            if (requestedInput && displayPerks && displayTotal) {
                const value = parseInt(requestedInput.value, 10) || 0;
                displayPerks.textContent = value;
                displayTotal.textContent = (value * data.perk_price).toFixed(2);
            }
        } catch (error) {
            console.error('Failed to refresh wallet price', error);
        }
    };

    const requestedInput = document.getElementById('requested_perks');
    const displayPerks = document.getElementById('display-perks');
    const displayTotal = document.getElementById('display-total');
    if (requestedInput && displayPerks && displayTotal) {
        const updatePreview = () => {
            const value = parseInt(requestedInput.value, 10) || 0;
            displayPerks.textContent = value;
            displayTotal.textContent = (value * Number(document.body.dataset.perkRate || 1)).toFixed(2);
        };
        requestedInput.addEventListener('input', updatePreview);
        updatePreview();
    }

    updateLivePrice();
    setInterval(updateLivePrice, 3000);
});
