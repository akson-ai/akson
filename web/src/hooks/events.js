import { useEffect } from "react";
import { API_BASE_URL } from "../constants";

export function useEvents(chatId, setMessages, setSelectedAssistant) {
  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE_URL}/chats/${chatId}/events`, {
      withCredentials: true,
    });

    eventSource.onmessage = function (event) {
      const data = JSON.parse(event.data);
      console.log(data);

      if (data.type === "begin_message") {
        setMessages((prev) => [
          ...prev,
          {
            id: data.id,
            role: data.role,
            name: data.name,
            content: "",
            category: data.category,
          },
        ]);
      } else if (data.type === "clear") {
        setMessages([]);
      } else if (data.type === "update_assistant") {
        setSelectedAssistant(data.assistant);
      } else if (data.type === "add_chunk") {
        setMessages((prev) => {
          const i = prev.length - 1;
          const message = structuredClone(prev[i]);

          if (!message.toolCall && ["tool_call.name", "tool_call.arguments"].includes(data.field)) {
            message.toolCall = { name: "", arguments: "", toolCallId: "" };
          }

          switch (data.field) {
            case "content":
              message.content += data.chunk;
              break;
            case "tool_call.name":
              message.toolCall.name += data.chunk;
              break;
            case "tool_call.arguments":
              message.toolCall.arguments += data.chunk;
              break;
            case "tool_call_id":
              message.toolCallId += data.chunk;
              break;
          }

          return [...prev.slice(0, i), message];
        });
      }
    };

    return () => {
      eventSource.close();
    };
  }, [chatId, setMessages]);
}
