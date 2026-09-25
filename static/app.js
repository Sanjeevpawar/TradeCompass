const API = "http://127.0.0.1:8000";

let tradeId = null;

function loadDecision() {
    tradeId = document.getElementById("tradeIdInput").value;

    fetch(`${API}/decision?trade_id=${tradeId}`)
        .then(res => res.json())
        .then(data => renderDecision(data.decision));
}

function renderDecision(decision) {
    document.getElementById("actionText").innerText =
        `${decision.action} (${decision.strategy})`;

    // Confidence
    const confidence = Math.round(decision.confidence * 100);
    document.getElementById("confidenceBar").style.width = confidence + "%";
    document.getElementById("confidenceText").innerText =
        `Confidence: ${confidence}%`;

    // Reasoning
    const list = document.getElementById("reasoningList");
    list.innerHTML = "";
    decision.reasoning.forEach(r => {
        const li = document.createElement("li");
        li.innerText = r;
        list.appendChild(li);
    });

    // Risks
    const riskBox = document.getElementById("riskTags");
    riskBox.innerHTML = "";
    decision.risk_tags.forEach(risk => {
        const span = document.createElement("span");
        span.className = "risk";
        span.innerText = risk;
        riskBox.appendChild(span);
    });
}

function confirmDecision() {
    fetch(`${API}/decision/confirm?trade_id=${tradeId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ response: "YES" })
    })
    .then(res => res.json())
    .then(data => alert("Trade confirmed"));
}
