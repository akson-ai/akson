import { FaArrowUp } from "react-icons/fa6";

function Input({ inputText, messageInputRef, onInputChange, onSendMessage }) {
  return (
    <div id="chatControls" className="flex flex-col mt-auto p-4 space-y-2">
      <div className="flex flex-col space-y-2">
        <label className="form-control w-full">
          <div className="flex space-x-2">
            <textarea
              id="messageInput"
              ref={messageInputRef}
              className="textarea textarea-bordered flex-1 min-h-12 max-h-48"
              placeholder="Type your message... (Shift+Enter for new line)"
              value={inputText}
              onChange={(e) => {
                onInputChange(e.target.value);
                // Auto-resize the textarea
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 192) + "px";
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSendMessage();
                }
              }}
              autoFocus
            />
            <button className="btn btn-primary" onClick={onSendMessage}>
              <FaArrowUp />
            </button>
          </div>
        </label>
      </div>
    </div>
  );
}

export default Input;
