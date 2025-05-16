import { useEffect } from "react";
import { API_BASE_URL } from "../constants";

export function useEvents(chatId, setMessages) {
  useEffect(() => {
    const eventSource = new EventSource(`${API_BASE_URL}/${chatId}/events`, {
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
      } else if (data.type === "add_chunk") {
        setMessages((prev) => {
          const i = prev.length - 1;
          const message = structuredClone(prev[i]);

          if (!message.toolCalls && ["function_name", "function_arguments"].includes(data.location)) {
            message.toolCalls = [{ name: "", arguments: "" }];
          }

          switch (data.location) {
            case "content":
              message.content += data.chunk;
              break;
            case "function_name":
              message.toolCalls[0].name += data.chunk;
              break;
            case "function_arguments":
              message.toolCalls[0].arguments += data.chunk;
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
