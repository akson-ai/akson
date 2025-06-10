import { useState, useEffect, useRef } from "react";
import { useSuspenseQuery, useMutation } from "@tanstack/react-query";
import { API_BASE_URL } from "../constants";
import Header from "./Header";
import History from "./History";
import Input from "./Input";
import KeyboardShortcuts from "./KeyboardShortcuts";
import { useEvents } from "../hooks/events";
import { generateMessageId } from "../utils/idGenerator";

function ChatApp({ chatId }) {
  const abortControllerRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState("");
  const [selectedAssistant, setSelectedAssistant] = useState(undefined);
  const [editingMessage, setEditingMessage] = useState(null);
  const messageInputRef = useRef(null);
  const { data: state } = useSuspenseQuery({ queryKey: ["chats", chatId] });

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
        toolCallId: msg.tool_call_id,
        category: msg.category,
      })),
    );
  }, [state]);

  const sendMessageMutation = useMutation({
    mutationFn: async (message) => {
      await fetch(`${API_BASE_URL}/chats/${chatId}/messages`, {
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
      await fetch(`${API_BASE_URL}/chats/${chatId}/messages/${messageId}`, {
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

  useEvents(chatId, setMessages, setSelectedAssistant);

  const sendMessage = () => {
    if (!inputText.trim()) return;

    if (editingMessage) {
      // Handle editing existing message
      editMessageMutation.mutate({
        messageId: editingMessage,
        content: inputText,
      });
    } else {
      // Handle new message
      const messageId = generateMessageId();

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
    }
  };

  const deleteMessage = (messageId) => {
    if (!confirm("Are you sure you want to delete this message?")) {
      return;
    }
    deleteMessageMutation.mutate(messageId);
  };

  const retryMessageMutation = useMutation({
    mutationFn: async (messageId) => {
      await fetch(`${API_BASE_URL}/chats/${chatId}/messages/${messageId}/retry`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        signal: abortControllerRef.current.signal,
      });
    },
  });

  const retryMessage = (messageId) => {
    if (!confirm("Are you sure you want to retry from this message? This will remove all messages below it.")) {
      return;
    }

    // Remove all messages after the selected one locally
    const messageIndex = messages.findIndex((msg) => msg.id === messageId);
    if (messageIndex !== -1) {
      setMessages((prev) => prev.slice(0, messageIndex));
    }

    abortControllerRef.current = new AbortController();
    retryMessageMutation.mutate(messageId);
  };

  const editMessage = (messageId) => {
    const message = messages.find((msg) => msg.id === messageId);
    if (message && message.role === "user") {
      setEditingMessage(messageId);
      setInputText(message.content);
      messageInputRef.current?.focus();
    }
  };

  const cancelEdit = () => {
    setEditingMessage(null);
    setInputText("");
  };

  const editMessageMutation = useMutation({
    mutationFn: async ({ messageId, content }) => {
      await fetch(`${API_BASE_URL}/chats/${chatId}/messages/${messageId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ content }),
      });
    },
    onSuccess: (_, { messageId, content }) => {
      setMessages((prev) => prev.map((msg) => (msg.id === messageId ? { ...msg, content } : msg)));
      setEditingMessage(null);
      setInputText("");
    },
  });

  const forkMessageMutation = useMutation({
    mutationFn: async (messageId) => {
      const response = await fetch(`${API_BASE_URL}/chats/${chatId}/fork/${messageId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
      });
      return response.json();
    },
    onSuccess: (data) => {
      // Navigate to the new forked chat
      window.location.href = `/chat?id=${data.chat_id}`;
    },
  });

  const forkMessage = (messageId) => {
    if (
      !confirm(
        "Are you sure you want to fork the chat from this message? This will create a new chat with messages up to this point.",
      )
    ) {
      return;
    }
    forkMessageMutation.mutate(messageId);
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
        <History
          messages={messages}
          onDeleteMessage={deleteMessage}
          onRetryMessage={retryMessage}
          onEditMessage={editMessage}
          onForkMessage={forkMessage}
        />
        <Input
          inputText={inputText}
          messageInputRef={messageInputRef}
          onInputChange={setInputText}
          onSendMessage={sendMessage}
          isEditing={!!editingMessage}
          onCancelEdit={cancelEdit}
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
