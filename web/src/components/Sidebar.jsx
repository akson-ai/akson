import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "../constants";
import { FaTrash } from "react-icons/fa6";

function Sidebar({ chatId }) {
  const [searchTerm, setSearchTerm] = useState("");
  const [hoveredChatId, setHoveredChatId] = useState(null);
  const queryClient = useQueryClient();
  const { data: chatHistory = [] } = useQuery({ queryKey: ["chats"] });

  const deleteChatMutation = useMutation({
    mutationFn: async (id) => {
      await fetch(`${API_BASE_URL}/chats/${id}`, {
        method: "DELETE",
        credentials: "include",
      });
    },
    onSuccess: (_, id) => {
      if (id === chatId) {
        window.location.href = "/chat";
      }
      queryClient.setQueryData(["chats"], (prev) => prev.filter((chat) => chat.id !== id));
    },
  });

  // Filter chats based on search term
  const filteredChats = searchTerm.trim()
    ? chatHistory.filter((chat) => chat.title.toLowerCase().includes(searchTerm.toLowerCase()))
    : chatHistory;

  const handleDeleteChat = (e, id) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this chat?")) {
      deleteChatMutation.mutate(id);
    }
  };

  return (
    <div className="menu bg-base-200 text-base-content min-h-full w-120 p-4">
      <input
        id="search-chats"
        type="text"
        placeholder="Search chats..."
        className="input input-bordered w-full"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />
      <ul className="mt-4">
        {filteredChats.map((chat) => (
          <li key={chat.id} onMouseEnter={() => setHoveredChatId(chat.id)} onMouseLeave={() => setHoveredChatId(null)}>
            <a href={`/chat?id=${chat.id}`}>
              <div className="truncate">{chat.title}</div>
              <button
                className={`btn btn-xs btn-ghost btn-square btn-error justify-self-end ${hoveredChatId === chat.id ? "visible" : "invisible"}`}
                onClick={(e) => handleDeleteChat(e, chat.id)}
                title="Delete chat"
              >
                <FaTrash />
              </button>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default Sidebar;
