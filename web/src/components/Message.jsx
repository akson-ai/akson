import { useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { FaTrash, FaCopy } from "react-icons/fa6";
import { FaTools } from "react-icons/fa";

function Message({ id, role, name, content, toolCalls, category, onDelete }) {
  const [isHovered, setIsHovered] = useState(false);
  const categoryTag = category ? `chat-bubble-${category}` : "";
  return (
    <div
      className={`chat ${role === "user" ? "chat-end" : "chat-start"}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="chat-image avatar">
        <div className="w-10 rounded-full bg-base-300 place-content-center">
          <div className="text-2xl place-self-center">{role === "user" ? "👤" : "🤖"}</div>
        </div>
      </div>
      <div className="chat-header">
        <time className="text-xs opacity-50">{name}</time>
      </div>
      <div className={`chat-bubble ${categoryTag} mt-1`}>
        {!(content || toolCalls) ? (
          <div className="flex items-center">
            <div className="loading loading-spinner loading-sm mr-2"></div>
            <span>Thinking...</span>
          </div>
        ) : (
          <div>
            {role == "tool" && (
              <div className="mt-2 border-t border-base-300">
                <div className="flex items-center gap-2 text-sm opacity-70">
                  <FaTools />
                  <span>Result:</span>
                </div>
              </div>
            )}
            <div className={categoryTag ? "" : "prose"}>
              <Markdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || "");
                    return match ? (
                      <SyntaxHighlighter style={vscDarkPlus} language={match[1]} {...props}>
                        {String(children).replace(/\n$/, "")}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {content}
              </Markdown>
            </div>
            {toolCalls &&
              toolCalls.map((toolCall, index) => (
                <div key={index} className="mt-2 border-t border-base-300 pt-2">
                  <div className="flex items-center gap-2 text-sm opacity-70">
                    <FaTools />
                    <span>Tool call:</span>
                  </div>
                  <div className="mt-1 space-y-1">
                    <div className="text-sm font-mono bg-base-200 p-2 rounded">
                      <span className="text-primary">{toolCall.name}</span>
                      &nbsp;
                      <span className="text-secondary">{toolCall.arguments}</span>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
      {content && (
        <div className={`chat-footer mt-1 ${isHovered ? "visible" : "invisible"}`}>
          <>
            <button
              className="btn btn-xs btn-ghost btn-square"
              onClick={() => navigator.clipboard.writeText(content)}
              title="Copy message"
            >
              <FaCopy />
            </button>
            <button
              className="btn btn-xs btn-ghost btn-square btn-error"
              onClick={() => onDelete(id)}
              title="Delete message"
            >
              <FaTrash />
            </button>
          </>
        </div>
      )}
    </div>
  );
}

export default Message;
