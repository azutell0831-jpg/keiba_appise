function updateMoney() {
    fetch("/api/money")
        .then(res => res.json())
        .then(data => {
            const moneySpan = document.getElementById("money");
            if (moneySpan && data.money !== null) {
                moneySpan.textContent = data.money;
            }
        });
}

setInterval(updateMoney, 6000);
