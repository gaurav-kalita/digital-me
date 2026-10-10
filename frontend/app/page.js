// frontend/app/page.js

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const assistantName = "Gaurav Kalita";

const initialMessages = [
  {
    id: "welcome",
    role: "assistant",
    content:
      "Hey, I’m Gaurav Kalita. Ask me anything about my work, projects, interests, or background and I’ll answer from the knowledge base.",
    sources: [],
    query: "",
  },
];

function createMessage(role, content, extra = {}) {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    sources: extra.sources || [],
    query: extra.query || "",
    status: extra.status || "sent",
  };
}

function Avatar({ role }) {
  return (
    <div className={`avatar ${role === "user" ? "user" : "assistant"}`}>
      {role === "user" ? "ME" : "GK"}
    </div>
  );
}

function TypingDots() {
  return (
    <div className="typingDots" aria-label="Assistant is typing">
      <span />
      <span />
      <span />
    </div>
  );
}

export default function HomePage() {
  const [messages, setMessages] = useState(initialMessages);
  const [question, setQuestion] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);
  const endOfMessagesRef = useRef(null);

  const onlineState = useMemo(() => {
    if (health?.status === "ok") {
      return "Online";
    }

    if (health?.error) {
      return health.error;
    }

    return "Checking connection...";
  }, [health]);

  useEffect(() => {
    let ignore = false;

    async function loadHealth() {
      try {
        const response = await fetch("/api/health", { cache: "no-store" });
        if (!response.ok) {
          throw new Error("Health check failed");
        }

        const data = await response.json();
        if (!ignore) {
          setHealth(data);
        }
      } catch (fetchError) {
        if (!ignore) {
          setHealth({ status: "degraded", error: "Backend is not reachable" });
        }
      }
    }

    loadHealth();
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedQuestion = question.trim();
    if (trimmedQuestion.length < 3) {
      setError("Please enter a longer question.");
      return;
    }

    setIsSending(true);
    setError("");
    setQuestion("");

    const loadingMessageId = `loading-${Date.now()}`;
    const userMessage = createMessage("user", trimmedQuestion);
    const loadingMessage = {
      id: loadingMessageId,
      role: "assistant",
      content: "",
      sources: [],
      query: "",
      status: "loading",
    };

    setMessages((current) => [...current, userMessage, loadingMessage]);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: trimmedQuestion }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || "Request failed");
      }

      const answerMessage = {
        id: `answer-${Date.now()}`,
        role: "assistant",
        content: data.answer,
        sources: data.sources || [],
        query: data.query || trimmedQuestion,
        status: "sent",
      };

      setMessages((current) =>
        current.map((message) => (message.id === loadingMessageId ? answerMessage : message))
      );
    } catch (submitError) {
      setMessages((current) => current.filter((message) => message.id !== loadingMessageId));
      setError(submitError.message || "Failed to send message.");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="shell">
      <section className="hero">
        <div className="heroCopy">
          <p className="eyebrow">Digital Me</p>
          <h1>Talk directly with Gaurav Kalita</h1>
          <p className="subtle">
            This is a personal AI conversation space. Ask about my work, ideas, projects, or
            background and I’ll answer in a natural chat flow.
          </p>

          <div className="profileStrip">
            <div className="profileBadge">
              <span className="profileDot" />
              <span>{assistantName}</span>
            </div>
            <div className="statusPill">
              <span className={`statusDot ${health?.status === "ok" ? "ok" : "bad"}`} />
              <span>{onlineState}</span>
            </div>
          </div>
        </div>

        <aside className="heroPanel">
          <p className="panelLabel">Conversation style</p>
          <h2>Warm, direct, grounded</h2>
          <p>
            The assistant speaks like a real person, keeps context from the knowledge base, and
            shows a typing indicator while answers are being prepared.
          </p>
        </aside>
      </section>

      <section className="chatShell" aria-label="Chat conversation">
        <div className="chatHeader">
          <div className="chatIdentity">
            <Avatar role="assistant" />
            <div>
              <p className="chatTitle">{assistantName}</p>
              <p className="chatSubtitle">Personal AI assistant</p>
            </div>
          </div>

          <div className="chatHint">Ask naturally. I’ll reply like a real conversation.</div>
        </div>

        <div className="messages" aria-live="polite" aria-relevant="additions text">
          {messages.map((message) => {
            const isLoading = message.status === "loading";

            return (
              <article key={message.id} className={`messageRow ${message.role}`}>
                <Avatar role={message.role} />

                <div className={`messageBubble ${message.role} ${isLoading ? "loading" : ""}`}>
                  {isLoading ? (
                    <div className="loadingState">
                      <div className="loadingLine short" />
                      <div className="loadingLine" />
                      <div className="loadingLine medium" />
                      <TypingDots />
                    </div>
                  ) : (
                    <>
                      <div className="messageMeta">
                        <span>{message.role === "user" ? "You" : assistantName}</span>
                        {message.query ? <span>Grounded reply</span> : null}
                      </div>
                      <div className="markdownBody">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                      </div>

                      {message.sources?.length ? (
                        <div className="sourceBlock">
                          <span className="sourceLabel">Sources used</span>
                          <div className="sourceList">
                            {message.sources.map((source) => (
                              <span key={source} className="sourceChip">
                                {source}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </>
                  )}
                </div>
              </article>
            );
          })}

          <div ref={endOfMessagesRef} />
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <div className="composerTopRow">
            <p className="composerLabel">Send a message</p>
            <p className="composerStatus">{isSending ? "Gaurav is thinking..." : "Ready"}</p>
          </div>

          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask me something like: What do you work on? What are you building? What should I know about you?"
            rows={4}
            disabled={isSending}
          />

          <div className="composerFooter">
            <p className="errorText">{error}</p>
            <button type="submit" disabled={isSending}>
              {isSending ? (
                <>
                  <span className="buttonSpinner" />
                  Sending
                </>
              ) : (
                "Send message"
              )}
            </button>
          </div>
        </form>
      </section>
    </main>
  );
}
