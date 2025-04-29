import { useEffect } from "react";
import { FaKeyboard } from "react-icons/fa6";

function KeyboardShortcuts({ createNewChat, messageInputRef, abortControllerRef }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Add shortcut for keyboard shortcuts modal
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        document.getElementById("shortcuts_modal").showModal();
      }

      // Check for Cmd+Shift+O (Mac) or Ctrl+Shift+O (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "o") {
        e.preventDefault();
        createNewChat();
      }

      // Check for Shift+Esc to focus input
      if (e.shiftKey && e.key === "Escape") {
        e.preventDefault();
        messageInputRef.current?.focus();
      }

      // Check for Escape to abort current request
      if (e.key === "Escape") {
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
          abortControllerRef.current = null;
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [createNewChat, messageInputRef, abortControllerRef]);

  return (
    <>
      <div
        className="fixed bottom-4 right-4 btn btn-sm btn-ghost opacity-60 hover:opacity-100"
        onClick={() => document.getElementById("shortcuts_modal").showModal()}
      >
        <FaKeyboard className="mr-1" />
        <span>⌘ + /</span>
      </div>
      <dialog id="shortcuts_modal" className="modal">
        <div className="modal-box">
          <h3 className="font-bold text-lg">Keyboard Shortcuts</h3>
          <div className="py-4">
            <table className="table table-zebra">
              <thead>
                <tr>
                  <th>Shortcut</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <kbd className="kbd kbd-sm">Cmd</kbd> + <kbd className="kbd kbd-sm">Shift</kbd> +{" "}
                    <kbd className="kbd kbd-sm">S</kbd>
                  </td>
                  <td>Toggle sidebar</td>
                </tr>
                <tr>
                  <td>
                    <kbd className="kbd kbd-sm">Esc</kbd>
                  </td>
                  <td>Close sidebar / Cancel current request</td>
                </tr>
                <tr>
                  <td>
                    <kbd className="kbd kbd-sm">Cmd</kbd> + <kbd className="kbd kbd-sm">Shift</kbd> +{" "}
                    <kbd className="kbd kbd-sm">O</kbd>
                  </td>
                  <td>New chat</td>
                </tr>
                <tr>
                  <td>
                    <kbd className="kbd kbd-sm">Shift</kbd> + <kbd className="kbd kbd-sm">Esc</kbd>
                  </td>
                  <td>Focus input</td>
                </tr>
                <tr>
                  <td>
                    <kbd className="kbd kbd-sm">Enter</kbd>
                  </td>
                  <td>Send message</td>
                </tr>
                <tr>
                  <td>
                    <kbd className="kbd kbd-sm">Shift</kbd> + <kbd className="kbd kbd-sm">Enter</kbd>
                  </td>
                  <td>New line in message</td>
                </tr>
                <tr>
                  <td>
                    <kbd className="kbd kbd-sm">Cmd</kbd> + <kbd className="kbd kbd-sm">/</kbd>
                  </td>
                  <td>Show this help</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="modal-action">
            <form method="dialog">
              <button className="btn">Close</button>
            </form>
          </div>
        </div>
      </dialog>
    </>
  );
}

export default KeyboardShortcuts;
