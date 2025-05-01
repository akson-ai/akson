import { useSuspenseQuery, useMutation } from "@tanstack/react-query";
import { API_BASE_URL } from "../constants";
import { PiChatsFill } from "react-icons/pi";
import { RiChatNewFill } from "react-icons/ri";

function Header({ chatId, selectedAssistant, onAssistantChange, createNewChat }) {
  const { data: assistants } = useSuspenseQuery({ queryKey: ["assistants"] });
  const updateAssistantMutation = useMutation({
    mutationFn: async (assistant) => {
      await fetch(`${API_BASE_URL}/${chatId}/assistant`, {
        method: "PUT",
        credentials: "include",
        body: assistant,
      });
    },
  });

  return (
    <div className="navbar bg-base-100 shadow-sm">
      <div className="navbar-start">
        <div className="tooltip tooltip-right" data-tip="Chat history">
          <label htmlFor="drawer-toggle" className="btn btn-ghost btn-circle">
            <PiChatsFill size={20} />
          </label>
        </div>
      </div>
      <div className="navbar-center">
        <select
          id="assistant-select"
          className="select select-bordered w-full max-w-xs"
          value={selectedAssistant}
          onChange={(e) => {
            const assistant = e.target.value;
            onAssistantChange(assistant);
            updateAssistantMutation.mutate(assistant);
            document.getElementById("messageInput").focus();
          }}
        >
          {assistants.map((assistant) => (
            <option key={assistant.name} value={assistant.name}>
              {assistant.name}
            </option>
          ))}
        </select>
      </div>
      <div className="navbar-end">
        <div className="tooltip tooltip-left" data-tip="New chat">
          <button className="btn btn-ghost btn-circle" onClick={createNewChat}>
            <RiChatNewFill size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default Header;
