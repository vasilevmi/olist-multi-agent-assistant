const form = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const submitButton = document.querySelector("#submit-button");
const buttonLabel = document.querySelector(".button-label");
const loadingPanel = document.querySelector("#loading-panel");
const errorPanel = document.querySelector("#error-panel");
const errorMessage = document.querySelector("#error-message");
const chatMessages = document.querySelector("#chat-messages");
const welcomeMessage = document.querySelector("#welcome-message");
const newChatButton = document.querySelector("#new-chat-button");
const exampleCards = document.querySelectorAll(".example-card");

const conversationHistory = [];
const MAX_HISTORY_MESSAGES = 10;
let conversationSessionId = createSessionId();

function createSessionId() {
  if (typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  questionInput.disabled = isLoading;
  submitButton.classList.toggle("loading", isLoading);
  buttonLabel.textContent = isLoading ? "Исследуем…" : "Отправить";
  loadingPanel.hidden = !isLoading;
}

function showError(message) {
  errorMessage.textContent = message;
  errorPanel.hidden = false;
}

function appendUserMessage(question) {
  welcomeMessage.hidden = true;
  const row = createElement("article", "message-row user-row");
  const bubble = createElement("div", "message-bubble user-bubble", question);
  const avatar = createElement("div", "message-avatar user-avatar", "Вы");
  row.append(bubble, avatar);
  chatMessages.append(row);
}

function renderMetrics(metrics) {
  const container = createElement("div", "metrics-grid");
  container.setAttribute("aria-label", "Метрики выполнения");
  const items = [
    [metrics.llm_calls, "LLM-вызовов"],
    [metrics.planning_calls, "Решений оркестратора"],
    [metrics.tool_calls, "Инструментов"],
    [`${metrics.duration_seconds} с`, "Время выполнения"],
  ];

  for (const [value, label] of items) {
    const card = createElement("div", "metric-card");
    card.append(
      createElement("span", "metric-value", String(value)),
      createElement("span", "metric-label", label),
    );
    container.append(card);
  }
  return container;
}

function jsonDetails(label, value) {
  const details = document.createElement("details");
  const summary = createElement("summary", "", label);
  const pre = createElement("pre", "", JSON.stringify(value, null, 2));
  details.append(summary, pre);
  return details;
}

function renderSteps(steps) {
  const container = createElement("div", "tab-content active");
  container.dataset.panel = "steps";
  if (!steps.length) {
    container.append(createElement("div", "empty-state", "Шаги не были выполнены."));
    return container;
  }

  steps.forEach((step, index) => {
    const card = createElement("article", "timeline-item");
    const number = createElement("div", "step-number", String(index + 1));
    const body = createElement("div");
    const meta = createElement("div", "item-meta");
    meta.append(
      createElement("span", "", step.agent_name),
      createElement("span", "", step.tool_name || "без инструмента"),
      createElement("span", "", step.status),
    );
    body.append(
      createElement("div", "item-title", step.description),
      meta,
      jsonDetails("Аргументы", step.arguments),
    );
    if (step.error_message) {
      body.append(
        createElement("p", "step-error", `Ошибка шага: ${step.error_message}`),
      );
    }
    card.append(number, body);
    container.append(card);
  });
  return container;
}

function renderEvidence(evidence) {
  const container = createElement("div", "tab-content");
  container.dataset.panel = "evidence";
  if (!evidence.length) {
    container.append(createElement("div", "empty-state", "Evidence пока не собраны."));
    return container;
  }

  for (const item of evidence) {
    const card = createElement("article", "evidence-card");
    const meta = createElement("div", "item-meta");
    meta.append(
      createElement("span", "", item.source),
      createElement("span", "", `ID ${item.evidence_id.slice(0, 8)}`),
    );
    card.append(
      createElement("div", "item-title", item.tool_name),
      meta,
      jsonDetails("Показать полученные данные", item.data),
    );
    container.append(card);
  }
  return container;
}

function renderFindings(findings) {
  const container = createElement("div", "tab-content");
  container.dataset.panel = "findings";
  if (!findings.length) {
    container.append(createElement("div", "empty-state", "Проверенных выводов нет."));
    return container;
  }

  for (const finding of findings) {
    const card = createElement("article", "finding-card");
    const header = createElement("div", "finding-header");
    const type = finding.is_hypothesis ? "hypothesis" : "fact";
    header.append(
      createElement("span", `type-badge ${type}`, finding.is_hypothesis ? "Гипотеза" : "Факт"),
      createElement("span", `confidence-badge ${finding.confidence}`, finding.confidence),
    );
    const ids = finding.evidence_ids.length
      ? finding.evidence_ids.map((id) => id.slice(0, 8)).join(", ")
      : "нет прямых Evidence";
    card.append(
      header,
      createElement("p", "finding-statement", finding.statement),
      createElement("div", "evidence-links", `Evidence: ${ids}`),
    );
    container.append(card);
  }
  return container;
}

function createTechnicalDetails(data) {
  const details = createElement("details", "technical-details");
  const summary = createElement("summary", "technical-summary");
  const label = createElement("span");
  label.append(
    createElement("strong", "", "Технические детали"),
    createElement("small", "", "Шаги агентов, Evidence, гипотезы и метрики"),
  );
  summary.append(label, createElement("span", "technical-chevron", "⌄"));

  const content = createElement("div", "technical-content");
  const trace = createElement("div", "trace-panel");
  const tabs = createElement("div", "tabs");
  tabs.setAttribute("role", "tablist");
  const tabDefinitions = [
    ["steps", "Шаги", data.steps.length],
    ["evidence", "Evidence", data.evidence.length],
    ["findings", "Факты и гипотезы", data.findings.length],
  ];

  for (const [name, labelText, count] of tabDefinitions) {
    const button = createElement("button", `tab-button${name === "steps" ? " active" : ""}`);
    button.type = "button";
    button.dataset.tab = name;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(name === "steps"));
    button.append(
      document.createTextNode(`${labelText} `),
      createElement("span", "tab-count", String(count)),
    );
    tabs.append(button);
  }

  const panels = createElement("div", "technical-panels");
  panels.append(
    renderSteps(data.steps),
    renderEvidence(data.evidence),
    renderFindings(data.findings),
  );

  tabs.addEventListener("click", (event) => {
    const button = event.target.closest(".tab-button");
    if (!button) return;
    tabs.querySelectorAll(".tab-button").forEach((item) => {
      const active = item === button;
      item.classList.toggle("active", active);
      item.setAttribute("aria-selected", String(active));
    });
    panels.querySelectorAll(".tab-content").forEach((panel) => {
      panel.classList.toggle("active", panel.dataset.panel === button.dataset.tab);
    });
  });

  trace.append(tabs, panels);
  content.append(renderMetrics(data.metrics), trace);
  details.append(summary, content);
  return details;
}

function appendListSection(parent, title, items, ordered = false) {
  if (!items?.length) return;
  const section = createElement("section", "answer-section");
  const list = document.createElement(ordered ? "ol" : "ul");
  for (const item of items) list.append(createElement("li", "", item));
  section.append(createElement("h3", "", title), list);
  parent.append(section);
}

function createFollowUps(items) {
  if (!items?.length) return null;
  const section = createElement("section", "follow-up-section");
  section.append(createElement("span", "follow-up-label", "Что проверить дальше"));
  const list = createElement("div", "follow-up-list");
  for (const item of items) {
    const button = createElement("button", "follow-up-button", item);
    button.type = "button";
    button.addEventListener("click", () => {
      questionInput.value = item;
      questionInput.focus();
      questionInput.setSelectionRange(item.length, item.length);
      form.scrollIntoView({ behavior: "smooth", block: "center" });
    });
    list.append(button);
  }
  section.append(list);
  return section;
}

function appendAssistantMessage(data) {
  const row = createElement("article", "message-row assistant-row");
  const avatar = createElement("div", "message-avatar", "AI");
  const bubble = createElement("div", "message-bubble assistant-bubble");
  const heading = createElement("div", "message-heading");
  heading.append(
    createElement("strong", "", "Olist Intelligence"),
    createElement("span", `status-badge ${data.status}`, data.status),
  );
  bubble.append(heading);

  const structured = data.structured_answer;
  if (structured?.short_summary) {
    const answer = createElement("div", "structured-answer");
    const summary = createElement("section", "answer-section");
    summary.append(
      createElement("h3", "", "Ответ"),
      createElement("p", "", structured.short_summary),
    );
    answer.append(summary);
    appendListSection(answer, "Основные факторы", structured.main_factors, true);
    bubble.append(answer);

    const followUps = createFollowUps(structured.next_checks);
    if (followUps) bubble.append(followUps);
  } else {
    bubble.append(
      createElement(
        "p",
        "final-answer",
        data.final_answer || data.error_message || "Итоговый ответ не сформирован.",
      ),
    );
  }

  bubble.append(createTechnicalDetails(data));
  row.append(avatar, bubble);
  chatMessages.append(row);
}

function historyContent(data) {
  const answer = data.structured_answer;
  if (!answer) return (data.final_answer || "").trim();
  return [
    answer.short_summary,
    ...(answer.main_factors || []),
  ].filter(Boolean).join("\n").trim();
}

function scrollToLatestMessage() {
  chatMessages.lastElementChild?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function sendQuestion(question) {
  const previousHistory = conversationHistory.slice(-MAX_HISTORY_MESSAGES);
  appendUserMessage(question);
  questionInput.value = "";
  errorPanel.hidden = true;
  setLoading(true);
  scrollToLatestMessage();

  try {
    const response = await fetch("/api/investigations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        history: previousHistory,
        session_id: conversationSessionId,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Сервер вернул ошибку");

    appendAssistantMessage(data);
    const assistantContent = historyContent(data);
    if (data.status === "completed" && assistantContent) {
      conversationHistory.push(
        { role: "user", content: question },
        { role: "assistant", content: assistantContent },
      );
    }
    scrollToLatestMessage();
  } catch (error) {
    showError(error.message || "Неизвестная ошибка");
  } finally {
    setLoading(false);
    questionInput.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (question) sendQuestion(question);
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

newChatButton.addEventListener("click", () => {
  conversationHistory.length = 0;
  conversationSessionId = createSessionId();
  chatMessages.querySelectorAll(".message-row:not(#welcome-message)").forEach((message) => message.remove());
  welcomeMessage.hidden = false;
  errorPanel.hidden = true;
  questionInput.value = "";
  questionInput.focus();
});

exampleCards.forEach((card) => {
  card.addEventListener("click", () => {
    questionInput.value = card.dataset.question || "";
    questionInput.focus();
    questionInput.setSelectionRange(questionInput.value.length, questionInput.value.length);
    form.scrollIntoView({ behavior: "smooth", block: "center" });
  });
});
