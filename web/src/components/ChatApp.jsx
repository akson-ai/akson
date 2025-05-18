import { useState, useEffect, useRef } from "react";
import { useSuspenseQuery, useMutation } from "@tanstack/react-query";
import { API_BASE_URL } from "../constants";
import Header from "./Header";
import History from "./History";
import Input from "./Input";
import KeyboardShortcuts from "./KeyboardShortcuts";
import { useEvents } from "../hooks/events";

function ChatApp({ chatId }) {
  const abortControllerRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [selectedAssistant, setSelectedAssistant] = useState(undefined);
  const messageInputRef = useRef(null);
  const { data: state } = useSuspenseQuery({ queryKey: [chatId, "state"] });

  useEffect(() => {
    document.title = state.title || "New Chat";
    setSelectedAssistant(state.assistant);
    setMessages(
      state.messages.map((msg) => ({
        id: msg.id,
        role: msg.role,
        name: msg.name,
        content: msg.content,
        toolCall: msg.tool_call,
        category: msg.category,
      })),
    );
  }, [state]);

  const sendMessageMutation = useMutation({
    mutationFn: async (message) => {
      await fetch(`${API_BASE_URL}/${chatId}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(message),
        signal: abortControllerRef.current.signal,
      });
    },
  });

  const deleteMessageMutation = useMutation({
    mutationFn: async (messageId) => {
      await fetch(`${API_BASE_URL}/${chatId}/message/${messageId}`, {
        method: "DELETE",
        credentials: "include",
      });
    },
    onSuccess: (_, messageId) => {
      setMessages((prev) => prev.filter((msg) => msg.id !== messageId));
    },
  });

  const createNewChat = () => {
    window.location.href = "/chat";
  };

  useEvents(chatId, setMessages);

  const sendMessage = () => {
    if (!inputText.trim()) return;

    const messageId = crypto.randomUUID().toString().replace(/-/g, "");

    setMessages((prev) => [
      ...prev,
      {
        id: messageId,
        role: "user",
        name: "You",
        content: inputText,
      },
    ]);

    abortControllerRef.current = new AbortController();

    sendMessageMutation.mutate({
      id: messageId,
      content: inputText,
      assistant: selectedAssistant,
    });

    setInputText("");
  };

  const deleteMessage = (messageId) => {
    if (!confirm("Are you sure you want to delete this message?")) {
      return;
    }
    deleteMessageMutation.mutate(messageId);
  };

  return (
    <>
      <Header
        chatId={chatId}
        selectedAssistant={selectedAssistant}
        onAssistantChange={setSelectedAssistant}
        createNewChat={createNewChat}
      />

      <div className="flex flex-col max-w-5xl mx-auto h-[calc(100vh-64px)] w-full">
        <History messages={messages} onDeleteMessage={deleteMessage} />
        <Input
          inputText={inputText}
          messageInputRef={messageInputRef}
          onInputChange={setInputText}
          onSendMessage={sendMessage}
        />
      </div>

      <KeyboardShortcuts
        createNewChat={createNewChat}
        messageInputRef={messageInputRef}
        abortControllerRef={abortControllerRef}
      />
    </>
  );
}

export default ChatApp;
