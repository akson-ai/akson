import { useState, useEffect } from "react";
import Sidebar from "./Sidebar";

function Drawer({ children, chatId }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Add useEffect for keyboard shortcuts related to the sidebar
  useEffect(() => {
    const handleKeyboardShortcuts = (e) => {
      // Toggle sidebar with Cmd+Shift+S (Mac) or Ctrl+Shift+S (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "s") {
        e.preventDefault();
        setSidebarOpen((prevState) => !prevState);
      }

      // Close sidebar with Escape key when it's open
      if (e.key === "Escape" && sidebarOpen) {
        e.preventDefault();
        setSidebarOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyboardShortcuts);

    return () => {
      window.removeEventListener("keydown", handleKeyboardShortcuts);
    };
  }, [sidebarOpen]);

  return (
    <div className="drawer">
      {" "}
      {/* The root container */}
      {/* A hidden checkbox to toggle the visibility of the sidebar */}
      <input
        id="drawer-toggle"
        type="checkbox"
        className="drawer-toggle"
        checked={sidebarOpen}
        onChange={() => setSidebarOpen(!sidebarOpen)}
      />
      {/* All main page content goes here */}
      <div className="drawer-content flex flex-col">{children}</div>
      {/* Sidebar wrapper */}
      <div className="drawer-side">
        {/* A dark overlay that covers the whole page when the drawer is open */}
        <label htmlFor="drawer-toggle" className="drawer-overlay"></label>

        {/* The sidebar content */}
        <Sidebar chatId={chatId} />
      </div>
    </div>
  );
}

export default Drawer;
