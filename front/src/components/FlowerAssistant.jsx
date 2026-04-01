import { useMemo, useState } from "react";
import { streamFlowerAssistant } from "../api/publicApi";
import "./FlowerAssistant.css";

const QUICK_PROMPTS = [
  "Подбери букет до 3500 ₽",
  "Нужен букет для свидания",
  "Хочу что-то нежное и светлое",
  "Что выбрать в подарок маме?",
];

const INITIAL_MESSAGES = [
  {
    id: "welcome-1",
    role: "assistant",
    text: "Помогу подобрать букет по бюджету, поводу и предпочтениям.",
  },
  {
    id: "welcome-2",
    role: "assistant",
    text: "Опишите, для кого букет и какой ориентир по бюджету.",
  },
];

function FlowerAssistant({ onAddToCart, onOpenCatalog }) {
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState(INITIAL_MESSAGES);

  const visibleMessages = useMemo(() => messages.slice(-8), [messages]);

  const submitMessage = async (text) => {
    const trimmedText = text.trim();
    if (!trimmedText || isLoading) {
      return;
    }

    const userMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: trimmedText,
    };
    const assistantMessageId = `assistant-${Date.now()}`;

    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        id: assistantMessageId,
        role: "assistant",
        text: "",
        suggestions: [],
      },
    ]);
    setDraft("");
    setIsOpen(true);
    setIsLoading(true);

    try {
      const history = [...messages, userMessage].map((message) => ({
        role: message.role,
        content: message.text,
      }));
      let finalPayload = null;

      await streamFlowerAssistant(history, {
        onChunk: (chunk) => {
          if (!chunk) {
            return;
          }
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantMessageId
                ? { ...message, text: `${message.text}${chunk}` }
                : message
            )
          );
        },
        onDone: (payload) => {
          finalPayload = payload;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantMessageId
                ? {
                    ...message,
                    text: payload?.text || message.text || "Консультант не вернул текст ответа.",
                    suggestions: Array.isArray(payload?.suggestions) ? payload.suggestions : [],
                  }
                : message
            )
          );
        },
      });

      if (!finalPayload) {
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantMessageId
              ? { ...message, text: "Не удалось получить ответ от консультанта." }
              : message
          )
        );
      }
    } catch {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                text: "Не удалось получить ответ от AI-консультанта. Проверьте backend API, Ollama и доступность базы данных.",
                suggestions: [],
                isError: true,
              }
            : message
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await submitMessage(draft);
  };

  return (
    <div className={`flower-assistant ${isOpen ? "is-open" : ""}`}>
      {isOpen ? (
        <section className="flower-assistant-panel" aria-label="Чат-помощник по выбору цветов">
          <div className="flower-assistant-header">
            <div>
              <p className="flower-assistant-eyebrow">Flower AI</p>
              <h2 className="flower-assistant-title">Помощник по букетам</h2>
            </div>
            <button
              type="button"
              className="flower-assistant-close"
              aria-label="Свернуть чат"
              onClick={() => setIsOpen(false)}
            >
              <img src="./src/assets/close-1511-svgrepo-com.svg" alt="close" />
            </button>
          </div>

          <div className="flower-assistant-messages">
            {visibleMessages.map((message) => (
              <div
                key={message.id}
                className={`flower-assistant-message flower-assistant-message--${message.role} ${message.isError ? "is-error" : ""}`}
              >
                <p>{message.text || (isLoading && message.role === "assistant" ? "Консультант думает..." : "")}</p>

                {message.suggestions?.length ? (
                  <div className="flower-assistant-recommendations">
                    {message.suggestions.map((product) => (
                      <article key={`${message.id}-${product.id}`} className="flower-assistant-product">
                        <div>
                          <h3>{product.title}</h3>
                          <p>{product.description || product.category || "Подходит под ваш запрос"}</p>
                          <span>{product.price} ₽</span>
                        </div>
                        <button type="button" onClick={() => onAddToCart(product)}>
                          В корзину
                        </button>
                      </article>
                    ))}
                    <button type="button" className="flower-assistant-link" onClick={onOpenCatalog}>
                      Открыть каталог
                    </button>
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          <form className="flower-assistant-form" onSubmit={handleSubmit}>
            <input
              type="text"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Например: букет до 5000 ₽ для мамы"
              disabled={isLoading}
            />
            <button type="submit" disabled={isLoading}>
              {isLoading ? "..." : "Отправить"}
            </button>
          </form>
        </section>
      ) : null}

      <button
        type="button"
        className="flower-assistant-trigger"
        aria-label="Открыть чат с помощником"
        onClick={() => setIsOpen((prev) => !prev)}
      >
        <span>AI</span>
        <strong>Ассистент</strong>
      </button>
    </div>
  );
}

export default FlowerAssistant;
