import { useEffect, useRef, useState } from "react";
import Message from "./Message";

function History({ messages, onDeleteMessage }) {
  const chatHistoryRef = useRef(null);
  const [scrolledToBottom, setScrolledToBottom] = useState(true);

  // Add scroll event listener to track when user scrolls
  useEffect(() => {
    const chatHistory = chatHistoryRef.current;
    if (!chatHistory) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = chatHistory;
      const isAtBottom = scrollHeight <= scrollTop + clientHeight;
      setScrolledToBottom(isAtBottom);
    };

    chatHistory.addEventListener("scroll", handleScroll);
    return () => chatHistory.removeEventListener("scroll", handleScroll);
  }, []);

  // Scroll to bottom when messages change, but only if already at bottom
  useEffect(() => {
    if (chatHistoryRef.current && scrolledToBottom) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages, scrolledToBottom]);

  return (
    <div id="chatHistory" className="p-4 overflow-y-auto flex-grow" ref={chatHistoryRef}>
      {messages.map((msg) => (
        <Message
          id={msg.id}
          key={msg.id}
          role={msg.role}
          content={msg.content}
          toolCall={msg.toolCall}
          toolCallId={msg.toolCallId}
          name={msg.name}
          category={msg.category}
          onDelete={onDeleteMessage}
        />
      ))}
    </div>
  );
}

export default History;
